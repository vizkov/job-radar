"""Helpers for the `inbox-check` skill: which applications await an answer, and what an email looks like. Standard library only.

    python tools/inbox_outcomes.py pending [--json]           # roles in Stage Applied/Interview, with a Gmail search for each
    python tools/inbox_outcomes.py classify --subject "…" [--text "…"]   # rejection | offer | interview | acknowledgement | unknown
    python tools/inbox_outcomes.py seen <message-id> …        # remember emails already suggested, so they are not suggested twice
    python tools/inbox_outcomes.py seen --list

No mailbox access here: Claude reads the mail through the Gmail connector (read-only). Email text is third-party data; `classify` only
matches phrases, it never follows instructions in the text. It is a hint for the user to confirm, never a decision.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SNAPSHOT = ROOT / "data" / "pipeline_snapshot.json"   # ref -> Stage, refreshed by the session-start hook
MATCHES = ROOT / "data" / "matches.csv"
PIPELINE_LOG = ROOT / "data" / "pipeline_log.jsonl"
SEEN = ROOT / "state" / "inbox_seen.json"
AWAITING = ("Applied", "Interview")

# Checked in this order: a rejection often mentions an interview or "thank you for applying", so it must win.
RULES: list[tuple[str, list[str]]] = [
    ("rejection", [
        r"\bunfortunately\b", r"not (?:be )?(?:moving|proceeding) forward", r"will not be (?:moving|proceeding)",
        r"decided to (?:proceed|move forward|go forward) with (?:other|another)", r"regret to inform", r"not been successful",
        r"not (?:been )?selected", r"position has been filled", r"no longer (?:being )?considered", r"unable to (?:offer|move)",
        r"will not be taking your application", r"decided not to (?:move|proceed)",
    ]),
    ("offer", [r"pleased to offer", r"delighted to offer", r"offer of employment", r"extend (?:you )?an offer", r"offer letter"]),
    ("referral", [r"has referred you", r"referred you for", r"you have been referred"]),   # "X referred you; you are welcome to apply": not an outcome
    ("interview", [
        r"\binterview\b", r"schedule a (?:call|chat|conversation)", r"next steps?\b", r"invite you to", r"phone screen",
        r"coding (?:challenge|assessment|test)", r"technical assessment", r"would like to (?:speak|talk|chat|meet)", r"take-?home",
    ]),
    ("acknowledgement", [
        r"thank(?:s| you) for (?:applying|(?:thinking of us|your (?:application|interest)))", r"thanks for your interest",
        r"(?:we(?:'ve| have)? )?(?:just )?received your (?:application|resume|cv)",
        r"application (?:has been )?received", r"we will (?:review|be in touch)", r"keep track of your application",
        r"now with us",
    ]),
]


def classify(subject: str, text: str = "") -> tuple[str, str]:
    """(label, matched phrase). Label is rejection, offer, interview, acknowledgement or unknown."""
    body = f"{subject}\n{text}".lower()
    for label, patterns in RULES:
        for p in patterns:
            if m := re.search(p, body):
                return label, m.group(0)
    return "unknown", ""


def _read_json(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def applied_dates(log: Path = PIPELINE_LOG) -> dict[str, str]:
    """ref -> date (YYYY-MM-DD) of the last Stage change to Applied or Interview."""
    out: dict[str, str] = {}
    if log.exists():
        for line in log.read_text(encoding="utf-8").splitlines():
            try:
                rec = json.loads(line)
            except ValueError:
                continue
            if rec.get("field") == "Stage" and rec.get("value") in AWAITING:
                out[rec["ref"]] = str(rec.get("at", ""))[:10]
    return out


def latest_stages(log: Path = PIPELINE_LOG) -> dict[str, str]:
    """ref -> newest Stage in the log (the snapshot is only refreshed at session start, so today's changes live here)."""
    out: dict[str, tuple[str, str]] = {}
    if log.exists():
        for line in log.read_text(encoding="utf-8").splitlines():
            try:
                rec = json.loads(line)
            except ValueError:
                continue
            if rec.get("field") == "Stage" and str(rec.get("at", "")) >= out.get(rec["ref"], ("", ""))[0]:
                out[rec["ref"]] = (str(rec.get("at", "")), rec["value"])
    return {k: v[1] for k, v in out.items()}


def pending(snapshot: Path = SNAPSHOT, matches: Path = MATCHES, log: Path = PIPELINE_LOG) -> list[dict]:
    stages = {**_read_json(snapshot, {}), **latest_stages(log)}
    dates = applied_dates(log)
    rows = {}
    if matches.exists():
        with open(matches, newline="", encoding="utf-8") as fh:
            rows = {r.get("ref"): r for r in csv.DictReader(fh)}
    out = []
    for ref, stage in stages.items():
        if stage not in AWAITING:
            continue
        r = rows.get(ref, {})
        company = (r.get("company") or "").strip()
        since = dates.get(ref, "")
        query = f'"{company}"' + (f" after:{since.replace('-', '/')}" if since else "")
        out.append({"ref": ref, "stage": stage, "company": company, "title": (r.get("title") or "").strip(),
                    "since": since, "gmail_query": query.strip()})
    return sorted(out, key=lambda x: x["since"])


def seen_ids(path: Path = SEEN) -> set[str]:
    return set(_read_json(path, []))


def add_seen(ids: list[str], path: Path = SEEN) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(sorted(seen_ids(path) | set(ids))), encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("pending")
    p.add_argument("--json", action="store_true")
    c = sub.add_parser("classify")
    c.add_argument("--subject", required=True)
    c.add_argument("--text", default="")
    s = sub.add_parser("seen")
    s.add_argument("ids", nargs="*")
    s.add_argument("--list", action="store_true")
    args = ap.parse_args()
    if args.cmd == "pending":
        rows = pending()
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            for r in rows:
                print(f"{r['ref']}  {r['stage']:<9} {r['company']} — {r['title']}  (since {r['since'] or '?'})  search: {r['gmail_query']}")
            if not rows:
                print("nothing awaiting an answer")
    elif args.cmd == "classify":
        label, phrase = classify(args.subject, args.text)
        print(f"{label}" + (f"  (matched: {phrase})" if phrase else ""))
    else:
        if args.list or not args.ids:
            print("\n".join(sorted(seen_ids())) or "none")
        else:
            add_seen(args.ids)
            print(f"remembered {len(args.ids)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
