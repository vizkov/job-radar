"""Keep your job search out of the public template repo.

    python tools/public_template.py export <dest>   # copy a clean template tree to <dest>
    python tools/public_template.py check           # fail if this git repo tracks private files

Private = your settings (profile/) and everything a run produces or derives from
your targets: state, digests, matches, the board list and coverage reports.
The template keeps code, docs, tests, examples/ and the public sponsor registers.
"""
from __future__ import annotations

import fnmatch
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

PRIVATE = [
    "profile/*",                  # your targets, filters, careers pages, aliases
    "state/*",                    # seen postings, source health
    "digests/*",                  # daily digests
    "data/matches.csv",           # every match ever found
    "boards.json",                # derived from your targets
    "data/candidates.csv",        # derived from your targets
    "data/coverage_report.csv",
    "data/verified_boards.csv",
    "data/scores.jsonl",          # your fit scores
    "work/*",                     # fetched job descriptions and Claude's drafts
    ".alert_mail/*",              # fetched alert emails
    "data/registers/*",           # public data, but refreshed weekly in your copy: shipping it would
                                  # make `git pull template main` conflict; fetch with refresh_registers.py
]
NEVER_COPY = [".git/*", ".venv/*", ".claude/settings.local.json", "*/__pycache__/*", "__pycache__/*", ".pytest_cache/*", "atss/*", "agg/*"]


def is_private(rel: str) -> bool:
    return any(fnmatch.fnmatch(rel, pat) for pat in PRIVATE)


def export(dest: Path) -> None:
    if dest.exists() and any(dest.iterdir()):
        raise SystemExit(f"{dest} is not empty")
    copied = skipped = 0
    for f in sorted(ROOT.rglob("*")):
        rel = f.relative_to(ROOT).as_posix()
        if f.is_dir() or any(fnmatch.fnmatch(rel, p) for p in NEVER_COPY):
            continue
        if is_private(rel):
            skipped += 1
            continue
        (dest / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(f, dest / rel)
        copied += 1
    print(f"copied {copied} files to {dest}, left out {skipped} private files")


def check() -> None:
    tracked = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, check=True).stdout.split()
    leaks = [t for t in tracked if is_private(t)]
    if leaks:
        print("Private files tracked in this repo (must not be in the public template):")
        print("\n".join(f"  {t}" for t in leaks))
        raise SystemExit(1)
    print("ok: no private files tracked")


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "export":
        export(Path(sys.argv[2]).resolve())
    elif len(sys.argv) == 2 and sys.argv[1] == "check":
        check()
    else:
        raise SystemExit(__doc__)
