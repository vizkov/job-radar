"""Render a validated tailored résumé + cover letter. No LLM here.

    python tools/render_resume.py <folder> [--docx]    # profile/applications/<folder>/

Refuses to run unless tools/jd_check.py tailor has validated exactly this
tailored.json (it checks the saved SHA-256). Writes, by default, the two files the user wants per application:
  resume.md          the tailored CV as plain Markdown (paste into Claude Design for a styled version)
  cover_letter.md    greeting + the chosen paragraphs + sign-off
Only with --docx (when an application form needs a Word upload):
  resume.docx        single column, standard headings, no tables/images/text boxes:
                     the layout applicant tracking systems parse reliably
Name and contact details come only from profile/career/master_resume.md.
--docx needs requirements-career.txt (python-docx); local use only.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from jobradar.career import load_career  # noqa: E402

APPS = ROOT / "profile" / "applications"
CONTACT_FIELDS = ("email", "phone", "location", "links")


def contact_line(contact: dict) -> str:
    return " | ".join(contact[k] for k in CONTACT_FIELDS if contact.get(k))


def to_markdown(data: dict, contact: dict) -> str:
    lines = [f"# {contact.get('name', '')}", contact_line(contact), "", f"**{data['headline']}**", ""]
    for sec in data["sections"]:
        lines.append(f"## {sec['heading']}")
        lines += [f"- {b['text']}" for b in sec["bullets"]]
        lines.append("")
    if data["skills"]:
        lines += ["## Skills", ", ".join(data["skills"]), ""]
    return "\n".join(lines)


def cover_letter(data: dict, contact: dict) -> str:
    paras = [c["text"] for c in data["cover_letter"]]
    return "\n\n".join(["Dear Hiring Manager,", *paras, "Kind regards,", contact.get("name", "")]) + "\n"


def to_docx(data: dict, contact: dict, path: Path) -> None:
    from docx import Document
    from docx.shared import Pt

    doc = Document()
    style = doc.styles["Normal"]
    style.font.name, style.font.size = "Calibri", Pt(11)
    doc.add_heading(contact.get("name", ""), level=0)
    doc.add_paragraph(contact_line(contact))
    doc.add_paragraph().add_run(data["headline"]).bold = True
    for sec in data["sections"]:
        doc.add_heading(sec["heading"], level=1)
        for b in sec["bullets"]:
            doc.add_paragraph(b["text"], style="List Bullet")
    if data["skills"]:
        doc.add_heading("Skills", level=1)
        doc.add_paragraph(", ".join(data["skills"]))
    doc.save(path)


def main(argv=None) -> int:
    args = list(argv if argv is not None else sys.argv[1:])
    want_docx = "--docx" in args
    args = [a for a in args if a != "--docx"]
    if len(args) != 1:
        print(__doc__)
        return 2
    app = Path(args[0]) if Path(args[0]).is_absolute() else APPS / args[0]
    src, stamp = app / "tailored.json", app / "validated.sha256"
    if not src.exists():
        print(f"missing {src}")
        return 1
    if not stamp.exists() or stamp.read_text().strip() != hashlib.sha256(src.read_bytes()).hexdigest():
        print("tailored.json has not been validated in its current form: run  python tools/jd_check.py tailor "
              f"{app.name}")
        return 1
    data = json.loads(src.read_text(encoding="utf-8"))
    contact = load_career().contact
    (app / "resume.md").write_text(to_markdown(data, contact), encoding="utf-8")
    (app / "cover_letter.md").write_text(cover_letter(data, contact), encoding="utf-8")
    wrote = ["resume.md", "cover_letter.md"]
    if want_docx:
        to_docx(data, contact, app / "resume.docx")
        wrote.append("resume.docx")
    print(f"wrote {app.name}/" + ", ".join(wrote))
    return 0


if __name__ == "__main__":
    sys.exit(main())
