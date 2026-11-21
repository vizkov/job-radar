"""What the Chrome sweeps found: one ledger line per finished LinkedIn post search or careers-site read (the user, 2026-11-21: "add roles found to measure").

    python tools/sweep_yield.py report [--days 90]     # per lane and company: runs, hiring posts, roles found, roles added

Written by `post_leads.py searched <key> --found N --added N` and `careers_queue.py done "<company>" --roles N --added N`; never by hand.
`found` = roles in the user's titles and countries the read surfaced, whether or not the radar already had them; `added` = new cards the
read created (through `add_role.py` / `post_leads.py add-role`). A read that finds nothing is still a line, so the cost shows next to the yield.
Private (state/). Standard library only.
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LEDGER = ROOT / "state" / "sweep_yield.jsonl"


def record(lane: str, company: str, hits: int = 0, found: int = 0, added: int = 0, ledger: Path | None = None, now: datetime | None = None) -> None:
    """Append one finished read. lane is "post" or "careers"."""
    ledger = ledger or LEDGER
    row = {"at": (now or datetime.now(timezone.utc)).isoformat(timespec="seconds"), "lane": lane, "company": company,
           "hits": int(hits), "found": int(found), "added": int(added)}
    ledger.parent.mkdir(parents=True, exist_ok=True)
    with ledger.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row) + "\n")


def rows(days: int = 90, ledger: Path | None = None, now: datetime | None = None) -> list[dict]:
    ledger = ledger or LEDGER
    if not ledger.exists():
        return []
    cutoff = ((now or datetime.now(timezone.utc)) - timedelta(days=days)).isoformat()
    out = []
    for line in ledger.read_text(encoding="utf-8").splitlines():
        try:
            r = json.loads(line)
        except ValueError:
            continue
        if r.get("at", "") >= cutoff:
            out.append(r)
    return out


def report(days: int = 90, ledger: Path | None = None, now: datetime | None = None) -> list[str]:
    data = rows(days, ledger, now)
    if not data:
        return ["no sweep reads logged yet (the ledger starts with the first read after 2026-11-21)"]
    lanes: dict[str, dict] = defaultdict(lambda: {"runs": 0, "hits": 0, "found": 0, "added": 0})
    per: dict[tuple, dict] = defaultdict(lambda: {"runs": 0, "hits": 0, "found": 0, "added": 0})
    for r in data:
        for tgt in (lanes[r["lane"]], per[(r["lane"], r["company"])]):
            tgt["runs"] += 1
            for k in ("hits", "found", "added"):
                tgt[k] += int(r.get(k, 0))
    out = [f"last {days} days:"]
    for lane in ("post", "careers"):
        if lane in lanes:
            t = lanes[lane]
            out.append(f"  {lane:8} {t['runs']} reads, {t['hits']} hiring posts, {t['found']} roles found, {t['added']} new cards")
    for (lane, company), t in sorted(per.items(), key=lambda kv: (-kv[1]["added"], -kv[1]["found"], kv[0])):
        out.append(f"    {lane:8} {company[:30]:30} {t['runs']} reads, {t['found']} found, {t['added']} added")
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("report")
    r.add_argument("--days", type=int, default=90)
    a = ap.parse_args(argv)
    print("\n".join(report(a.days)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
