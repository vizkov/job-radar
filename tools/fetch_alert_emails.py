"""Fetch job-alert emails over IMAP into .eml files. STANDARD LIBRARY ONLY.

This is the only code that sees the mailbox password. The workflow runs it
before `pip install`, with `python -I -S` (no site-packages, no .pth hooks), so
no third-party code is on the machine or in the process while the secret is in
the environment. radar.py then parses the saved files without any secret.

    python -I -S tools/fetch_alert_emails.py --out .alert_mail [--days 3] [--providers linkedin,indeed]

Credentials: JOBALERT_IMAP_USER, JOBALERT_IMAP_PASSWORD (a Gmail app password for
a mailbox used only for job alerts). The mailbox is opened read-only (EXAMINE)
and messages are fetched with BODY.PEEK[], so nothing is marked read or deleted.

Always writes <out>/_status.json and exits 0: a mail problem is reported by the
alert_email source in the digest, and never blocks the rest of the radar run.
"""
from __future__ import annotations

import argparse
import imaplib
import json
import os
import re
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))  # python -I leaves the script's folder off sys.path
from jobradar.alert_providers import PROVIDERS  # noqa: E402  (stdlib-only module)


ADDRESS = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")


def all_mail_name(m) -> str | None:
    """Gmail's "All Mail" folder (found by its \\All flag, so "[Google Mail]/All Mail" works too).
    Alerts that a filter or category keeps out of the Inbox are still there."""
    try:
        typ, data = m.list()
    except Exception:
        return None
    for line in data if typ == "OK" and data else []:
        text = line.decode(errors="replace") if isinstance(line, bytes) else str(line)
        if "\\All" in text.split(")")[0]:
            quoted = re.findall(r'"([^"]*)"', text)
            return quoted[-1] if quoted else text.rsplit(" ", 1)[-1]
    return None


def _search(m, since: date, sender: str) -> set[bytes]:
    typ, data = m.uid("SEARCH", None, "SINCE", since.strftime("%d-%b-%Y"), "FROM", f'"{sender}"')
    return set(data[0].split()) if typ == "OK" and data and data[0] else set()


def fetch(host: str, user: str, password: str, mailbox: str, since: date, senders: list[str],
          domains: dict[str, str] | None = None) -> tuple[list[tuple[str, bytes]], dict]:
    """Return ([(uid, raw message)] for mail from `senders` since `since`, diagnostics), read-only.

    Diagnostics, per provider domain: how many emails came from that domain at all, and the sender
    ADDRESSES (never contents) that aren't alert senders, so a changed sender or missing alerts show up
    in the log. `mailbox="auto"` means Gmail's All Mail if present, else INBOX."""
    out, diag = [], {"mailbox": "", "providers": {}}
    with imaplib.IMAP4_SSL(host, timeout=60) as m:
        m.login(user, password)
        if mailbox == "auto":
            mailbox = all_mail_name(m) or "INBOX"
        diag["mailbox"] = mailbox
        typ, _ = m.select(f'"{mailbox}"', readonly=True)  # EXAMINE: never marks or deletes
        if typ != "OK":
            raise RuntimeError(f"cannot open mailbox {mailbox!r}")
        uids: set[bytes] = set()
        for sender in senders:
            uids |= _search(m, since, sender)
        for name, domain in (domains or {}).items():
            from_domain = _search(m, since, domain)
            others: dict[str, int] = {}
            for uid in sorted(from_domain - uids, key=int)[:50]:
                typ, data = m.uid("FETCH", uid, "(BODY.PEEK[HEADER.FIELDS (FROM)])")
                if typ == "OK" and data and isinstance(data[0], tuple):
                    addr = ADDRESS.search(data[0][1].decode(errors="replace"))
                    if addr:
                        others[addr.group(0).lower()] = others.get(addr.group(0).lower(), 0) + 1
            diag["providers"][name] = {"from_domain": len(from_domain), "alert_senders": len(from_domain & uids),
                                       "other_senders": others}
        for uid in sorted(uids, key=int):
            typ, data = m.uid("FETCH", uid, "(BODY.PEEK[])")
            if typ == "OK" and data and isinstance(data[0], tuple):
                out.append((uid.decode(), data[0][1]))
    return out, diag


def configured_providers(path: Path | None = None) -> list[str]:
    """The `providers: [...]` list under `alert_email:` in profile/sources.yaml, so the workflow fetches exactly what
    the radar parses. Standard library only (this step holds the mailbox password), so no YAML parser: one regex.
    Falls back to every known provider when the file or the key is missing."""
    path = path or ROOT / "profile" / "sources.yaml"
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return list(PROVIDERS)
    block = re.search(r"^\s*alert_email:\s*$(.*?)(?=^\S|^\s{0,2}[A-Za-z_]+:\s*$|\Z)", text, re.M | re.S)
    m = re.search(r"^\s*providers:\s*\[([^\]]*)\]", block.group(1) if block else "", re.M)
    names = [n.strip().strip("'\"") for n in m.group(1).split(",") if n.strip()] if m else []
    return names or list(PROVIDERS)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default=".alert_mail")
    ap.add_argument("--days", type=int, default=3)
    ap.add_argument("--mailbox", default="auto", help='"auto" = Gmail All Mail if present, else INBOX')
    ap.add_argument("--host", default="imap.gmail.com")
    ap.add_argument("--providers", default="config",
                    help='comma list, or "config" (default) = the `providers` list of alert_email in profile/sources.yaml')
    args = ap.parse_args(argv)

    out = Path(args.out) if Path(args.out).is_absolute() else ROOT / args.out
    out.mkdir(parents=True, exist_ok=True)
    for old in out.glob("*.eml"):  # only this run's mail; seen.json handles repeats
        old.unlink()
    status = {"ok": False, "error": "", "fetched": 0, "at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    try:
        user, pw = os.environ.get("JOBALERT_IMAP_USER"), os.environ.get("JOBALERT_IMAP_PASSWORD")
        if not user or not pw:
            raise RuntimeError("JOBALERT_IMAP_USER / JOBALERT_IMAP_PASSWORD not set")
        names = configured_providers() if args.providers == "config" else             [n.strip() for n in args.providers.split(",") if n.strip()]
        unknown = [n for n in names if n not in PROVIDERS]
        if unknown:
            raise RuntimeError(f"unknown providers: {', '.join(unknown)}")
        senders = sorted({s.lstrip("@") for n in names for s in PROVIDERS[n].senders})
        domains = {n: PROVIDERS[n].dkim_domain for n in names}
        msgs, diag = fetch(args.host, user, pw, args.mailbox, date.today() - timedelta(days=args.days), senders,
                           domains)
        for uid, raw in msgs:
            (out / f"{uid}.eml").write_bytes(raw)
        status.update(ok=True, fetched=len(msgs), **diag)
    except Exception as e:  # report, never crash the workflow; never echo credentials
        status["error"] = f"{type(e).__name__}: {str(e)[:200]}"
    (out / "_status.json").write_text(json.dumps(status, indent=1), encoding="utf-8")
    print(f"alert mail: {'ok' if status['ok'] else 'FAILED'} ({status['fetched']} fetched"
          f"{' from ' + status['mailbox'] if status.get('mailbox') else ''})"
          f"{' ' + status['error'] if status['error'] else ''}")
    for name, d in status.get("providers", {}).items():  # addresses and counts only, never contents
        others = ", ".join(f"{a} ({n})" for a, n in sorted(d["other_senders"].items(), key=lambda x: -x[1])[:5])
        print(f"  {name}: {d['from_domain']} emails from {name}'s domain, {d['alert_senders']} from alert senders"
              + (f"; other senders: {others}" if others else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
