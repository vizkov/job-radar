"""PDF layout: the HTML is built from the tailored text plus the master CV's structure. The one real-browser
test is skipped where no Chrome/Edge is installed."""
import sys
from datetime import date
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import render_pdf as rp  # noqa: E402
from jobradar.career import Career, Item  # noqa: E402

CONTACT = {"name": "Alex Example", "email": "alex@example.com", "phone": "+44 1234 567890",
           "location": "Leeds, UK · Open to relocation to NL",
           "links": "https://www.linkedin.com/in/alex, https://github.com/alex"}


def career() -> Career:
    c = Career(contact=CONTACT)
    add = lambda i, t, s, ctx="": c.items.__setitem__(i, Item(i, t, s, ctx))  # noqa: E731
    add("P01", "Application security engineer with 6+ years.", "Summary")
    add("P02", "Hands-on in pentesting.", "Summary")
    add("P05", "Impact: found a chain of flaws before go-live.", "Key achievements")
    add("B01", "Security for banks and airlines.", "Experience", "ExampleSec (formerly Acme) — Leeds — Jan 2021 to Present")
    add("B02", "Led threat modelling for a client.", "Experience", "Staff Consultant — ExampleSec — Jan 2024 to Present")
    add("B03", "Ran pentests for a bank.", "Experience", "Associate — Acme — Jan 2021 to Dec 2023")
    add("B04", "Wrote web and API tests.", "Experience", "Analyst — OldCo (now NewCo) — Paris — Jan 2018 to Dec 2020")
    add("B05", "https://github.com/alex/oss: a code review method.", "Experience", "Projects and writing")
    add("K01", "Application security: pentesting, code review", "Skills")
    add("K02", "Languages: Python, Java", "Skills")
    add("E01", "Example University: B.Sc. Computer Science (2010 – 2014)", "Education")
    add("C03", "A chain of flaws was found.", "Seeing across systems")
    add("C15", "One example of it.", "Seeing across systems: the example (optional)")
    add("C09", "The bank accepted the findings.", "Explaining risk")
    return c


DATA = {"key": "0" * 16, "headline": "Senior Application Security Engineer: penetration testing, threat modelling, AI/LLM security",
        "sections": [{"heading": "x", "bullets": [{"source_id": i, "text": t} for i, t in [
            ("P01", "Application security engineer with 6+ years."), ("P02", "Hands-on in pentesting."),
            ("P05", "Impact: found a chain of flaws before go-live."),
            ("B01", "Security for banks and airlines."), ("B02", "Led threat modelling for a client."),
            ("B03", "Ran pentests for a bank."), ("B04", "Wrote web and API tests."),
            ("B05", "https://github.com/alex/oss: a code review method."),
            ("E01", "Example University: B.Sc. Computer Science (2010 – 2014)")]]}],
        "skills": [], "cover_letter": [{"source_id": i, "text": t} for i, t in [
            ("C01", "I am applying for the role."), ("C02", "It matches my work."), ("C03", "A chain of flaws was found."),
            ("C15", "One example of it."), ("C09", "The bank accepted the findings."), ("C13", "I would need visa sponsorship."),
            ("C14", "Thank you for your time.")]]}


def test_headline_uses_the_designs_middots():
    assert rp.pretty_headline(DATA["headline"]) == \
        "Senior Application Security Engineer · Penetration Testing · Threat Modelling · AI/LLM Security"


def test_resume_layout_follows_the_design():
    h = rp.resume_html(DATA, career(), CONTACT)
    order = [h.index(s) for s in ("<h2>Profile", "<h2>Key achievements", "<h2>Experience", "<h2>Skills",
                                  "Projects &amp; writing", "<h2>Education")]
    assert order == sorted(order)                                     # the design's section order
    assert "Application security engineer with 6+ years. Hands-on in pentesting." in h   # profile = one paragraph
    assert "<b>Impact:</b> found a chain" in h                        # bold label on a key achievement
    assert '<span class="co">ExampleSec <small>(formerly Acme)</small></span>' in h
    assert "Leeds · Jan 2021 – Present" in h                          # city and dates, right-aligned meta
    assert "Staff Consultant</b><span class=\"sub\"> · ExampleSec</span>" in h and "Associate</b>" in h
    assert 'class="desc">Security for banks and airlines.' in h        # the company's one-line description
    assert "OldCo <small>(now NewCo)</small>" in h and "Paris · Jan 2018 – Dec 2020" in h   # a 4-part role is its own company
    assert '<a href="https://github.com/alex/oss">github.com/alex/oss</a>: a code review method.' in h
    assert "<p><b>Application security:</b> pentesting, code review</p>" in h
    assert 'Example University</b>: B.Sc. Computer Science' in h and ">2010 – 2014<" in h
    assert 'mailto:alex@example.com' in h and "linkedin.com/in/alex" in h and "size: A4" in h


def test_cover_letter_layout_follows_the_design():
    h = rp.cover_html(DATA, career(), CONTACT, "Security Engineer", "ExampleCo", date(2026, 9, 30))
    assert "30 September 2026" in h and "ExampleCo" in h and "Dear Hiring Manager," in h
    assert "<b>Re: Security Engineer</b>" in h and "size: Letter" in h
    assert "I am applying for the role. It matches my work." in h     # C01 + C02 are one paragraph
    assert h.index("What I would bring to the team:") < h.index("<b>Seeing across systems.</b>") < h.index("Explaining risk.")
    assert "<li>One example of it.</li>" in h                          # an optional block is a sub-point of the one before
    assert h.index("Explaining risk") < h.index("I would need visa sponsorship.") < h.index("Kind regards,")


def test_skills_grid_uses_the_tailored_skill_lines_else_all_master_lines():
    c = career()
    assert "<p><b>Languages:</b> Python, Java</p>" in rp.resume_html(DATA, c, CONTACT)        # none chosen: every master line
    tailored = {**DATA, "sections": DATA["sections"] + [{"heading": "Skills", "bullets": [
        {"source_id": "K02", "text": "Languages: Java, Python"}]}]}
    h = rp.resume_html(tailored, c, CONTACT)
    assert "<p><b>Languages:</b> Java, Python</p>" in h and "Application security:</b>" not in h   # chosen lines only, as worded


def test_markdown_links_in_a_bullet_become_teal_links():
    h = rp.rich("[Thick Client Security Assessment](https://medium.com/@a), a blog series & more")
    assert h == '<a href="https://medium.com/@a">Thick Client Security Assessment</a>, a blog series &amp; more'


def test_text_is_escaped():
    d = {**DATA, "sections": [{"heading": "x", "bullets": [{"source_id": "P01", "text": "a <script>x</script> & b"}]}]}
    h = rp.resume_html(d, career(), CONTACT)
    assert "<script>" not in h and "a &lt;script&gt;x&lt;/script&gt; &amp; b" in h


@pytest.mark.skipif(rp.find_browser() is None, reason="no Chrome or Edge installed")
def test_prints_a_real_pdf(tmp_path):
    out = tmp_path / "resume.pdf"
    rp.print_pdf(rp.resume_html(DATA, career(), CONTACT), out)
    assert out.read_bytes()[:5] == b"%PDF-" and out.stat().st_size > 1000
