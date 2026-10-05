"""Are the master cover blocks in sync with the CV lines and stories they expand?

    python tools/cover_sync.py status   # lists blocks whose CV lines or stories changed since the last recorded sync (exit 1 if any)
    python tools/cover_sync.py done     # record the sync, after reviewing and updating the listed blocks

`profile/career/cover_blocks.md` is a ranked bank: each block has a metadata comment under its heading naming the CV lines it
expands (anchor) and its stories (sources). A change to any of those makes the block stale. `master_drift.py clear` and
`jd_check.py tailor` refuse while any block is stale, so a letter is never built from a block that no longer matches the record.
Blocks without a metadata comment (and the example career) are ignored.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from jobradar.career import cover_blocks_stale, cover_sync_message, record_cover_sync  # noqa: E402


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("action", choices=["status", "done"])
    args = ap.parse_args(argv)
    if args.action == "done":
        print(f"cover blocks recorded as in sync with the CV and stories ({record_cover_sync()} blocks)")
        return 0
    stale = cover_blocks_stale()
    print("cover blocks in sync with the CV and stories" if not stale else cover_sync_message(stale))
    return 1 if stale else 0


if __name__ == "__main__":
    raise SystemExit(main())
