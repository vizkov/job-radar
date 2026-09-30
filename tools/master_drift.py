"""Which applications no longer match the master career documents?

    python tools/master_drift.py            # every application folder with a tailored.json

Tailored lines are copies of master lines (P/B/K/E in the CV, C/S in the letter). When the user
changes the master CV, cover blocks or stories, an application built earlier may be stale. Per
application this prints:

  * STALE: the master files changed after resume.pdf was rendered
  * MISSING: a cited ID no longer exists in the master
  * DIFFERS: the tailored text is under 90% similar to the master line (a deliberate condensation
    or relabel is normal; a master edit is what the reviewer should look for)

Output is candidates for judgement (the `master-update` skill), not verdicts. Read-only.
"""
from __future__ import annotations

import argparse
import difflib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from jobradar.career import career_dir, load_career  # noqa: E402

APPS = ROOT / "profile" / "applications"
MASTER_FILES = ("master_resume.md", "cover_blocks.md", "stories.md")
SIMILAR = 0.90


def check_app(app: Path, career, master_mtime: float) -> dict:
    data = json.loads((app / "tailored.json").read_text(encoding="utf-8"))
    lines = [b for s in data.get("sections", []) for b in s.get("bullets", [])] + data.get("cover_letter", [])
    missing = sorted({b["source_id"] for b in lines if not career.has(b["source_id"])})
    differs = []
    for b in lines:
        if career.has(b["source_id"]):
            src = career.items[b["source_id"]].text
            ratio = difflib.SequenceMatcher(None, src.lower(), b["text"].lower()).ratio()
            if ratio < SIMILAR:
                differs.append((b["source_id"], round(ratio * 100)))
    pdf = app / "resume.pdf"
    stale = pdf.exists() and master_mtime > pdf.stat().st_mtime
    return {"folder": app.name, "stale": stale, "missing": missing, "differs": differs}


def main() -> int:
    argparse.ArgumentParser(description=__doc__.split("\n")[0]).parse_args()
    career = load_career()
    master_mtime = max((career_dir() / f).stat().st_mtime for f in MASTER_FILES if (career_dir() / f).exists())
    apps = sorted(p for p in APPS.glob("*/") if (p / "tailored.json").exists()) if APPS.exists() else []
    if not apps:
        print("no tailored applications")
        return 0
    for app in apps:
        r = check_app(app, career, master_mtime)
        flags = ("STALE " if r["stale"] else "") + ("MISSING " if r["missing"] else "")
        print(f"{r['folder']}: {flags or 'ok '}".rstrip())
        if r["missing"]:
            print(f"  MISSING ids: {', '.join(r['missing'])}")
        if r["differs"]:
            print("  DIFFERS from master (id, % similar): " + ", ".join(f"{i} {p}" for i, p in r["differs"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
