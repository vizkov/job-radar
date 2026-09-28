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
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))  # python -I leaves the script's folder off sys.path
from jobradar.alert_providers import PROVIDERS  # noqa: E402  (stdlib-only module)


def fetch(host: str, user: str, password: str, mailbox: str, since: date, senders: list[str]) -> list[tuple[str, bytes]]:
    """Return [(uid, raw message)] for mail from `senders` since `since`, without changing the mailbox."""
    out = []
    with imaplib.IMAP4_SSL(host, timeout=60) as m:
        m.login(user, password)
        typ, _ = m.select(f'"{mailbox}"', readonly=True)  # EXAMINE: never marks or deletes
        if typ != "OK":
            raise RuntimeError(f"cannot open mailbox {mailbox!r}")
        uids: set[bytes] = set()
        for sender in senders:
            typ, data = m.uid("SEARCH", None, "SINCE", since.strftime("%d-%b-%Y"), "FROM", f'"{sender}"')
            if typ == "OK" and data and data[0]:
                uids.update(data[0].split())
        for uid in sorted(uids, key=int):
            typ, data = m.uid("FETCH", uid, "(BODY.PEEK[])")
            if typ == "OK" and data and isinstance(data[0], tuple):
                out.append((uid.decode(), data[0][1]))
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default=".alert_mail")
    ap.add_argument("--days", type=int, default=3)
    ap.add_argument("--mailbox", default="INBOX")
    ap.add_argument("--host", default="imap.gmail.com")
    ap.add_argument("--providers", default=",".join(PROVIDERS))
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
        names = [n.strip() for n in args.providers.split(",") if n.strip()]
        unknown = [n for n in names if n not in PROVIDERS]
        if unknown:
            raise RuntimeError(f"unknown providers: {', '.join(unknown)}")
        senders = sorted({s.lstrip("@") for n in names for s in PROVIDERS[n].senders})
        msgs = fetch(args.host, user, pw, args.mailbox, date.today() - timedelta(days=args.days), senders)
        for uid, raw in msgs:
            (out / f"{uid}.eml").write_bytes(raw)
        status.update(ok=True, fetched=len(msgs))
    except Exception as e:  # report, never crash the workflow; never echo credentials
        status["error"] = f"{type(e).__name__}: {str(e)[:200]}"
    (out / "_status.json").write_text(json.dumps(status, indent=1), encoding="utf-8")
    print(f"alert mail: {'ok' if status['ok'] else 'FAILED'} ({status['fetched']} fetched){' ' + status['error'] if status['error'] else ''}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
