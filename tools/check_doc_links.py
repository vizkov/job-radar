"""Check documentation links. Standard library only.

    python check_doc_links.py [repo_root]

1. Every relative Markdown link  ](target)  in docs/**/*.md, README.md, CLAUDE.md and
   .claude/skills/**/*.md points at a file that exists.
2. Every  docs/<folder>/<Page>.md  path mentioned in code, config or docs exists.
Exit code 1 if anything is broken.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

LINK = re.compile(r"\]\(([^)]*)\)")  # any target, so a space inside one is caught too
DOC_PATH = re.compile(r"docs/[A-Za-z0-9_-]+/[A-Za-z0-9_.-]+\.md")
SKIP_DIRS = {".git", ".venv", "venv", "node_modules", "__pycache__", "tests"}
SCAN_SUFFIXES = {".md", ".py", ".yaml", ".yml", ".json", ".toml", ".ts", ".js"}


def main(root: Path) -> int:
    bad = []
    md_files = [*root.glob("docs/**/*.md"), *root.glob(".claude/skills/**/*.md")]
    md_files += [p for p in (root / "README.md", root / "CLAUDE.md") if p.exists()]
    for f in md_files:
        for m in LINK.finditer(f.read_text(encoding="utf-8")):
            target = m.group(1).strip().split("#", 1)[0]
            if not target or target.startswith(("http://", "https://", "mailto:")) or target in ("…", "..."):
                continue
            if " " in target or not (f.parent / target).resolve().exists():
                bad.append(f"{f.relative_to(root)} -> {target}")
    for f in root.rglob("*"):
        if f.is_file() and f.suffix in SCAN_SUFFIXES and not (SKIP_DIRS & set(f.relative_to(root).parts)):
            for m in DOC_PATH.finditer(f.read_text(encoding="utf-8", errors="ignore")):
                if not (root / m.group(0)).exists():
                    bad.append(f"{f.relative_to(root)} mentions {m.group(0)}")
    print("\n".join(sorted(set(bad))) or "ok: all doc links resolve")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()))
