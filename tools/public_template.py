"""Keep your job search out of the public template repo.

    python tools/public_template.py export <dest>   # copy a clean template tree to <dest>
    python tools/public_template.py check           # fail if this git repo tracks private files
    python tools/public_template.py drift           # code in this private copy not yet in the template
    python tools/public_template.py autopublish     # what .githooks/post-commit runs after each commit
    python tools/public_template.py publish <template-clone-dir> -m "message"
                                                    # copy that code to a clone of the template, test,
                                                    # check, commit, push; then: git pull template main

Private = your settings (profile/) and everything a run produces or derives from
your targets: state, digests, matches, the board list and coverage reports.
The template keeps code, docs, tests and examples/. The sponsor registers are public data but
are downloaded per copy (refresh_registers.py), so they're kept out to avoid merge conflicts.
"""
from __future__ import annotations

import fnmatch
import re
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
    "data/usage_log.jsonl",       # how much Claude usage scoring batches took
    "docs/reviews.md",            # weekly system-review notes about your search
    "work/*",                     # fetched job descriptions and Claude's drafts
    ".alert_mail/*",              # fetched alert emails
    "data/registers/*",           # public data, but refreshed weekly in your copy: shipping it would
                                  # make `git pull template main` conflict; fetch with refresh_registers.py
]
NEVER_COPY = [".git/*", ".venv/*", ".claude/settings.local.json", "*/__pycache__/*", "__pycache__/*", ".pytest_cache/*", "atss/*", "agg/*"]


# Only these paths are ever published. A new kind of file (private or not) stays private
# until someone deliberately adds it here: safer than relying on PRIVATE alone.
PUBLIC = [".claude/skills/*", ".claude/settings.json", ".github/*", ".githooks/*", "jobradar/*", "tools/*",
          "tests/*", "docs/wiki/*", "docs/design/*", "examples/*", "CLAUDE.md", "README.md", "radar.py", "verify_boards.py",
          "requirements*.in", "requirements*.txt", "pytest.ini", ".gitignore", ".gitattributes"]


def is_private(rel: str) -> bool:
    return any(fnmatch.fnmatch(rel, pat) for pat in PRIVATE)


def is_public(rel: str) -> bool:
    return (any(fnmatch.fnmatch(rel, pat) for pat in PUBLIC) and not is_private(rel)
            and not any(fnmatch.fnmatch(rel, n) for n in NEVER_COPY))


def export(dest: Path) -> None:
    if dest.exists() and any(dest.iterdir()):
        raise SystemExit(f"{dest} is not empty")
    copied = skipped = 0
    for f in sorted(ROOT.rglob("*")):
        rel = f.relative_to(ROOT).as_posix()
        if f.is_dir() or any(fnmatch.fnmatch(rel, p) for p in NEVER_COPY):
            continue
        if not is_public(rel):  # same allowlist as publish(): unknown kinds of file stay out
            skipped += 1
            continue
        (dest / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(f, dest / rel)
        copied += 1
    print(f"copied {copied} files to {dest}, left out {skipped} private or unlisted files")


def drift(fetch: bool = True) -> list[str]:
    """Non-private files changed on this branch since it last merged the template."""
    if fetch:
        subprocess.run(["git", "fetch", "-q", "template"], cwd=ROOT, capture_output=True, timeout=60)
    # --no-renames: a moved file must show under its old path too, or publish never deletes it there
    r = subprocess.run(["git", "diff", "--name-only", "--no-renames", "template/main...HEAD"], cwd=ROOT,
                       capture_output=True, text=True)
    dirty = subprocess.run(["git", "status", "--porcelain", "--untracked-files=all"], cwd=ROOT,
                           capture_output=True, text=True).stdout.splitlines()
    paths = set(r.stdout.splitlines()) | status_paths(dirty)
    return sorted(p for p in paths if p and is_public(p))


def status_paths(lines: list[str]) -> set[str]:
    """Paths from `git status --porcelain`; a rename ("R  old -> new") yields both."""
    out = set()
    for line in lines:
        for part in line[3:].split(" -> "):
            out.add(part.strip().strip('"'))
    return out


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


def autopublish() -> None:
    """Run by .githooks/post-commit: publish public code changes, then merge the template back.
    Never raises: a commit must not fail because publishing did."""
    try:
        cfg = subprocess.run(["git", "config", "jobradar.templateDir"], cwd=ROOT, capture_output=True, text=True)
        template_dir = Path(cfg.stdout.strip()) if cfg.stdout.strip() else None
        if not template_dir or not (template_dir / ".git").exists():
            return  # not configured (e.g. someone else's copy): silently skip
        if not drift():
            return
        subject = subprocess.run(["git", "log", "-1", "--format=%s"], cwd=ROOT, capture_output=True,
                                 text=True).stdout.strip()
        publish(template_dir, f"{subject}\n\n(auto-published from a private job-radar copy)")
        subprocess.run(["git", "pull", "-q", "--no-rebase", "--no-edit", "template", "main"], cwd=ROOT)
        mirror_wiki(template_dir)
    except BaseException as e:  # includes SystemExit from failed tests
        print(f"job-radar autopublish skipped: {e}")


def wiki_text(text: str, blob_base: str) -> str:
    """docs/wiki page -> GitHub Wiki page: sibling links drop .md, links into the repo become absolute."""
    text = re.sub(r"\]\((?:\.\./)+([^)]+)\)",lambda m: f"]({blob_base}/docs/{m.group(1)})", text)
    return re.sub(r"\]\(([A-Za-z0-9-]+)\.md(#[^)]*)?\)", lambda m: f"]({m.group(1)}{m.group(2) or ''})", text)


def mirror_wiki(template_dir: Path) -> None:
    """Copy docs/wiki/ (the source of truth) into the template's GitHub Wiki tab, for browsing.
    No-op until the wiki exists (GitHub creates its git repo when the first page is saved in the UI)."""
    url = subprocess.run(["git", "remote", "get-url", "origin"], cwd=template_dir, capture_output=True,
                         text=True).stdout.strip()
    if not url.endswith(".git"):
        return
    wiki_dir = template_dir.parent / (template_dir.name + ".wiki")
    if not (wiki_dir / ".git").exists():
        if subprocess.run(["git", "clone", "-q", url[:-4] + ".wiki.git", str(wiki_dir)],
                          capture_output=True).returncode != 0:
            return
    subprocess.run(["git", "pull", "-q"], cwd=wiki_dir, capture_output=True)
    blob_base = url[:-4] + "/blob/main"
    for page in (ROOT / "docs" / "wiki").glob("*.md"):
        (wiki_dir / page.name).write_text(wiki_text(page.read_text(encoding="utf-8"), blob_base), encoding="utf-8")
    for old in wiki_dir.glob("*.md"):
        if not (ROOT / "docs" / "wiki" / old.name).exists():
            old.unlink()
    subprocess.run(["git", "add", "-A"], cwd=wiki_dir, check=True)
    if subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=wiki_dir).returncode != 0:
        subprocess.run(["git", "commit", "-q", "-m", "Mirror docs/wiki"], cwd=wiki_dir, check=True)
        subprocess.run(["git", "push", "-q"], cwd=wiki_dir, check=True)
        print("wiki tab updated from docs/wiki")


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
    elif len(sys.argv) == 2 and sys.argv[1] == "autopublish":
        autopublish()
    elif len(sys.argv) == 2 and sys.argv[1] == "drift":
        print("\n".join(drift()) or "no unpublished code changes")
    elif len(sys.argv) == 5 and sys.argv[1] == "publish" and sys.argv[3] == "-m":
        publish(Path(sys.argv[2]).resolve(), sys.argv[4])
    else:
        raise SystemExit(__doc__)
