"""Fetch application-related emails over IMAP into one JSON file. STANDARD LIBRARY ONLY.

Like fetch_alert_emails.py, this is code that sees the mailbox password: the workflow runs it before `pip install`,
with `python -I -S`. It reads the mailbox read-only (EXAMINE, BODY.PEEK[]), so nothing is marked read or deleted.

    python -I -S tools/fetch_application_mail.py --out .app_mail [--days 4]

It looks for mail about roles whose card is Shortlisted, Applied or Interview (from data/pipeline_snapshot.json,
data/pipeline_log.jsonl and data/matches.csv in the checkout): mail from a recruiting system, or from a sender or with a
subject that names the company. Sign-in codes, password resets, security alerts, job-alert mail and bulk promotions are
skipped without being read. For each kept message it saves headers, Gmail's thread id and the first ~2500 characters of
the text part to <out>/messages.json (never committed). `tools/app_mail.py ingest` then classifies them without any
secret and writes the ledger, which holds no message text.

Credentials: JOBALERT_IMAP_USER, JOBALERT_IMAP_PASSWORD (the same secrets as the alert-mail step).
Always writes <out>/_status.json and exits 0: a mail problem is reported in the brief and never blocks the radar run.
"""
from __future__ import annotations

import argparse
import email
import email.policy
import html
import imaplib
import json
import os
import re
import sys
from datetime import date, datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))  # python -I leaves the script's folder off sys.path
sys.path.insert(0, str(ROOT / "tools"))
from fetch_alert_emails import all_mail_name  # noqa: E402  (stdlib-only)
from jobradar import application_mail as am  # noqa: E402  (stdlib-only)

SNIPPET_CHARS = 2500
MAX_SCANNED = 600      # newest messages in the window whose headers are read
MAX_CANDIDATES = 120   # per run: each one is a fetch, and a busy mailbox must not make the step slow
THREAD = re.compile(rb"X-GM-THRID (\d+)")
TAGS = re.compile(r"<[^>]+>")
BLOCKS = re.compile(r"(?is)<(style|script|head)\b.*?</\1>")   # CSS and scripts would fill the snippet


def _text(msg: email.message.Message) -> str:
    """The first text/plain part (else the tags-stripped text/html part), truncated."""
    for kind in ("plain", "html"):
        part = msg.get_body(preferencelist=(kind,))
        if part is None:
            continue
        try:
            body = part.get_content()
        except Exception:
            continue
        if kind == "html":
            body = html.unescape(TAGS.sub(" ", BLOCKS.sub(" ", body)))
        return re.sub(r"\s+", " ", body).strip()[:SNIPPET_CHARS]
    return ""


def fetch(host: str, user: str, password: str, mailbox: str, since: date, tgts: list[dict]) -> tuple[list[dict], dict]:
    out: list[dict] = []
    diag = {"mailbox": "", "scanned": 0, "candidates": 0}
    with imaplib.IMAP4_SSL(host, timeout=60) as m:
        m.login(user, password)
        if mailbox == "auto":
            mailbox = all_mail_name(m) or "INBOX"
        diag["mailbox"] = mailbox
        typ, _ = m.select(f'"{mailbox}"', readonly=True)
        if typ != "OK":
            raise RuntimeError(f"cannot open mailbox {mailbox!r}")
        typ, data = m.uid("SEARCH", None, "SINCE", since.strftime("%d-%b-%Y"))
        uids = data[0].split() if typ == "OK" and data and data[0] else []
        diag["scanned"] = len(uids)
        for uid in uids[-MAX_SCANNED:]:   # the newest ones: a busy mailbox must not make the step slow
            typ, data = m.uid("FETCH", uid, "(BODY.PEEK[HEADER.FIELDS (FROM SUBJECT LIST-UNSUBSCRIBE)])")
            if typ != "OK" or not data or not isinstance(data[0], tuple):
                continue
            head = email.message_from_bytes(data[0][1], policy=email.policy.default)
            sender, subject = str(head.get("From", "")), str(head.get("Subject", ""))
            if not am.candidate(sender, subject, bool(head.get("List-Unsubscribe")), tgts):
                continue
            diag["candidates"] += 1
            if diag["candidates"] > MAX_CANDIDATES:
                break
            typ, data = m.uid("FETCH", uid, "(X-GM-THRID BODY.PEEK[])")
            if typ != "OK" or not data or not isinstance(data[0], tuple):
                continue
            msg = email.message_from_bytes(data[0][1], policy=email.policy.default)
            thread = THREAD.search(data[0][0])
            try:
                when = parsedate_to_datetime(str(msg.get("Date"))).astimezone(timezone.utc).isoformat(timespec="seconds")
            except (TypeError, ValueError):
                when = ""
            out.append({"message_id": str(msg.get("Message-ID", "")).strip() or f"uid-{uid.decode()}",
                        "from": sender[:200], "subject": subject[:300], "date": when,
                        "thread": format(int(thread.group(1)), "x") if thread else "",
                        "text": _text(msg)})
    return out, diag


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default=".app_mail")
    ap.add_argument("--days", type=int, default=4)
    ap.add_argument("--mailbox", default="auto", help='"auto" = Gmail All Mail if present, else INBOX')
    ap.add_argument("--host", default="imap.gmail.com")
    args = ap.parse_args(argv)

    out = Path(args.out) if Path(args.out).is_absolute() else ROOT / args.out
    out.mkdir(parents=True, exist_ok=True)
    status = {"ok": False, "error": "", "fetched": 0, "at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    messages: list[dict] = []
    try:
        user, pw = os.environ.get("JOBALERT_IMAP_USER"), os.environ.get("JOBALERT_IMAP_PASSWORD")
        if not user or not pw:
            raise RuntimeError("JOBALERT_IMAP_USER / JOBALERT_IMAP_PASSWORD not set")
        tgts = am.targets(ROOT)
        if tgts:
            messages, diag = fetch(args.host, user, pw, args.mailbox, date.today() - timedelta(days=args.days), tgts)
            status.update(diag)
        status.update(ok=True, fetched=len(messages), watched=len(tgts))
    except Exception as e:  # report, never crash the workflow; never echo credentials
        status["error"] = f"{type(e).__name__}: {str(e)[:200]}"
    (out / "messages.json").write_text(json.dumps(messages), encoding="utf-8")
    (out / "_status.json").write_text(json.dumps(status, indent=1), encoding="utf-8")
    print(f"application mail: {'ok' if status['ok'] else 'FAILED'} ({status['fetched']} kept of "
          f"{status.get('candidates', 0)} candidates, {status.get('watched', 0)} roles watched)"
          f"{' ' + status['error'] if status['error'] else ''}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
