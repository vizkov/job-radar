"""Sponsorship verdicts: what the checker accepts, and the card block."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import sponsorship as sp  # noqa: E402

REF = "a" * 16
JD = "We offer relocation support. Unfortunately we are unable to sponsor work visas for this role."


def rec(**over):
    d = {"key": REF, "country": "GB", "verdict": "likely", "summary": "Licensed and hires internationally.",
         "evidence": [{"kind": "register", "text": "UK register: Acme UK Ltd"},
                      {"kind": "company_page", "text": "Careers FAQ says it sponsors engineers",
                       "url": "https://acme.example/careers/faq", "date": "2026-09-28"}]}
    return {**d, **over}


def test_valid_record_passes():
    assert sp.check(rec(), REF, JD) == []


def test_rejections():
    assert any("verbatim" in e for e in sp.check(rec(verdict="no", evidence=[
        {"kind": "ad", "text": "says no", "quote": "we never sponsor anyone"}]), REF, JD))
    assert any("LinkedIn" in e for e in sp.check(rec(evidence=[
        {"kind": "company_page", "text": "x", "url": "https://www.linkedin.com/company/acme"}]), REF, JD))
    assert any("'confirmed' needs" in e for e in sp.check(rec(verdict="confirmed", evidence=[
        {"kind": "register", "text": "on the register"}]), REF, JD))
    assert any("'no' needs" in e for e in sp.check(rec(verdict="no", evidence=[
        {"kind": "register", "text": "not on the register"}]), REF, JD))
    assert sp.check(rec(verdict="no", evidence=[{"kind": "company_page", "text": "policy: no sponsorship",
                                                  "url": "https://acme.example/visas"}]), REF, JD) == []
    assert any("verdict must be" in e for e in sp.check(rec(verdict="yes"), REF, JD))


def test_no_verdict_with_verbatim_quote_passes_and_renders_escaped():
    d = rec(verdict="no", summary="The ad rules it out [x](http://evil).", evidence=[
        {"kind": "ad", "text": "The ad says", "quote": "unable to sponsor work visas"}])
    assert sp.check(d, REF, JD) == []
    block = sp.visa_section(d)
    assert "**Visa sponsorship: No** (GB)" in block and r"\[x\]" in block and '"unable to sponsor work visas"' in block


def test_with_visa_replaces_in_place():
    body = "**Acme**\n\nRole ID: `x`\n"
    once = sp.with_visa(body, sp.visa_section(rec()))
    twice = sp.with_visa(once, sp.visa_section(rec(verdict="unclear")))
    assert twice.count(sp.VISA_START) == 1 and "Unclear" in twice and "Likely" not in twice
