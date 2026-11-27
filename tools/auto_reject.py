"""Move applications with no answer to Rejected after `board.auto_reject_days` days. STANDARD LIBRARY ONLY.

    python tools/auto_reject.py list                  # what is due, waiting or held; changes nothing
    python tools/auto_reject.py run                   # move the due ones (the SessionStart hook and `inbox-check` run this)
    python tools/auto_reject.py hold <ref> --note "…" # the user heard back: never move this one automatically

Off unless `board.auto_reject_days` in profile/config.json is above 0. A card is moved only when all of these hold:
  - it is on the live board in Stage Applied;
  - the days since it was applied to have passed (the first Applied entry of the current run in data/pipeline_log.jsonl,
    else the first application receipt in the mail ledger; with neither, it is listed and left alone);
  - the mailbox was searched for this role on or after the deadline (state/inbox_checked.json), so nobody is rejected unread;
  - no unhandled reply is in the mail ledger, and the user has not put a hold on it.
A moved role is logged with by="auto", its application folder is deleted (CLAUDE.md rule 10), and the mail scan keeps
watching it for late replies (jobradar/application_mail.py).
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))
import app_mail  # noqa: E402
import inbox_outcomes  # noqa: E402

HOLDS = "state/auto_reject_hold.json"
MAX_PER_RUN = 10   # each move is several GitHub calls
_REF = re.compile(r"job-radar:ref=([0-9a-f]{16})")


def _json(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def limit_days(root: Path = ROOT) -> int:
    try:
        return int(_json(root / "profile" / "config.json", {}).get("board", {}).get("auto_reject_days", 0) or 0)
    except (TypeError, ValueError, AttributeError):
        return 0


def _day(text: str) -> date | None:
    try:
        return date.fromisoformat(str(text)[:10])
    except ValueError:
        return None


def applied_since(root: Path, ref: str) -> date | None:
    """When the current Applied run began; with no log entry, the first application receipt the mailbox scan saw."""
    log, records = root / "data" / "pipeline_log.jsonl", []
    if log.exists():
        for line in log.read_text(encoding="utf-8").splitlines():
            try:
                rec = json.loads(line)
            except ValueError:
                continue
            if rec.get("ref") == ref and rec.get("field") == "Stage":
                records.append(rec)
    start = None
    for rec in sorted(records, key=lambda r: str(r.get("at", ""))):
        start = (start or _day(rec.get("at"))) if rec.get("value") == "Applied" else None
    if start:
        return start
    receipts = [d for r in app_mail.ledger(root)[0] if r.get("ref") == ref and r.get("type") == "receipt" if (d := _day(r.get("at")))]
    return min(receipts, default=None)


def unhandled_reply(root: Path, ref: str) -> str:
    """The subject of a reply about this role that nobody has dealt with yet, or ''."""
    rows, acked = app_mail.ledger(root)
    for r in rows:
        if r.get("ref") == ref and r["id"] not in acked and r.get("action") and r.get("type") in ("interview", "offer", "unknown"):
            return app_mail.safe(r.get("subject"), 70)
    return ""


def assess(root: Path, items: list[dict], today: date) -> dict[str, list[dict]]:
    """{"due": [...], "waiting": [...] (past the deadline, mail not searched since), "held": [...], "undated": [...]}."""
    out: dict[str, list[dict]] = {"due": [], "waiting": [], "held": [], "undated": []}
    days = limit_days(root)
    if days <= 0:
        return out
    checked = inbox_outcomes.checked_dates(root / "state" / "inbox_checked.json")
    holds = _json(root / HOLDS, {})
    for i in items:
        hit = _REF.search((i.get("content") or {}).get("body") or "")
        if not hit or i.get("stage") != "Applied":
            continue
        ref = hit.group(1)
        row = {"ref": ref, "title": app_mail.safe(i.get("title"), 80), "item": i}
        since = applied_since(root, ref)
        if since is None:
            out["undated"].append(row)
            continue
        row.update(since=since.isoformat(), days=(today - since).days)
        deadline = since + timedelta(days=days)
        if today < deadline:
            continue
        reply = unhandled_reply(root, ref)
        if ref in holds or reply:
            out["held"].append({**row, "why": holds.get(ref) or f"unhandled reply: {reply}"})
        elif (_day(checked.get(ref, "")) or date.min) < deadline:
            out["waiting"].append(row)
        else:
            out["due"].append(row)
    return out


def remove_folders(root: Path, ref: str) -> list[str]:
    gone = []
    for f in sorted((root / "profile" / "applications").glob("*/tailored.json")):
        if _json(f, {}).get("key") == ref:
            shutil.rmtree(f.parent)
            gone.append(f.parent.name)
    return gone


def run(root: Path, items: list[dict], today: date, gh=None) -> dict[str, list[dict]]:
    """Move the due cards. Returns assess()'s result with "moved" added; `items` are updated in place."""
    result = assess(root, items, today)
    result["moved"] = []
    if not result["due"]:
        return result
    import board_sync
    gh = gh or board_sync.Gh()
    for row in result["due"][:MAX_PER_RUN]:
        note = f"No answer {row['days']} days after applying ({row['since']}): moved automatically. Not a reply from the employer."
        message = board_sync.set_role_fields(gh, row["ref"], {"Stage": "Rejected"}, note=note, by="auto")
        if "Stage=Rejected" not in message:
            result["held"].append({**row, "why": app_mail.safe(message, 120)})
            continue
        row["item"]["stage"] = "Rejected"
        snap_path = root / "data" / "pipeline_snapshot.json"
        snap = _json(snap_path, None)
        if snap is not None:   # so the next session does not report this as a card the user dragged
            snap[row["ref"]] = "Rejected"
            snap_path.write_text(json.dumps(snap, indent=1, sort_keys=True), encoding="utf-8")
        result["moved"].append({**row, "folders": remove_folders(root, row["ref"])})
    return result


def lines(result: dict[str, list[dict]]) -> list[str]:
    out = []
    if result.get("moved"):
        out.append("- AUTO-REJECT: moved to Rejected for no answer (tell the user in one line each, then commit data/ and any removed "
                   "application folder and push, so the mail scan keeps watching for a late reply; no rejection-review):")
        out += [f"  - {r['title']}: {r['days']} days" + (f"; removed {', '.join(r['folders'])}" if r["folders"] else "") for r in result["moved"]]
    if result.get("waiting"):
        out.append(f"- AUTO-REJECT: {len(result['waiting'])} application(s) past the limit wait for a mail search first (`inbox-check`, "
                   "then `python tools/auto_reject.py run`): " + "; ".join(f"{r['title']} ({r['days']} days)" for r in result["waiting"]))
    if result.get("held"):
        out.append("- AUTO-REJECT held (ask the user): " + "; ".join(f"{r['title']}: {r['why']}" for r in result["held"]))
    if result.get("undated"):
        out.append("- AUTO-REJECT: no application date, so left alone (ask the user when they applied): "
                   + "; ".join(r["title"] for r in result["undated"]))
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list")
    sub.add_parser("run")
    h = sub.add_parser("hold")
    h.add_argument("ref")
    h.add_argument("--note", required=True)
    args = ap.parse_args(argv)
    if args.cmd == "hold":
        holds = _json(ROOT / HOLDS, {})
        holds[args.ref] = args.note
        (ROOT / HOLDS).parent.mkdir(parents=True, exist_ok=True)
        (ROOT / HOLDS).write_text(json.dumps(holds, indent=1, ensure_ascii=False), encoding="utf-8")
        print(f"{args.ref}: held")
        return 0
    if limit_days() <= 0:
        print("automatic rejection is off (board.auto_reject_days is 0)")
        return 0
    from session_brief import board_items, run as gh_run
    items, note = board_items(ROOT, gh_run)
    if items is None:
        print(f"board unreadable ({note}); try again in a minute")
        return 1
    today = datetime.now(timezone.utc).date()
    if args.cmd == "run":
        result = run(ROOT, items, today)
    else:
        result = assess(ROOT, items, today)
        for r in result["due"]:
            print(f"due: {r['ref']} {r['title']} (applied {r['since']}, {r['days']} days)")
    print("\n".join(lines(result)) or ("" if result["due"] else "nothing to do"))
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
