"""job-radar manual: everything the system can do, generated from the skills and tools themselves.

    python tools/manual.py            # full manual
    python tools/manual.py skills     # just "what can I ask for"

STANDARD LIBRARY ONLY. Because it reads .claude/skills/*/SKILL.md and each tool's docstring,
it stays current whenever a capability is added or changed; there's nothing to update by hand.
"""
from __future__ import annotations

import ast
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

INTRO = """job-radar has two interfaces:
  1. Claude (this conversation): ask in plain words; Claude runs everything below for you.
  2. Your GitHub Projects board: every new role is a card; move it New -> Offer.
The scheduled GitHub Action finds new roles 3x a day and puts them on the board."""


def skills() -> list[tuple[str, str]]:
    out = []
    for f in sorted((ROOT / ".claude" / "skills").glob("*/SKILL.md")):
        text = f.read_text(encoding="utf-8")
        name = re.search(r"^name:\s*(.+)$", text, re.M)
        desc = re.search(r"^description:\s*(.+)$", text, re.M)
        if name and desc:
            out.append((name.group(1).strip(), desc.group(1).strip()))
    return out


def tools() -> list[tuple[str, str]]:
    out = []
    for f in sorted([ROOT / "radar.py", ROOT / "verify_boards.py", *(ROOT / "tools").glob("*.py")]):
        try:
            doc = ast.get_docstring(ast.parse(f.read_text(encoding="utf-8"))) or ""
        except SyntaxError:
            continue
        first = doc.strip().splitlines()[0] if doc.strip() else ""
        out.append((str(f.relative_to(ROOT)).replace("\\", "/"), first))
    return out


def wrap(text: str, width: int = 96, indent: str = "      ") -> str:
    words, lines, line = text.split(), [], ""
    for w in words:
        if len(line) + len(w) + 1 > width - len(indent):
            lines.append(line)
            line = w
        else:
            line = f"{line} {w}".strip()
    lines.append(line)
    return "\n".join(indent + l for l in lines)


def paint(color: bool):
    """ANSI colours only for a real terminal (never when Claude reads the output); NO_COLOR disables."""
    def c(code: str, text: str) -> str:
        return f"[{code}m{text}[0m" if color else text
    return c


def main(argv=None, color: bool | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    if color is None:
        color = sys.stdout.isatty() and not os.environ.get("NO_COLOR")
    c = paint(color)
    out = []
    if not args:
        out += [c("1;36", "JOB-RADAR MANUAL"), "", INTRO, ""]
    out += [c("1;33", "WHAT YOU CAN ASK FOR") + " (skills; Claude picks the right one from what you say)", ""]
    for name, desc in skills():
        out += ["  " + c("1;32", name), wrap(desc), ""]
    if not args:
        out += [c("1;33", "TOOLS CLAUDE RUNS FOR YOU") + " (you never need to)", ""]
        out += ["  " + c("36", f"{path:32}") + f" {first}" for path, first in tools()]
        wiki = sorted(p.stem for p in (ROOT / "docs" / "wiki").glob("*.md"))
        out += ["", c("1;33", "MORE DETAIL"), f"  Your guide, docs/wiki/: {', '.join(wiki)}; how it works inside: docs/design/",
                "  Board: your GitHub Project (views: All Roles table, Pipeline board)."]
    print("\n".join(out))
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
