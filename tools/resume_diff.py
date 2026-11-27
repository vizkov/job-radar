"""What a tailored CV changes compared with the general resume. STANDARD LIBRARY ONLY, no model.

    python tools/resume_diff.py <folder>      # a folder name under profile/applications/, or a path

Compares the two tailored.json files line by line, matched on the master line ID: reworded, added, left out (with the
recorded reason), moved within a section, and changes to the headline, the skills list and the bold highlights. Unchanged
lines are only counted. Prints Markdown for the chat. The general resume is profile/general-resume/tailored.json.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
APPS = ROOT / "profile" / "applications"
GENERAL = ROOT / "profile" / "general-resume"


def _lines(data: dict) -> dict[str, str]:
    return {b["source_id"]: b["text"] for s in data.get("sections", []) for b in s["bullets"]}


def _moves(general: dict, tailored: dict) -> list[str]:
    """Per section, the new order of the lines both have, when it differs."""
    base = [[b["source_id"] for b in s["bullets"]] for s in general.get("sections", [])]
    out = []
    for section in tailored.get("sections", []):
        ids = [b["source_id"] for b in section["bullets"]]
        for old in base:
            was, now = [i for i in old if i in ids], [i for i in ids if i in old]
            if was != now:
                out.append(f"- {section['heading']}: {', '.join(was)} → {', '.join(now)}")
    return out


def _listed(title: str, general: list, tailored: list) -> list[str]:
    added, removed = [x for x in tailored if x not in general], [x for x in general if x not in tailored]
    out = []
    if added:
        out.append(f"- {title} added: {', '.join(added)}")
    if removed:
        out.append(f"- {title} removed: {', '.join(removed)}")
    if not out and general != tailored:
        out.append(f"- {title} reordered: {', '.join(tailored)}")
    return out


def diff(general: dict, tailored: dict) -> str:
    a, b = _lines(general), _lines(tailored)
    changed = [i for i in b if i in a and a[i] != b[i]]
    added = [i for i in b if i not in a]
    removed = [i for i in a if i not in b]
    reasons = tailored.get("dropped") or {}
    out = [f"**Against the general resume:** {len(changed)} reworded, {len(added)} added, {len(removed)} left out, "
           f"{len(a) - len(changed) - len(removed)} unchanged."]
    if general.get("headline") != tailored.get("headline"):
        out += ["", "**Headline**", f"- general: {general.get('headline')}", f"- tailored: {tailored.get('headline')}"]
    if changed:
        out += ["", "**Reworded**"]
        for i in changed:
            out += [f"- **{i}**", f"  - general: {a[i]}", f"  - tailored: {b[i]}"]
    if added:
        out += ["", "**Added**"] + [f"- **{i}**: {b[i]}" for i in added]
    if removed:
        out += ["", "**Left out**"] + [f"- **{i}**: {a[i]}" + (f" _(reason: {reasons[i]})_" if i in reasons else "") for i in removed]
    if moves := _moves(general, tailored):
        out += ["", "**Moved**"] + moves
    extras = _listed("Skills", general.get("skills", []), tailored.get("skills", [])) + \
        _listed("Bold phrases", general.get("highlight", []), tailored.get("highlight", []))
    if extras:
        out += ["", "**Skills list and highlights**"] + extras
    if tailored.get("cover_letter") and not general.get("cover_letter"):
        out += ["", "The cover letter has no general version, so it is not compared."]
    return "\n".join(out)


def main(argv=None) -> int:
    args = list(argv if argv is not None else sys.argv[1:])
    if len(args) != 1:
        print(__doc__)
        return 2
    app = Path(args[0])
    if not (app / "tailored.json").exists():
        app = APPS / args[0]
    loaded = []
    for path in (GENERAL / "tailored.json", app / "tailored.json"):
        if not path.exists():
            print(f"missing {path}")
            return 1
        loaded.append(json.loads(path.read_text(encoding="utf-8")))
    print(diff(*loaded))
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
