"""Trim the JD packets (work/jd/<ref>/) of roles you are done with, so the folder does not keep growing.

    python tools/jd_cleanup.py list      # what would be removed, and why (changes nothing)
    python tools/jd_cleanup.py run       # remove it, stamp the cadence job, and print one line

A role's folder keeps its verdicts for good: `score.json`, `meta.json` and `sponsorship.json` are small and are never touched. The bulky
files, `jd.txt` and `packet.md` (the packet only wraps the same text), are removed once the role is done with:

  * Stage Skipped: 14 days after it was skipped;
  * Stage Rejected: 30 days after the rejection (long enough to look at what the ad asked and the CV lacked);
  * scored `skip` with no card or stage change at all: 14 days after the score.

Roles in any other stage (New, Shortlisted, Applied, Interview, Offer) are never touched. The days can be changed in
`profile/config.json`: {"cleanup": {"skipped_days": 14, "rejected_days": 30}}. The SessionStart hook runs this daily; a removed `jd.txt` can be
fetched again by `jd_prep.py --ref <ref>` if a role is ever restored.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
import cadence  # noqa: E402

BULK = ("jd.txt", "packet.md")
DEFAULT_DAYS = {"Skipped": 14, "Rejected": 30, "skip-scored": 14}


def _days(root: Path) -> dict[str, int]:
    days = dict(DEFAULT_DAYS)
    try:
        cfg = json.loads((root / "profile" / "config.json").read_text(encoding="utf-8")).get("cleanup", {})
        days["Skipped"] = int(cfg.get("skipped_days", days["Skipped"]))
        days["skip-scored"] = int(cfg.get("skipped_days", days["skip-scored"]))
        days["Rejected"] = int(cfg.get("rejected_days", days["Rejected"]))
    except (OSError, ValueError, TypeError, AttributeError):
        pass
    return days


def _stage_log(root: Path) -> dict[str, tuple[str, datetime]]:
    """ref -> (latest Stage, when it was set), from data/pipeline_log.jsonl."""
    out: dict[str, tuple[str, datetime]] = {}
    path = root / "data" / "pipeline_log.jsonl"
    if not path.exists():
        return out
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            r = json.loads(line)
        except ValueError:
            continue
        if r.get("field") == "Stage" and r.get("ref") and r.get("value"):
            at = cadence._naive(r.get("at", ""))
            if at:
                out[r["ref"]] = (r["value"], at)
    return out


def _skip_scored(root: Path) -> set[str]:
    out: set[str] = set()
    path = root / "data" / "scores.jsonl"
    if not path.exists():
        return out
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            r = json.loads(line)
        except ValueError:
            continue
        ref = r.get("ref") or r.get("key")
        if ref and (r.get("recommendation") or r.get("rec")) == "skip":
            out.add(ref)
    return out


def candidates(root: Path = ROOT, now: datetime | None = None) -> list[dict]:
    """[{ref, reason, since, files}]: folders whose bulky files are past their retention."""
    now = now or datetime.now(timezone.utc).replace(tzinfo=None)
    work = root / "work" / "jd"
    if not work.exists():
        return []
    days, stages, skips = _days(root), _stage_log(root), _skip_scored(root)
    out = []
    for folder in sorted(p for p in work.iterdir() if p.is_dir()):
        files = [folder / f for f in BULK if (folder / f).exists()]
        if not files:
            continue
        ref = folder.name
        stage = stages.get(ref)
        if stage and stage[0] in ("Skipped", "Rejected"):
            reason, since = stage[0], stage[1]
        elif not stage and ref in skips and (folder / "score.json").exists():
            reason, since = "skip-scored", datetime.fromtimestamp((folder / "score.json").stat().st_mtime)
        else:
            continue
        if now - since >= timedelta(days=days[reason]):
            out.append({"ref": ref, "reason": reason, "since": since, "files": files,
                        "bytes": sum(f.stat().st_size for f in files)})
    return out


def run(root: Path = ROOT, now: datetime | None = None, dry: bool = False) -> str:
    now = now or datetime.now(timezone.utc).replace(tzinfo=None)
    found = candidates(root, now)
    freed = sum(c["bytes"] for c in found)
    if not dry:
        for c in found:
            for f in c["files"]:
                f.unlink(missing_ok=True)
        cadence.done("jd_cleanup", root, now)
    verb = "would remove" if dry else "removed"
    return (f"JD packets: {verb} jd.txt and packet.md for {len(found)} done role(s) ({freed / 1024:.0f} KB); "
            "score.json, meta.json and sponsorship.json are kept") if found else "JD packets: nothing past its retention"


def main(argv=None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if args[:1] == ["list"]:
        for c in candidates():
            print(f"{c['ref']}  {c['reason']:<11} since {c['since']:%Y-%m-%d}  {c['bytes'] / 1024:.0f} KB")
        print(run(dry=True))
        return 0
    if args[:1] == ["run"]:
        print(run())
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main())
