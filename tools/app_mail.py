"""Application mail ledger: what the companies have written to you, and what to do about each email. STANDARD LIBRARY ONLY.

    python tools/app_mail.py ingest [--dir .app_mail]   # classify the daily scan's messages into state/application_mail.jsonl
    python tools/app_mail.py plan [--json]              # what needs doing: auto moves, questions, action-needed mail
    python tools/app_mail.py ack <id> … [--how moved]   # an item is dealt with: stop listing it
    python tools/app_mail.py status                     # when the scan last ran and whether it worked

The GitHub Action fetches the mail (tools/fetch_application_mail.py, the only step with the mailbox password), then
`ingest` runs without any secret and commits the ledger. The ledger is private (state/) and holds sender address, subject,
date, Gmail thread id, the classification and the matched role, never message text. Email text is third-party data:
the classifier only matches phrases, it never follows instructions in a message.

The Action cannot move board cards (its token cannot reach the Project), so the session does it: `plan` says which
moves are safe to make and tell the user about ("auto") and which need the user's yes ("ask").
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))
from jobradar import application_mail as am  # noqa: E402
import inbox_outcomes  # noqa: E402

LEDGER = "state/application_mail.jsonl"
STATUS = "state/application_mail_status.json"
SCAN_STALE_HOURS = 36   # the Action runs three times a day; a day and a half without a good scan is a problem
INFO_DAYS = 3           # receipts and referral notices are mentioned for this long

# An interview email is only trusted to move a card when it is an invitation, not boilerplate that mentions interviews.
STRONG_INTERVIEW = re.compile(r"schedul|invite you|phone screen|would like to (?:speak|talk|chat|meet)|book a (?:time|slot)|"
                              r"calendly|your availability", re.I)
NEEDS_ACTION = re.compile(r"please (?:complete|reply|respond|confirm|submit|upload|book|select|provide)|action required|"
                          r"within \d+ (?:hours?|days?|business days)|assessment|calendly|availability|deadline", re.I)
DEFINITE_REJECTION = re.compile(r"unfortunately|regret to inform|decided (?:to (?:proceed|move forward|go forward) with|not to)|"
                                r"position has been filled|will not be (?:moving|proceeding)", re.I)
_CONTROL = re.compile(r"[\x00-\x1f\x7f]")


def safe(text, limit: int = 80) -> str:
    t = " ".join(_CONTROL.sub(" ", str(text or "")).split())
    return t if len(t) <= limit else t[: limit - 1] + "…"


def classify_mail(subject: str, text: str) -> tuple[str, str, bool, bool]:
    """(type, matched phrase, strong, needs_action). type: rejection | offer | interview | receipt | referral | unknown.

    A definite rejection or an offer in the text wins. Otherwise a receipt-like subject ("Thank you for applying") makes it a receipt even
    when the body talks about interviews, which receipts routinely do."""
    label, phrase = inbox_outcomes.classify(subject, text)
    subject_label, _ = inbox_outcomes.classify(subject, "")
    if subject_label in ("acknowledgement", "referral") and (label not in ("rejection", "offer") or (
            label == "rejection" and not DEFINITE_REJECTION.search(text))):
        # receipts say "if you are not selected, we will keep your details" and "an interview may follow"
        label = subject_label
    kind = {"acknowledgement": "receipt"}.get(label, label)
    body = f"{subject}\n{text}"
    strong = kind == "interview" and bool(STRONG_INTERVIEW.search(body))
    action = kind not in ("receipt", "referral", "rejection") and (kind in ("interview", "offer", "unknown")
                                                                    or bool(NEEDS_ACTION.search(body)))
    return kind, phrase, strong, action


def _read(path: Path) -> list[dict]:
    rows: list[dict] = []
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            try:
                rows.append(json.loads(line))
            except ValueError:
                continue
    return rows


def ledger(root: Path = ROOT) -> tuple[list[dict], set[str]]:
    """(mail rows, acked ids)."""
    rows = _read(root / LEDGER)
    return [r for r in rows if "ack" not in r], {r["ack"] for r in rows if "ack" in r}


def _append(root: Path, rows: list[dict]) -> None:
    path = root / LEDGER
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n")


def mail_id(message_id: str) -> str:
    return hashlib.sha1(message_id.encode("utf-8", "replace")).hexdigest()[:10]


def ingest(root: Path, messages: list[dict], now: datetime | None = None) -> list[dict]:
    """Classify fetched messages and append the new ones to the ledger. Returns the new rows."""
    now = now or datetime.now(timezone.utc).replace(tzinfo=None)
    tgts = am.targets(root)
    known = {r["id"] for r in ledger(root)[0]}
    new: list[dict] = []
    for m in messages:
        mid = mail_id(m.get("message_id", ""))
        subject = str(m.get("subject", ""))
        if mid in known or am.NOISE_SUBJECT.search(subject):
            continue
        text = str(m.get("text", ""))
        ref, how, cands = am.resolve(f"{m.get('from', '')} {subject} {text}", tgts)
        if how == "none":    # not about a role being watched: not logged
            continue
        kind, phrase, strong, action = classify_mail(subject, text)
        sender = am.ADDRESS.search(m.get("from", ""))
        known.add(mid)
        new.append({"id": mid, "at": m.get("date") or now.isoformat(timespec="seconds"), "from": sender.group(0).lower() if sender else "",
                    "subject": safe(subject, 160), "type": kind, "phrase": phrase, "strong": strong, "action": action,
                    "ref": ref, "how": how, "candidates": cands, "thread": m.get("thread", "")})
    _append(root, new)
    return new


def _link(thread: str) -> str:
    return f"https://mail.google.com/mail/u/0/#all/{thread}" if thread else ""


def plan(root: Path = ROOT, now: datetime | None = None) -> dict[str, list[dict]]:
    """Unhandled mail in four buckets: auto (safe moves), ask (needs the user's yes), action (the user must do something),
    info (receipts and referral notices from the last few days)."""
    now = now or datetime.now(timezone.utc).replace(tzinfo=None)
    rows, acked = ledger(root)
    stages = am.latest_stages(root)
    by_ref = {t["ref"]: t for t in am.targets(root, stages=("Shortlisted", "Applied", "Interview", "Offer", "Rejected", "Skipped"))}
    out: dict[str, list[dict]] = {"auto": [], "ask": [], "action": [], "info": []}
    for r in sorted(rows, key=lambda x: x.get("at", "")):
        if r["id"] in acked:
            continue
        t = by_ref.get(r.get("ref", ""), {})
        stage = stages.get(r.get("ref", ""), "")
        item = {"id": r["id"], "ref": r.get("ref", ""), "company": t.get("company", ""), "title": t.get("title", ""),
                "stage": stage, "type": r["type"], "subject": r["subject"], "at": r["at"][:10], "how": r.get("how", ""),
                "link": _link(r.get("thread", "")), "to": "", "why": ""}
        resolved = r.get("how") in ("exact", "company")
        kind = r["type"]
        if kind == "receipt":
            if stage == "Shortlisted" and resolved:
                out["ask"].append({**item, "to": "Applied", "why": "the company confirmed an application, the card still says Shortlisted"})
            elif _recent(r["at"], now):
                out["info"].append(item)
        elif kind == "referral":
            if _recent(r["at"], now):
                out["info"].append(item)
        elif kind == "rejection":
            if stage in ("Rejected", "Skipped"):
                continue
            if r.get("how") == "exact" and stage in ("Shortlisted", "Applied", "Interview"):
                out["auto"].append({**item, "to": "Rejected", "why": "the email names this exact role"})
            else:
                out["ask"].append({**item, "to": "Rejected", "why": f"match is '{r.get('how')}', not the exact role"})
        elif kind == "offer":
            if resolved and stage not in ("Offer", "Rejected", "Skipped"):
                out["auto"].append({**item, "to": "Offer", "why": "offer wording and one matching role"})
            else:
                out["ask"].append({**item, "to": "Offer", "why": "could not tie it to one role"})
        elif kind == "interview" and r.get("strong") and resolved and stage in ("Shortlisted", "Applied"):
            out["auto"].append({**item, "to": "Interview", "why": "an invitation to speak or schedule"})
        elif r.get("action"):
            out["action"].append(item)
    return out


def _recent(at: str, now: datetime) -> bool:
    try:
        return now - datetime.fromisoformat(at[:19]) <= timedelta(days=INFO_DAYS)
    except ValueError:
        return False


def scan_status(root: Path = ROOT) -> dict:
    try:
        return json.loads((root / STATUS).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def scan_line(root: Path, now: datetime) -> tuple[str, bool]:
    """(CADENCE line for the brief, due). The scan is the Action's job: it is overdue when no good scan is recent."""
    s = scan_status(root)
    if not s:
        return ("  - Application mail scan (GitHub Action): never ran, or the ledger is not in this copy yet · "
                "DUE: check that the JOBALERT_IMAP_USER / JOBALERT_IMAP_PASSWORD secrets exist (run `health`)", True)
    try:
        at = datetime.fromisoformat(s.get("at", "")[:19])
    except ValueError:
        at = None
    ago = f"{int((now - at).total_seconds() // 3600)}h ago" if at else "unknown"
    if not s.get("ok"):
        return (f"  - Application mail scan (GitHub Action): last run {ago} FAILED ({safe(s.get('error'), 100)}) · DUE: run `health`", True)
    if at is None or now - at > timedelta(hours=SCAN_STALE_HOURS):
        return (f"  - Application mail scan (GitHub Action): last good run {ago} · OVERDUE: check the workflow with `health`", True)
    return (f"  - Application mail scan (GitHub Action): last run {ago}, {s.get('watched', 0)} role(s) watched · ok", False)


def brief_lines(root: Path, now: datetime) -> list[str]:
    p = plan(root, now)
    lines: list[str] = []

    def who(i):
        return f"{safe(i['company'], 24)} — {safe(i['title'], 50)}" if i["company"] else "unmatched role"

    if p["auto"]:
        lines.append("- MAIL (auto): the daily mailbox scan found these. Make each move with `track` (Stage + a dated --note, "
                     "and rule 10 for Rejected), tell the user in one line each, then `python tools/app_mail.py ack <id>`:")
        lines += [f"  - [{i['id']}] {who(i)}: {i['type']} email {i['at']} ({safe(i['subject'], 70)}) -> {i['to']}; {i['why']}"
                  for i in p["auto"]]
    if p["ask"]:
        lines.append("- MAIL (ask): suggest these changes and wait for the user's yes (then `track`, then `app_mail.py ack <id>`):")
        lines += [f"  - [{i['id']}] {who(i)}: {i['type']} {i['at']} ({safe(i['subject'], 70)}) -> {i['to']}?; {i['why']}" for i in p["ask"]]
    if p["action"]:
        lines.append("- MAIL (action needed, tell the user first; ack when they say it is dealt with):")
        lines += [f"  - [{i['id']}] {who(i)}: {safe(i['subject'], 80)} ({i['at']}) {i['link']}" for i in p["action"]]
    if p["info"]:
        counts = Counter((safe(i["company"], 20) or "unmatched", i["type"]) for i in p["info"])
        lines.append("- MAIL (received, last few days; nothing to do): " + "; ".join(
            f"{c} {t}" + (f" x{n}" if n > 1 else "") for (c, t), n in counts.items()))
    return lines


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    g = sub.add_parser("ingest")
    g.add_argument("--dir", default=".app_mail")
    p = sub.add_parser("plan")
    p.add_argument("--json", action="store_true")
    a = sub.add_parser("ack")
    a.add_argument("ids", nargs="+")
    a.add_argument("--how", default="dealt-with")
    sub.add_parser("status")
    args = ap.parse_args(argv)
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    if args.cmd == "ingest":
        d = Path(args.dir) if Path(args.dir).is_absolute() else ROOT / args.dir
        try:
            messages = json.loads((d / "messages.json").read_text(encoding="utf-8"))
            fetch_status = json.loads((d / "_status.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            messages, fetch_status = [], {"ok": False, "error": "no fetch output found"}
        new = ingest(ROOT, messages, now) if fetch_status.get("ok") else []
        (ROOT / STATUS).parent.mkdir(parents=True, exist_ok=True)
        (ROOT / STATUS).write_text(json.dumps({k: fetch_status.get(k) for k in ("at", "ok", "error", "fetched", "watched", "mailbox")}
                                              | {"new": len(new)}, indent=1), encoding="utf-8")
        print(f"application mail: {len(new)} new email(s) logged" + ("" if fetch_status.get("ok") else f" (scan failed: {fetch_status.get('error')})"))
    elif args.cmd == "plan":
        result = plan(ROOT, now)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            lines = brief_lines(ROOT, now)
            print("\n".join(lines) or "nothing needs doing")
    elif args.cmd == "ack":
        known = {r["id"] for r in ledger(ROOT)[0]}
        bad = [i for i in args.ids if i not in known]
        if bad:
            print(f"unknown id(s): {', '.join(bad)}")
            return 2
        _append(ROOT, [{"ack": i, "at": now.isoformat(timespec="seconds"), "how": args.how} for i in args.ids])
        print(f"acknowledged {len(args.ids)}")
    else:
        print(scan_line(ROOT, now)[0].strip())
    return 0


if __name__ == "__main__":
    sys.exit(main())
