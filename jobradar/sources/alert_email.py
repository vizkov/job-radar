"""Job-alert emails (LinkedIn, Indeed, Glassdoor) → postings. No scraping, no logins.

You set up job alerts on each site; they email you. A filter in your main Gmail
auto-forwards those emails to a dedicated mailbox used only for this.

This adapter never touches IMAP and never sees a credential. The mail is fetched
by tools/fetch_alert_emails.py, a standard-library-only script that runs in its
own workflow step before any third-party package is installed, and saves the
messages as .eml files in `eml_dir` (default .alert_mail/) with a _status.json.
That keeps the mailbox password away from the dozens of third-party packages
this process imports.

Trust: email is spoofable. A message is only used when its sender belongs to a
known provider and (by default) it carries a passing DKIM signature for that
provider's domain. Job URLs are rebuilt from the job ID, so a spoofed or
tampered email can't smuggle a phishing link into the digest. Where a provider's
alerts carry no ID (Indeed: opaque tracking redirects), only links on its own
https redirect host are accepted. Titles/companies
are still untrusted text (see untrusted.py).
"""
from __future__ import annotations

import asyncio
import email
import hashlib
import json
import re
from email.message import Message
from email.policy import default as default_policy
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.parse import unquote

from selectolax.parser import HTMLParser

from jobradar.alert_providers import PROVIDERS, Provider, dkim_ok, provider_for  # noqa: F401 (re-exported)
from jobradar.common import ROOT, countries_for
from jobradar.model import Posting, SourceResult, UnitStatus
from jobradar.sources import register

# card lines that are never the company or location
_NOISE = re.compile(r"^(easy apply|apply with .*|actively recruiting|promoted|be an early applicant|urgently hiring|"
                    r"\d+\s+(connections?|alumni|applicants?|school alumni).*|.*\bago$|new|view job:?.*|"
                    r"see all jobs.*|.*salary.*|[£€$].*|\d+\s*(company alumni|connection).*|"
                    r"responsive employer|just posted|\d(\.\d)?\s*★?|easily apply|view all jobs.*|"
                    # LinkedIn card "insights" (seen in real alerts, 2026-09): not title, company or location
                    r"this company is actively hiring|actively hiring|fast growing|hiring multiple candidates|"
                    r"top applicant|in your network|school alumni|<[^>]+>.*)$", re.I)


def _part(msg: Message, ctype: str) -> str:
    for part in msg.walk():
        if part.get_content_type() == ctype and not part.is_attachment():
            try:
                return part.get_content()
            except Exception:
                payload = part.get_payload(decode=True) or b""
                return payload.decode(part.get_content_charset() or "utf-8", "replace")
    return ""


def _find_id(p: Provider, s: str) -> str | None:
    m = p.job_id.search(s) or p.job_id.search(unquote(s))  # tracking redirects URL-encode the target
    return m.group(1) if m else None


def _find_link(p: Provider, s: str) -> tuple[str | None, str | None]:
    """(job ID, None) when the link carries one; else (None, redirect URL) for ID-less providers."""
    if (jid := _find_id(p, s)):
        return jid, None
    m = p.redirect.search(s) if p.redirect else None
    return None, (m.group(0) if m else None)


def _has_company_line(line: str) -> bool:
    return any(sep in line for sep in (" · ", " - ", " – "))


def _content_id(title: str, company: str, location: str) -> str:
    """Stable ID for a job the email only links to through a one-off tracking redirect."""
    key = "|".join(" ".join(x.lower().split()) for x in (title, company, location))
    return "h" + hashlib.sha1(key.encode()).hexdigest()[:15]


def _split_company_location(lines: list[str]) -> tuple[str, str]:
    lines = [l for l in lines if l and not _NOISE.match(l)]
    if not lines:
        return "", ""
    for sep in (" · ", " - ", " – "):  # "Acme Ltd · London, England, United Kingdom (Hybrid)"
        if sep in lines[0]:
            company, _, location = lines[0].partition(sep)
            return company.strip(), location.strip()
    return lines[0], (lines[1] if len(lines) > 1 else "")


def parse_text(p: Provider, body: str) -> list[dict]:
    """Plain-text part: a card is a short paragraph ending in (or followed by) the job URL."""
    jobs, para, prev = [], [], []
    for raw in body.splitlines():
        line = " ".join(raw.split())
        jid, link = _find_link(p, line) if "http" in line else (None, None)
        if jid or link:
            # An insight line ("This company is actively hiring") can sit after a blank line, alone in
            # its paragraph: then the card is the paragraph before it.
            card = [l for l in para if not _NOISE.match(l)] or [l for l in prev if not _NOISE.match(l)]
            # longer = prose, not a job card; an ID-less link needs a real "Company - Location" line,
            # else it's the email's own browse/unsubscribe/footer link
            if card and len(card) <= 6 and (jid or (len(card) > 1 and _has_company_line(card[1]))):
                company, location = _split_company_location(card[1:])
                jobs.append({"id": jid or _content_id(card[0], company, location), "link": link,
                             "title": card[0], "company": company, "location": location})
            para, prev = [], []
        elif not line or set(line) <= set("-=_"):
            if para:
                prev, para = para, []
        else:
            para.append(line)
    return jobs


def parse_html(p: Provider, body: str) -> list[dict]:
    """HTML part: find job links, take the largest enclosing element that holds only that one job."""
    tree = HTMLParser(body)
    jobs, done = [], set()
    for a in tree.css("a[href]"):
        jid = _find_id(p, a.attributes.get("href") or "")
        if not jid or jid in done:
            continue
        node = a
        while node.parent is not None:
            parent_ids = {_find_id(p, x.attributes.get("href") or "") for x in node.parent.css("a[href]")} - {None}
            if len(parent_ids) > 1:
                break
            node = node.parent
        lines = [" ".join(t.split()) for t in node.text(separator="\n").splitlines()]
        lines = [l for l in lines if l and not _NOISE.match(l)]
        title = next((" ".join(x.text().split()) for x in node.css("a[href]")
                      if _find_id(p, x.attributes.get("href") or "") == jid and x.text().strip()), "")
        if not title:
            continue
        rest = lines[lines.index(title) + 1:] if title in lines else lines
        company, location = _split_company_location(rest)
        done.add(jid)
        jobs.append({"id": jid, "title": title, "company": company, "location": location})
    return jobs


_SUBJECT_PLACE = re.compile(r"\bjobs? in (.+?)(?: is now active)?$", re.I)


def to_postings(msg: Message, p: Provider) -> list[Posting]:
    jobs = parse_text(p, _part(msg, "text/plain")) or parse_html(p, _part(msg, "text/html"))
    # Alerts are per search, e.g. "5 new … jobs in United Kingdom": the searched place backs up card
    # locations the country lookup doesn't know (small towns).
    hit = _SUBJECT_PLACE.search(" ".join((msg.get("Subject") or "").split()))
    place = hit.group(1) if hit else ""
    out = []
    try:
        when = parsedate_to_datetime(msg.get("Date")) if msg.get("Date") else None
    except (TypeError, ValueError):
        when = None
    for j in jobs:
        countries = countries_for(None, j["location"]) or (countries_for(None, place) if place else set())
        out.append(Posting(source=f"{p.name}_email", company=j["company"], title=j["title"],
                           location=j["location"], countries=frozenset(countries),
                           url=j.get("link") or p.url.format(id=j["id"]), external_id=j["id"], posted_at=when,
                           raw={"message_id": msg.get("Message-ID", "")}))
    return out


class AlertEmailSource:
    name = "alert_email"

    def __init__(self, cfg: dict):
        self.timeout = float(cfg.get("timeout_seconds", 120))
        self.require_dkim = cfg.get("require_dkim", True)
        eml_dir = Path(cfg.get("eml_dir") or ".alert_mail")
        self.eml_dir = eml_dir if eml_dir.is_absolute() else ROOT / eml_dir
        self.providers = [PROVIDERS[n] for n in cfg.get("providers") or ["linkedin"]]

    def _messages(self) -> list[Message]:
        if not self.eml_dir.is_dir():
            raise RuntimeError(f"no fetched mail in {self.eml_dir.name}/ (run tools/fetch_alert_emails.py first)")
        status_file = self.eml_dir / "_status.json"
        self.fetch_status = {}
        if status_file.exists():
            status = json.loads(status_file.read_text(encoding="utf-8"))
            if not status.get("ok"):
                raise RuntimeError(f"mail fetch failed: {status.get('error') or 'unknown error'}")
            self.fetch_status = status
        return [email.message_from_bytes(f.read_bytes(), policy=default_policy)
                for f in sorted(self.eml_dir.glob("*.eml"))]

    async def fetch(self) -> SourceResult:
        msgs = await asyncio.to_thread(self._messages)
        out = SourceResult(self.name)
        per = {p.name: {"jobs": 0, "rejected": 0, "empty": 0, "mails": 0} for p in self.providers}
        foreign = 0
        for msg in msgs:
            p = provider_for(msg)
            if p is None or p.name not in per:
                foreign += 1
                continue
            stats = per[p.name]
            stats["mails"] += 1
            if self.require_dkim and not dkim_ok(msg, p.dkim_domain):
                stats["rejected"] += 1
                continue
            ps = to_postings(msg, p)
            stats["jobs"] += len(ps)
            stats["empty"] += not ps
            out.postings += ps
        for name, s in per.items():
            # a quiet week with no alerts is normal (track_empty=False)
            out.units.append(UnitStatus(name, ok=True, raw_count=s["jobs"], label=f"{name} alert emails",
                                        track_empty=False))
            if s["rejected"]:
                out.units.append(UnitStatus(f"{name}:rejected", ok=False, track_empty=False,
                                            label=f"{name} emails failing DKIM",
                                            error=f"{s['rejected']} of {s['mails']} {name} emails failed DKIM"))
            if s["empty"]:  # the provider changed its email layout
                out.units.append(UnitStatus(f"{name}:parse", ok=False, label=f"{name} alert emails with no jobs",
                                            error=f"{s['empty']} {name} emails yielded no jobs (layout change?)"))
        if foreign:
            out.units.append(UnitStatus("foreign", ok=False, track_empty=False, label="emails from unknown senders",
                                        error=f"{foreign} of {len(msgs)} emails ignored (unknown sender)"))
        out.units += self._mailbox_units()
        return out

    def _mailbox_units(self) -> list[UnitStatus]:
        """What the fetcher saw in the mailbox (counts and sender addresses only), as health units, so
        "no alert emails" is explained on the status card instead of looking like a quiet week."""
        seen = (getattr(self, "fetch_status", {}) or {}).get("providers") or {}
        units = []
        wanted = [p.name for p in self.providers if p.name in seen]
        if wanted and all(seen[n]["from_domain"] == 0 for n in wanted):
            units.append(UnitStatus("mailbox:none", ok=False, track_empty=False, label="alert emails in the mailbox",
                                    error=f"no emails at all from {', '.join(wanted)} in the last days (checked "
                                          f"{self.fetch_status.get('mailbox') or 'the mailbox'}): alerts not set up, "
                                          "paused, or going to a different mailbox"))
        for n in wanted:
            d = seen[n]
            if d["from_domain"] and not d["alert_senders"] and d.get("other_senders"):
                who = ", ".join(sorted(d["other_senders"], key=lambda a: -d["other_senders"][a])[:3])
                units.append(UnitStatus(f"{n}:senders", ok=False, track_empty=False, label=f"{n} alert sender",
                                        error=f"{d['from_domain']} {n} emails, none from a known alert sender "
                                              f"(seen: {who}): the alert sender may have changed"))
        return units


register("alert_email")(AlertEmailSource)
