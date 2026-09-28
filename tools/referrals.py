"""Referrals: who the user can ask at a company, and what happened with each ask. Standard library only.

    python tools/referrals.py contacts "<company>"      # people in profile/network.csv who can help there
    python tools/referrals.py ask <ref> --person "Name" [--relation recruiter|hiring_manager] [--channel "…"] [--note "…"]
    python tools/referrals.py result <ref> --person "Name" --status referred|declined|no_reply [--note "…"]
    python tools/referrals.py route <ref> --status finding|none|not_needed [--note "…"]
    python tools/referrals.py pending [--days N]        # asks with no answer for N+ days (default: config)

The user's plan, in order: people they know (family, friends, their network), then strangers
(recruiters, hiring managers). The user messages people they know in their own words; Claude drafts only
messages to strangers. Nothing here contacts anyone.

profile/network.csv (private) holds only who can help where, as the user told it:  name,company,added
(one row per person per company; nothing about how they're related or what they do). Every ask and
result is appended to data/referrals.jsonl (private), and
the board's Referral field plus a comment on the role's issue are updated (tools/board_sync.py).
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))
from jobradar.matching import normalize_words  # noqa: E402  (stdlib-only)
from jobradar.paths import profile_path  # noqa: E402

NETWORK = ROOT / "profile" / "network.csv"
LOG = ROOT / "data" / "referrals.jsonl"
RELATIONS = ["known", "recruiter", "hiring_manager"]   # someone the user knows, or a stranger (drafts only for these)
RELATION_NAMES = {"known": "", "recruiter": "recruiter", "hiring_manager": "hiring manager"}
RESULTS = {"referred": "Referred", "declined": None, "no_reply": None}          # result -> board value
ROUTES = {"finding": "Finding contact", "none": "No route", "not_needed": "Not needed"}
NETWORK_FIELDS = ["name", "company", "added"]


def wait_days() -> int:
    try:
        cfg = json.loads(profile_path("config.json").read_text(encoding="utf-8"))
        return int(cfg.get("referrals", {}).get("wait_days", 4))
    except (OSError, ValueError):
        return 4


def contacts(company: str, network: Path | None = None) -> list[dict]:
    """People who can help at `company`. Loose on purpose (whole-word prefix either way, so
    "Amazon UK Services Ltd" is found for "Amazon"): a wrong suggestion costs a question, a miss costs a referral."""
    network = network or NETWORK
    if not network.exists():
        return []
    key = normalize_words(company)

    def same(other: str) -> bool:
        o = normalize_words(other)
        return bool(key and o) and (o == key or o.startswith(key + " ") or key.startswith(o + " "))
    with open(network, encoding="utf-8", newline="") as fh:
        rows = [r for r in csv.DictReader(fh) if same(r.get("company", ""))]
    return rows  # in the order the user told Claude


def records(log: Path | None = None) -> list[dict]:
    log = log or LOG
    if not log.exists():
        return []
    return [json.loads(line) for line in log.read_text(encoding="utf-8").splitlines() if line.strip()]


def _append(rec: dict, log: Path | None = None) -> None:
    log = log or LOG
    log.parent.mkdir(parents=True, exist_ok=True)
    rec = {**rec, "at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    with open(log, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, ensure_ascii=False) + "\n")


def pending(days: int, now: datetime | None = None, log: Path | None = None) -> list[dict]:
    """Latest record per (ref, person) that is still 'asked' after `days` days."""
    now = now or datetime.now(timezone.utc)
    latest: dict[tuple[str, str], dict] = {}
    for r in records(log):
        if r.get("person"):
            latest[(r["ref"], r["person"])] = r
    out = []
    for r in latest.values():
        at = datetime.fromisoformat(r["at"])
        if r.get("status") == "asked" and now - at >= timedelta(days=days):
            out.append({**r, "days": (now - at).days})
    return sorted(out, key=lambda r: -r["days"])


def _board(ref: str, value: str | None, note: str, gh=None) -> str:
    """Update the card's Referral field (when value is set) and comment the note on the issue."""
    import board_sync
    gh = gh or board_sync.Gh()
    values = {"Referral": value} if value else {}
    if not values:  # nothing to set, but still leave the note on the card
        board = board_sync.load_board()
        item = board_sync.find_item(gh, board, ref) if board else None
        url = ((item or {}).get("content") or {}).get("url")
        if url and note:
            path = board_sync._body_file(note)
            try:
                gh("issue", "comment", url, "--body-file", path)
            finally:
                Path(path).unlink(missing_ok=True)
            return f"{ref}: noted on the card"
        return f"{ref}: no board card yet; logged only"
    return board_sync.set_role_fields(gh, ref, values, note=note)


def ask(ref: str, person: str, relation: str = "known", channel: str = "", note: str = "", gh=None) -> str:
    if relation not in RELATIONS:
        raise SystemExit(f"relation must be one of {', '.join(RELATIONS)}")
    _append({"ref": ref, "person": person, "relation": relation, "channel": channel, "status": "asked", "note": note})
    already = any(r["ref"] == ref and r.get("status") == "referred" for r in records())
    who = f"{person} ({RELATION_NAMES[relation]})" if RELATION_NAMES[relation] else person
    text = f"Referral: asked {who}{' via ' + channel if channel else ''}." + (f" {note}" if note else "")
    return _board(ref, None if already else "Asked", text, gh)


def result(ref: str, person: str, status: str, note: str = "", gh=None) -> str:
    if status not in RESULTS:
        raise SystemExit(f"status must be one of {', '.join(RESULTS)}")
    _append({"ref": ref, "person": person, "status": status, "note": note})
    words = {"referred": "referred you", "declined": "couldn't refer you", "no_reply": "didn't reply"}[status]
    return _board(ref, RESULTS[status], f"Referral: {person} {words}." + (f" {note}" if note else ""), gh)


def route(ref: str, status: str, note: str = "", gh=None) -> str:
    if status not in ROUTES:
        raise SystemExit(f"status must be one of {', '.join(ROUTES)}")
    _append({"ref": ref, "person": "", "status": status, "note": note})
    return _board(ref, ROUTES[status], f"Referral: {ROUTES[status].lower()}." + (f" {note}" if note else ""), gh)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("contacts"); c.add_argument("company")
    a = sub.add_parser("ask"); a.add_argument("ref"); a.add_argument("--person", required=True)
    a.add_argument("--relation", default="known", choices=RELATIONS); a.add_argument("--channel", default="")
    a.add_argument("--note", default="")
    r = sub.add_parser("result"); r.add_argument("ref"); r.add_argument("--person", required=True)
    r.add_argument("--status", required=True, choices=list(RESULTS)); r.add_argument("--note", default="")
    o = sub.add_parser("route"); o.add_argument("ref"); o.add_argument("--status", required=True, choices=list(ROUTES))
    o.add_argument("--note", default="")
    p = sub.add_parser("pending"); p.add_argument("--days", type=int)
    args = ap.parse_args(argv)
    if args.cmd == "contacts":
        people = contacts(args.company)
        print("\n".join(f"{x['name']}"
                        for x in people) or f"no contacts at {args.company} in {NETWORK.relative_to(ROOT)}")
    elif args.cmd == "ask":
        print(ask(args.ref, args.person, args.relation, args.channel, args.note))
    elif args.cmd == "result":
        print(result(args.ref, args.person, args.status, args.note))
    elif args.cmd == "route":
        print(route(args.ref, args.status, args.note))
    else:
        rows = pending(args.days if args.days is not None else wait_days())
        print("\n".join(f"{r['ref']}  {r['person']}, asked "
                        f"{r['days']} days ago" for r in rows) or "no unanswered asks")
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
