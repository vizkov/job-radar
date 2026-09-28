"""Keep your job search out of the public template repo.

    python tools/public_template.py export <dest>   # copy a clean template tree to <dest>
    python tools/public_template.py check           # fail if this git repo tracks private files
    python tools/public_template.py drift           # code in this private copy not yet in the template
    python tools/public_template.py publish <template-clone-dir> -m "message"
                                                    # copy that code to a clone of the template, test,
                                                    # check, commit, push; then: git pull template main

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
    "data/pipeline_log.jsonl",    # your application stage history
    "data/pipeline_snapshot.json",
    "docs/reviews.md",            # weekly system-review notes about your search
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


def drift(fetch: bool = True) -> list[str]:
    """Non-private files changed on this branch since it last merged the template."""
    if fetch:
        subprocess.run(["git", "fetch", "-q", "template"], cwd=ROOT, capture_output=True, timeout=60)
    r = subprocess.run(["git", "diff", "--name-only", "template/main...HEAD"], cwd=ROOT,
                       capture_output=True, text=True)
    dirty = subprocess.run(["git", "status", "--porcelain", "--untracked-files=all"], cwd=ROOT,
                           capture_output=True, text=True).stdout.splitlines()
    paths = set(r.stdout.split()) | {line[3:].strip().strip('"') for line in dirty}
    return sorted(p for p in paths if p and not is_private(p) and not any(fnmatch.fnmatch(p, n) for n in NEVER_COPY))


def publish(template_dir: Path, message: str) -> None:
    files = drift()
    if not files:
        print("nothing to publish: the template already has all code changes")
        return
    for rel in files:
        src, dst = ROOT / rel, template_dir / rel
        if src.exists():
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
        elif dst.exists():
            dst.unlink()  # deleted here, delete there
    tests = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider"], cwd=template_dir,
                           capture_output=True, text=True)
    if tests.returncode != 0:
        raise SystemExit("tests failed in the template copy; nothing committed:\n" + tests.stdout[-2000:])
    subprocess.run([sys.executable, "tools/public_template.py", "check"], cwd=template_dir, check=True)
    subprocess.run(["git", "add", "-A"], cwd=template_dir, check=True)
    subprocess.run(["git", "commit", "-q", "-m", message], cwd=template_dir, check=True)
    subprocess.run(["git", "push", "-q", "origin", "main"], cwd=template_dir, check=True)
    print(f"published {len(files)} files: {', '.join(files)}\nnow run: git pull template main")


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
    elif len(sys.argv) == 2 and sys.argv[1] == "drift":
        print("\n".join(drift()) or "no unpublished code changes")
    elif len(sys.argv) == 5 and sys.argv[1] == "publish" and sys.argv[3] == "-m":
        publish(Path(sys.argv[2]).resolve(), sys.argv[4])
    else:
        raise SystemExit(__doc__)
