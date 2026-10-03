"""Application-mail helpers shared by the secret-holding fetch step and the offline ingest. STANDARD LIBRARY ONLY.

tools/fetch_application_mail.py imports this in the workflow step that holds the Gmail app password, before any
third-party package is installed (like jobradar/alert_providers.py), so keep it free of non-stdlib imports.

Everything here works on text the mailbox owner did not write (company and recruiter emails): it only compares and
matches, it never follows instructions found in a message.
"""
from __future__ import annotations

import csv
import json
import re
from pathlib import Path

# Stages whose roles can be the subject of an email. Shortlisted is included on purpose: the user often applies
# before moving the card, and the receipt email is the first evidence that they did.
WATCHED = ("Shortlisted", "Applied", "Interview")

# Sender domains of recruiting systems and big employers' no-reply senders. Mail from these is considered even when the
# company's name is not in the sender (Lever and Greenhouse send for many companies).
ATS_DOMAINS = (   # the sender's domain is one of these or a subdomain of one
    "lever.co", "greenhouse.io", "myworkday.com", "myworkdayjobs.com", "ashbyhq.com", "smartrecruiters.com", "icims.com",
    "successfactors.com", "successfactors.eu", "taleo.net", "workable.com", "recruitee.com", "teamtailor.com", "jobvite.com",
    "bamboohr.com", "pinpointhq.com", "eightfold.ai", "phenompeople.com", "amazon.jobs", "email.apple.com",
)
# A subdomain label that recruiting systems use in front of a company's own domain (hire.acme.com, recruiting.facebook.com).
ATS_LABELS = ("hire", "recruiting", "careers", "jobs", "talent", "apply")

# Mail that must never reach the ledger: sign-in codes, password resets and security alerts.
NOISE_SUBJECT = re.compile(
    r"verification code|passcode|one[- ]time|\botp\b|password|security alert|sign[- ]?in|log[- ]?in code|2-step|"
    r"confirm your (?:email|account)|verify your", re.I)

# Job-board alert and newsletter senders: handled by the alert-mail pipeline, not by this one.
ALERT_SENDER = re.compile(r"(?:jobalerts|jobs-listings|jobs-noreply|newsletters?|alert)[^@]*@|@(?:\w+\.)*(?:indeed|glassdoor)\.com", re.I)

ADDRESS = re.compile(r"[\w.+-]+@([\w-]+(?:\.[\w-]+)+)")
_WORDS = re.compile(r"[^a-z0-9]+")


def norm(text: str) -> str:
    """Lower-case words separated by single spaces ("Sr. Security Engineer , AppSec" -> "sr security engineer appsec")."""
    return _WORDS.sub(" ", (text or "").lower()).strip()


def contains(haystack: str, needle: str) -> bool:
    """True when `needle` occurs in `haystack` as whole words (both already passed through norm)."""
    return bool(needle) and f" {needle} " in f" {haystack} "


def sender_domain(from_header: str) -> str:
    m = ADDRESS.search(from_header or "")
    return m.group(1).lower() if m else ""


def is_ats(from_header: str) -> bool:
    domain = sender_domain(from_header)
    labels = domain.split(".")
    return (any(domain == d or domain.endswith("." + d) for d in ATS_DOMAINS)
            or any(label in ATS_LABELS for label in labels[:-2]))   # whole labels: yorkshire.gov.uk is not "hire."


def _json(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def latest_stages(root: Path) -> dict[str, str]:
    """ref -> Stage: the committed board snapshot, overlaid with the newest Stage change in the pipeline log."""
    stages = dict(_json(root / "data" / "pipeline_snapshot.json", {}))
    newest: dict[str, str] = {}
    log = root / "data" / "pipeline_log.jsonl"
    if log.exists():
        for line in log.read_text(encoding="utf-8").splitlines():
            try:
                rec = json.loads(line)
            except ValueError:
                continue
            if rec.get("field") == "Stage" and str(rec.get("at", "")) >= newest.get(rec["ref"], ""):
                newest[rec["ref"]] = str(rec.get("at", ""))
                stages[rec["ref"]] = rec["value"]
    return stages


def targets(root: Path, stages: tuple[str, ...] = WATCHED) -> list[dict]:
    """The roles an email may be about: [{ref, stage, company, title, c (normalised company), t (normalised title)}]."""
    live = latest_stages(root)
    rows: dict[str, dict] = {}
    matches = root / "data" / "matches.csv"
    if matches.exists():
        with open(matches, newline="", encoding="utf-8") as fh:
            rows = {r.get("ref"): r for r in csv.DictReader(fh)}
    out = []
    for ref, stage in live.items():
        if stage not in stages or ref not in rows:
            continue
        company, title = (rows[ref].get("company") or "").strip(), (rows[ref].get("title") or "").strip()
        if company:
            out.append({"ref": ref, "stage": stage, "company": company, "title": title,
                        "c": norm(company), "t": norm(title)})
    return out


def candidate(from_header: str, subject: str, has_unsubscribe: bool, tgts: list[dict]) -> bool:
    """Cheap header-only test: is this message worth fetching a snippet for?"""
    if NOISE_SUBJECT.search(subject or "") or ALERT_SENDER.search(from_header or ""):
        return False
    if is_ats(from_header):
        return True
    if has_unsubscribe:        # bulk mail (promotions, newsletters) from a non-recruiting sender
        return False
    head = norm(f"{from_header} {subject}")
    return any(contains(head, t["c"]) for t in tgts)


def resolve(text: str, tgts: list[dict]) -> tuple[str, str, list[str]]:
    """Which role is this email about? -> (ref, how, candidate refs).

    how: "exact" (one role's full title is in the text), "company" (only one watched role at that company),
    "ambiguous" (several roles at the company and no title match) or "none" (no watched company named).
    Matching by company alone is not trusted for rejections: Amazon alone can have three open applications."""
    body = norm(text)
    at_company = [t for t in tgts if contains(body, t["c"])]
    if not at_company:
        return "", "none", []
    exact = [t for t in at_company if t["t"] and contains(body, t["t"])]
    if exact:
        longest = max(len(t["t"]) for t in exact)
        best = [t for t in exact if len(t["t"]) == longest]
        if len(best) == 1:
            return best[0]["ref"], "exact", [t["ref"] for t in at_company]
    if len({t["ref"] for t in at_company}) == 1:
        return at_company[0]["ref"], "company", [at_company[0]["ref"]]
    return "", "ambiguous", [t["ref"] for t in at_company]
