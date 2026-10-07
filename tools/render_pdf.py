"""Render a validated tailored CV and cover letter as PDFs in the user's Claude Design layout. No LLM here.

Called by  python tools/render_resume.py <folder>  (the default output; it first checks the SHA-256 that
tools/jd_check.py tailor saved, so only validated text is rendered). Writes resume.pdf and cover_letter.pdf.

The layout (Arial, A4 CV / US Letter cover letter, teal #005477 headings, a rule under the header, right-aligned
dates on roles; education and volunteering years stay inline so parsers keep them attached) copies the user's Downloads/cv.pdf and cover.pdf. The text is the tailored text; the structure (company,
role, city and dates for each bullet, skill categories, education years) comes from profile/career/master_resume.md,
so nothing is invented. HTML is printed to PDF with headless Chrome or Edge (already on the machine, no extra
packages); the PDF is real text, not an image, so applicant tracking systems can read it.
"""
from __future__ import annotations

import csv
import html
import os
import re
import shutil
import subprocess
import tempfile
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEAL, INK, GREY = "#005477", "#1d1e20", "#44464a"

BROWSERS = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/usr/bin/google-chrome", "/usr/bin/chromium", "/usr/bin/chromium-browser",
]


def esc(s: str) -> str:
    return html.escape(s or "", quote=False)


_MDLINK = re.compile(r"\[([^\]]+)\]\((https?://[^)\s]+)\)")


def rich(s: str) -> str:
    """Escaped text in which [phrase](https://url) becomes a link (the design's teal links)."""
    return _MDLINK.sub(lambda m: f'<a href="{m.group(2)}">{m.group(1)}</a>', esc(s))


def find_browser() -> str | None:
    for name in ("chrome", "google-chrome", "chromium", "msedge"):
        if p := shutil.which(name):
            return p
    return next((b for b in BROWSERS if os.path.exists(b)), None)


def print_pdf(html_text: str, pdf_path: Path) -> None:
    browser = find_browser()
    if not browser:
        raise RuntimeError("no Chrome or Edge found")
    with tempfile.TemporaryDirectory() as tmp:
        src = Path(tmp) / "page.html"
        src.write_text(html_text, encoding="utf-8")
        cmd = [browser, "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
               f"--user-data-dir={Path(tmp) / 'profile'}", f"--print-to-pdf={pdf_path}", src.as_uri()]
        subprocess.run(cmd, check=True, capture_output=True, timeout=90)
    if not pdf_path.exists() or pdf_path.stat().st_size < 1000:
        raise RuntimeError(f"the browser did not write {pdf_path.name}")


# ---------------------------------------------------------------- shared header / helpers

def base(name: str) -> str:
    """Company name without a trailing "(formerly …)"."""
    return re.sub(r"\s*\(.*?\)", "", name).strip()


def all_names(name: str) -> str:
    """"X (formerly part of A, then B)" -> "X / A / B": a role line names every employer the master names."""
    m = re.match(r"(.+?)\s*\((.*?)\)\s*$", name)
    if not m:
        return name
    inner = re.sub(r"^(?:formerly|now|ex-?)\s+(?:part of\s+)?", "", m.group(2).strip(), flags=re.I)
    parts = [x.strip() for x in re.split(r",\s*(?:then\s+)?|\s+then\s+", inner) if x.strip()]
    return " / ".join([m.group(1).strip(), *parts])


SMALL_WORDS = {"and", "or", "of", "for", "the", "to", "in", "on", "a", "an", "with", "at", "by"}


def smart_title(s: str) -> str:
    """Title-case a headline phrase: keep acronyms/mixed case, keep small words lowercase ("AI and Agent Security")."""
    words = s.split()
    return " ".join(w if any(c.isupper() for c in w[1:]) or "/" in w or (i and w.lower() in SMALL_WORDS)
                    else w[:1].upper() + w[1:] for i, w in enumerate(words))


def pretty_headline(h: str) -> str:
    """'Senior X: a, b, c' -> 'Senior X · A · B · C' (the design's middot line)."""
    parts = [p.strip() for p in re.split(r":\s*|,\s*", h) if p.strip()]
    return " · ".join(parts[:1] + [smart_title(p) for p in parts[1:]])


def short_link(url: str) -> str:
    return re.sub(r"^https?://(www\.)?", "", url.strip()).rstrip("/")


def header_html(contact: dict, headline: str) -> str:
    loc = esc(contact.get("location", ""))
    email, phone = contact.get("email", ""), contact.get("phone", "")
    line1 = [loc] if loc else []
    if email:
        line1.append(f'<a href="mailto:{esc(email)}">{esc(email)}</a>')
    if phone:
        line1.append(esc(phone))
    links = [u.strip() for u in contact.get("links", "").split(",") if u.strip()]
    line2 = [f'<a href="{esc(u)}">{esc(short_link(u))}</a>' for u in links]
    return (f'<h1>{esc(contact.get("name", ""))}</h1><div class="headline">{esc(headline)}</div>'
            f'<div class="contact">{"".join(f"<span>{p}</span>" for p in line1)}</div>'
            f'<div class="contact">{"".join(f"<span>{p}</span>" for p in line2)}</div><hr class="rule">')


CSS = f"""
* {{ box-sizing: border-box; }}
body {{ font-family: Arial, Helvetica, sans-serif; color: {INK}; margin: 0; font-size: 10pt; line-height: 1.43; }}
a {{ color: {TEAL}; text-decoration: none; }}
h1 {{ font-size: 23pt; line-height: 1.15; margin: 0; font-weight: bold; }}
.headline {{ color: {TEAL}; font-size: 11.5pt; margin-top: 4pt; line-height: 1.3; }}
.contact {{ color: {GREY}; font-size: 9.5pt; line-height: 1.65; }}
.contact span {{ margin-right: 9pt; white-space: nowrap; }}
.headline + .contact {{ margin-top: 5pt; }}
.rule {{ border: 0; border-top: .75pt solid {INK}; margin: 7pt 0 0; }}
h2 {{ color: {TEAL}; font-size: 9.5pt; letter-spacing: 0; text-transform: uppercase; margin: 10.4pt 0 4pt;
     font-weight: bold; break-after: avoid; }}
p {{ margin: 0; }}
ul {{ margin: 0; padding-left: 12pt; }}
li {{ margin-top: 2.6pt; orphans: 2; widows: 2; }}
ul ul {{ list-style: circle; margin-top: 3pt; }}
.row {{ display: flex; justify-content: space-between; align-items: baseline; gap: 12pt; }}
.row .meta {{ color: {GREY}; white-space: nowrap; }}
.co {{ font-size: 10.5pt; font-weight: bold; }}
.co small {{ font-size: 10pt; font-weight: normal; color: {GREY}; }}
.desc {{ color: {GREY}; font-style: italic; }}
.role {{ margin-top: 7pt; break-inside: avoid; break-after: avoid; }}
.sub {{ color: {GREY}; }}
.block {{ margin-top: 8pt; }}
.block + .block {{ margin-top: 10pt; }}
.skills p {{ margin: 0 0 3pt; padding-left: 0; }}
.skills b {{ font-weight: bold; }}
.edu p {{ margin-top: 2pt; }}
"""


def page(css_extra: str, body: str) -> str:
    return f'<!doctype html><html><head><meta charset="utf-8"><style>{CSS}{css_extra}</style></head><body>{body}</body></html>'


# ---------------------------------------------------------------- resume

def experience_structure(career) -> list[dict]:
    """Companies and roles in master order: [{'company','city','dates','desc_ctx','roles':[{'title','company','dates','ctx'}]}]."""
    ctxs: list[str] = []
    for it in career.items.values():
        if it.id.startswith("B") and it.context and not it.context.startswith(("Projects", "Volunteering")) \
                and it.context not in ctxs:
            ctxs.append(it.context)
    parsed = [(c, [p.strip() for p in c.split(" — ")]) for c in ctxs]
    role_companies = {base(p[1]) for _, p in parsed if len(p) >= 3}
    blocks: list[dict] = []
    for ctx, p in parsed:
        if len(p) == 3 and base(p[0]) in role_companies and not any(b["company"] == p[0] for b in blocks):
            blocks.append({"company": p[0], "city": p[1], "dates": p[2], "desc_ctx": ctx, "roles": []})
        elif len(p) == 4:                      # title — company — city — dates: its own company block
            blocks.append({"company": p[1], "city": p[2], "dates": p[3], "desc_ctx": None,
                           "roles": [{"title": p[0], "company": "", "dates": "", "ctx": ctx}]})
        elif len(p) == 3:                      # title — company — dates
            cur = blocks[-1] if blocks else None
            names = [base(n) for n in p[1].split("/")]   # "A / B / C": the employer under several names
            if cur is None or not any(n in cur["company"] for n in names):
                cur = {"company": p[1], "city": "", "dates": "", "desc_ctx": None, "roles": []}
                blocks.append(cur)
            cur["roles"].append({"title": p[0], "company": all_names(p[1]), "dates": p[2], "ctx": ctx})   # keep "(formerly …)": the master names every employer
    return blocks


def dash(s: str) -> str:
    return s.replace(" to ", " – ")


def split_label(text: str) -> tuple[str, str]:
    if ":" in text:
        a, b = text.split(":", 1)
        return a.strip(), b.strip()
    return "", text.strip()


def resume_html(data: dict, career, contact: dict) -> str:
    chosen = [(b["source_id"], b["text"]) for sec in data["sections"] for b in sec["bullets"]]
    by_id = dict(chosen)

    def of(kind_section: str) -> list[tuple[str, str]]:
        return [(i, t) for i, t in chosen if i[0] == "P" and career.items[i].section == kind_section]

    out = [header_html(contact, pretty_headline(data["headline"]))]
    if profile := of("Summary"):
        out.append('<h2>Profile</h2><p>' + esc(" ".join(t for _, t in profile)) + "</p>")
    if ach := of("Key achievements"):
        lis = []
        for _, t in ach:
            label, rest = split_label(t)
            lis.append(f"<li><b>{esc(label)}:</b> {rich(rest)}</li>" if label else f"<li>{rich(t)}</li>")
        out.append("<h2>Key achievements</h2><ul>" + "".join(lis) + "</ul>")

    exp = []
    for blk in experience_structure(career):
        roles = []
        for r in blk["roles"]:
            ids = [i for i, _ in chosen if i.startswith("B") and career.items[i].context == r["ctx"]]
            if not ids:
                continue
            title = "<span><b>" + esc(r["title"]) + "</b>" + (f'<span class="sub"> · {esc(r["company"])}</span>' if r["company"] else "") + "</span>"
            meta = f'<span class="meta">{esc(dash(r["dates"]))}</span>' if r["dates"] else ""
            head = f'<div class="row role">{title}{meta}</div>'
            roles.append(head + "<ul>" + "".join(f"<li>{rich(by_id[i])}</li>" for i in ids) + "</ul>")
        desc = [by_id[i] for i, _ in chosen if blk["desc_ctx"] and i.startswith("B") and career.items[i].context == blk["desc_ctx"]]
        if not roles and not desc:
            continue
        company = base(blk["company"])
        extra = blk["company"][len(company):].strip()
        meta = " · ".join(p for p in (blk["city"], dash(blk["dates"])) if p)
        head = (f'<div class="row"><span class="co">{esc(company)} <small>{esc(extra)}</small></span>'
                f'<span class="meta">{esc(meta)}</span></div>')
        exp.append('<div class="block">' + head + "".join(f'<div class="desc">{esc(d)}</div>' for d in desc) + "".join(roles) + "</div>")
    if exp:
        out.append("<h2>Experience</h2>" + "".join(exp))

    picked = [i for i, _ in chosen if i.startswith("K")]
    ks = [(i, by_id[i]) for i in picked] or [(it.id, it.text) for it in career.items.values() if it.id.startswith("K")]
    if ks:
        rows = []
        for _, text in ks:
            label, rest = split_label(text)
            rows.append(f"<p><b>{esc(label)}:</b> {esc(rest)}</p>")
        out.append('<h2>Skills</h2><div class="skills">' + "".join(rows) + "</div>")

    proj = [(i, t) for i, t in chosen if i.startswith("B") and career.items[i].context.startswith("Projects")]
    if proj:
        lis = []
        for _, t in proj:
            m = re.match(r"(https?://\S+?):\s+(.*)", t)
            lis.append(f'<li><a href="{esc(m.group(1))}">{esc(short_link(m.group(1)))}</a>: {esc(m.group(2))}</li>'
                       if m else f"<li>{rich(t)}</li>")
        out.append("<h2>Projects &amp; writing</h2><ul>" + "".join(lis) + "</ul>")

    vol = [(i, t) for i, t in chosen if i.startswith("B") and career.items[i].context.startswith("Volunteering")]
    if vol:
        rows = []
        for i, t in vol:
            label, rest = split_label(t)
            year = career.items[i].context.split(" — ")[-1]
            if not label:   # the entry name lives in the master heading, so the line itself need not repeat it
                parts = career.items[i].context.split(" — ")
                label = parts[1] if len(parts) > 1 else parts[0]
            # the year stays in the entry's own text: a right-aligned date column is read as a separate column by text extractors
            # (ATS parsers), which detach it from its entry (found by two ATS readers on 2026-10-07)
            rows.append(f'<p><b>{esc(label)}</b>: {esc(rest.rstrip("."))} ({esc(year)})</p>')   # the year ends the entry, as in Education
        out.append('<h2>Volunteering</h2><div class="edu">' + "".join(rows) + "</div>")

    edu = [(i, t) for i, t in chosen if i[0] == "E"]
    if edu:
        rows = []
        for _, t in edu:   # the master line already carries its years, "(2019 – 2020)": keep them inline (see Volunteering)
            label, rest = split_label(t)
            rows.append(f'<p><b>{esc(label)}</b>{": " + esc(rest) if rest else ""}</p>')
        out.append('<h2>Education</h2><div class="edu">' + "".join(rows) + "</div>")
    return page("@page { size: A4; margin: 35.4pt 43pt 30pt 43pt; }", "".join(out))


# ---------------------------------------------------------------- cover letter

OPENING, CLOSING = ("C01", "C02"), ("C12", "C13", "C14")


def role_and_company(ref: str) -> tuple[str, str]:
    path = ROOT / "data" / "matches.csv"
    if path.exists():
        for r in csv.DictReader(open(path, encoding="utf-8")):
            if r.get("ref") == ref:
                return r.get("title", ""), r.get("company", "")
    return "", ""


def cover_html(data: dict, career, contact: dict, role_title: str = "", company: str = "", today: date | None = None) -> str:
    today = today or date.today()
    when = f"{today.day} {today:%B %Y}"
    paras = [(c["source_id"], c["text"]) for c in data["cover_letter"]]
    labels = {c["source_id"]: c["label"] for c in data["cover_letter"] if c.get("label")}   # per-letter run-in labels
    opening = " ".join(t for i, t in paras if i in OPENING)
    body = [header_html(contact, pretty_headline(data["headline"]))]
    body.append(f'<p class="addr">{esc(when)}</p>' + (f'<p class="addr">{esc(company)}</p>' if company else ""))
    body.append('<p class="salute">Dear Hiring Manager,</p>')
    if role_title:
        role_title = re.sub(r"(\w)- ", r"\1 – ", role_title)   # posting titles often read "Engineer- VP"
        body.append(f'<p class="re"><b>Re: {esc(role_title)}</b></p>')
    body.append(f"<p>{esc(opening)}</p>")
    blocks = [(i, t) for i, t in paras if i not in OPENING + CLOSING]
    if blocks:
        body.append("<p class=\"lead\">What I would bring to the team:</p><ul class=\"blocks\">")
        cur = ""
        for i, t in blocks:
            title = career.items[i].section if career.has(i) else ""
            if "(optional)" in title:                      # a sub-point of the block before it
                cur += f"<li>{esc(t)}</li>"
                continue
            if cur:
                body.append(cur + "</ul></li>")
            cur = f'<li><b>{esc(labels.get(i) or title)}.</b> {esc(t)}<ul>'
        body.append(cur + "</ul></li></ul>")
    for i, t in paras:
        if i in CLOSING:
            body.append(f"<p>{esc(t)}</p>")
    body.append(f'<p>Kind regards,</p><p><b>{esc(contact.get("name", ""))}</b></p>')
    css = ("@page { size: Letter; margin: 40pt 54pt 34pt 54pt; } body { font-size: 10.5pt; line-height: 1.5; } "
           "p { margin: 0 0 8.5pt; } .addr { margin: 0 0 1.5pt; } hr.rule + .addr { margin-top: 13.5pt; } "
           ".salute { margin-top: 9.5pt; } .lead { margin-bottom: 4.5pt; } "
           "ul.blocks { padding-left: 14pt; margin: 0 0 8.5pt; } ul.blocks > li { margin-top: 5pt; } "
           "ul.blocks ul { list-style: circle; padding-left: 16pt; margin-top: 4pt; } ul ul:empty { display: none; }")
    return page(css, "".join(body))


def render_pdfs(app: Path, data: dict, career, ref: str) -> list[str]:
    contact = career.contact
    if data.get("location"):
        contact = {**contact, "location": data["location"]}
    role_title, company = role_and_company(ref)
    print_pdf(resume_html(data, career, contact), app / "resume.pdf")
    print_pdf(cover_html(data, career, contact, role_title, company), app / "cover_letter.pdf")
    return ["resume.pdf", "cover_letter.pdf"]
