"""Cross-check the CV, cover letter and STAR stories against each other. No LLM here.

    python tools/consistency_check.py                          # the career docs in profile/career/
    python tools/consistency_check.py --folder <application>   # that folder's resume.md + cover_letter.md (or work/apps/<folder>/)
                                                               #   + profile/career/stories.md
    python tools/consistency_check.py --cv a.pdf --cover b.pdf --stories c.md   # explicit files
    add --final to treat leftover placeholders as errors, --json for the fact sheet

Files may be .md, .txt or .pdf (PDFs are read with `pdftotext`, which must be installed).
Pulls out the checkable facts: figures (numbers and percentages with the word after them, spelled-out
numbers converted), years, and names (tools, products, companies), then reports:

  unsupported   a figure, year or name in the cover letter or stories that the other documents never mention
  cv-only       a figure in the CV that no cover paragraph or STAR story backs up (interview risk)
  placeholders  "[Optional", "[Date]", "{company}", "Fill in before using" left in the text

This finds candidates only. Whether two sentences *disagree* (a rating "confirmed" in one document and
"compromised" in another, a tense that overclaims) needs reading: the `application-review` skill has a
subagent do that, and uses this output as its checklist. Exit code 1 when there are unsupported items,
or placeholders with --final.
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from jobradar.career import career_dir  # noqa: E402

WORDS = {"two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8,
         "nine": 9, "ten": 10, "eleven": 11, "twelve": 12, "zero": 0}      # "one" is mostly a pronoun: skipped
_NUM_WORD = "|".join(WORDS)
# "14%", "100+ assessments", "eight assessors", "six years'": a number, an optional + or %, the noun it counts.
FIGURE = re.compile(rf"\b(\d+(?:[.,]\d+)*|{_NUM_WORD})(\+|%)?(?:\s+([A-Za-z][A-Za-z-]+))?", re.I)
YEAR = re.compile(r"\b(?:19|20)\d\d\b")
PLACEHOLDER = re.compile(r"\[Optional|\[Date\]|\[Company|\[Hiring|\[Role|\[One sentence|\[the UK|\[notice|\{[a-z_]+\}"
                         r"|Fill in before using|\bTODO\b|\bTBD\b", re.I)
# Names: acronyms, CamelCase, or a capitalised word that is not the first word of a line or sentence.
NAME = re.compile(r"(?<![.!?]\s)(?<!^)(?<!\n)\b([A-Z][a-z]+(?:[A-Z][a-zA-Z]*)+|[A-Z]{2,}[a-z]*|[A-Z][a-z]+)\b")
STOP_NAMES = {"STAR", "CV", "PDF", "SLA", "SLAs", "Optional", "Kind", "Regards", "Dear", "Hiring", "Manager",
              "Team", "Fortune", "Situation", "Task", "Action", "Result", "Lesson", "Re", "Say", "Name", "Lead",
              "Stop", "Learn", "Two", "Doing", "Keep", "Fill", "Taking", "Speed", "Problem", "Yes", "Wasn", "Classic",
              "Disagree"}
# Words that follow a number but don't say what was counted.
FILLER = {"of", "and", "or", "the", "a", "an", "in", "to", "for", "with", "on", "at", "by", "from", "as", "is",
          "was", "that", "which", "who", "i", "my", "our", "we", "days", "day", "most", "your", "would", "example", "minutes", "minute", "seconds"}
DOCS = ("cv", "cover", "stories")
DASH = "–—-"


def read_doc(path: Path) -> str:
    if path.suffix.lower() == ".pdf":
        exe = shutil.which("pdftotext")
        if not exe:
            sys.exit("pdftotext not found: install poppler, or pass a .md/.txt copy of the PDF")
        return subprocess.run([exe, "-layout", str(path), "-"], capture_output=True, text=True,
                              encoding="utf-8", errors="replace", check=True).stdout
    return path.read_text(encoding="utf-8", errors="replace")


def clean(text: str) -> str:
    """Drop front matter, comments, [Bxx] ID markers, all-caps headings and the STAR story-picker numbers."""
    text = re.sub(r"\A---\n.*?\n---\n", "", text, flags=re.S)
    text = re.sub(r"<!--.*?-->", "", text, flags=re.S)
    text = re.sub(r"\[[BPKESC]\d{2}\]\s*", "", text)
    text = re.sub(r"^#+\s*", "", text, flags=re.M)                                  # markdown heading marks
    text = re.sub(rf"^\s*\d\s+[{DASH}]\s+[A-Z].*$", "", text, flags=re.M)            # "1 - The payment settlement"
    text = re.sub(rf"\s\d\s+[{DASH}]\s+backup\s+\d|\s\d\s*$", "", text, flags=re.M)    # picker-table answers
    keep = [ln for ln in text.splitlines()
            if len(ln) < 4 or sum(c.isupper() for c in ln) < 0.8 * max(1, sum(c.isalpha() for c in ln))]
    return "\n".join(keep)


def figures(text: str) -> dict[str, str]:
    """number -> an example phrase ("eight assessors"), so reports show what was counted."""
    out: dict[str, str] = {}
    for m in FIGURE.finditer(text):
        num, sign, noun = m.group(1).lower().rstrip(".,").replace(",", ""), m.group(2) or "", (m.group(3) or "")
        num = str(WORDS.get(num, num))
        if YEAR.fullmatch(num):
            continue                                   # years are compared separately
        if noun.lower() in FILLER:
            noun = ""
        if not sign and not noun:
            continue                                   # a bare number says little
        out.setdefault(num, f"{m.group(1)}{sign} {noun}".strip())
    return out


def names(text: str) -> set[str]:
    return {n for n in NAME.findall(text) if n not in STOP_NAMES and not n.endswith("ing")}


def facts(text: str) -> dict:
    text = clean(text)
    return {"figures": figures(text), "years": set(YEAR.findall(text)), "names": names(text),
            "placeholders": sorted({m.group(0) for m in PLACEHOLDER.finditer(text)}), "_text": text.lower()}


def compare(docs: dict[str, dict]) -> dict:
    """Per document: facts that appear in no other document (unsupported), plus CV-only figures."""
    findings = {"unsupported": [], "cv-only": [], "placeholders": []}
    for name, f in docs.items():
        others = [docs[o] for o in DOCS if o != name and o in docs]
        other_text = " ".join(o["_text"] for o in others)
        other_nums = set().union(*(set(o["figures"]) for o in others)) if others else set()
        other_years = set().union(*(o["years"] for o in others)) if others else set()
        rows = [("figure", f["figures"][n]) for n in sorted(f["figures"], key=float) if n not in other_nums]
        if name != "cv":                                # the CV is the source of dates and names
            rows += [("year", y) for y in sorted(f["years"] - other_years)]
            rows += [("name", n) for n in sorted(f["names"]) if n.lower() not in other_text]
        for kind, item in rows:
            key = "cv-only" if name == "cv" else "unsupported"
            findings[key].append({"doc": name, "kind": kind, "item": item})
        for p in f["placeholders"]:
            findings["placeholders"].append({"doc": name, "item": p})
    return findings


def locate(args) -> dict[str, Path]:
    if args.folder:
        folder = Path(args.folder)
        folder = folder if folder.is_absolute() or folder.exists() else ROOT / "profile" / "applications" / folder
        scratch = ROOT / "work" / "apps" / folder.name     # render_resume.py writes the review text here
        pick = lambda n: folder / n if (folder / n).exists() else scratch / n  # noqa: E731
        paths = {"cv": pick("resume.md"), "cover": pick("cover_letter.md"),
                 "stories": career_dir() / "stories.md"}
    else:
        paths = {"cv": career_dir() / "master_resume.md", "cover": career_dir() / "cover_blocks.md",
                 "stories": career_dir() / "stories.md"}
    for key in DOCS:
        if getattr(args, key):
            paths[key] = Path(getattr(args, key))
    missing = [f"{k}: {p}" for k, p in paths.items() if not p.exists()]
    if missing:
        sys.exit("missing file(s):\n  " + "\n  ".join(missing))
    return paths


def report(paths: dict[str, Path], findings: dict) -> str:
    lines = ["Consistency check (candidates for review, not verdicts)"]
    lines += [f"  {k:8} {p}" for k, p in paths.items()]
    titles = {"unsupported": "UNSUPPORTED: in the cover letter or stories, but in neither of the other documents",
              "cv-only": "CV-ONLY figures: no cover paragraph or STAR story backs these up",
              "placeholders": "PLACEHOLDERS left in the text"}
    for key, title in titles.items():
        rows = findings[key]
        lines += ["", f"{title} ({len(rows)})"]
        lines += [f"  [{r['doc']}] " + (f"{r['kind']}: " if "kind" in r else "") + r["item"] for r in rows] or ["  none"]
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--folder", help="application folder (name under profile/applications/ or a path)")
    for k in DOCS:
        ap.add_argument(f"--{k}", help=f"explicit {k} file (.md, .txt or .pdf)")
    ap.add_argument("--final", action="store_true", help="placeholders are errors")
    ap.add_argument("--json", action="store_true", help="print the findings and per-document facts as JSON")
    args = ap.parse_args()
    paths = locate(args)
    docs = {k: facts(read_doc(p)) for k, p in paths.items()}
    findings = compare(docs)
    if args.json:
        shown = {k: {a: (sorted(b) if isinstance(b, set) else b) for a, b in f.items() if a != "_text"}
                 for k, f in docs.items()}
        print(json.dumps({"files": {k: str(p) for k, p in paths.items()}, "findings": findings, "facts": shown},
                         indent=2))
    else:
        print(report(paths, findings))
    return 1 if findings["unsupported"] or (args.final and findings["placeholders"]) else 0


if __name__ == "__main__":
    sys.exit(main())
