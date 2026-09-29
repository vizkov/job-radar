import copy
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import jd_check  # noqa: E402
import render_resume  # noqa: E402
from jobradar.career import load_career
from jobradar.paths import EXAMPLES

CAREER = load_career(EXAMPLES / "career")
GOOD = {
    "key": "ab" * 8,
    "headline": "Application Security Engineer — secure code review and threat modeling",
    "sections": [
        {"heading": "Summary", "bullets": [{"source_id": "P01", "text": CAREER.items["P01"].text}]},
        {"heading": "Experience — ExampleSec Consulting (2021 to present)", "bullets": [
            {"source_id": "B03", "text": "Performed manual secure code review of Java/Spring and Node.js services, "
                                         "finding authorisation bypass and IDOR issues missed by SAST."},
            {"source_id": "B02", "text": CAREER.items["B02"].text}]},
        {"heading": "Certifications", "bullets": [{"source_id": "E01", "text": CAREER.items["E01"].text}]}],
    "skills": ["Burp Suite", "Semgrep", "STRIDE"],
    "cover_letter": [{"source_id": "C01", "text": CAREER.items["C01"].text},
                     {"source_id": "S01", "text": "Before a payments launch I found an authorisation bypass in "
                                                  "code review that SAST missed; the pattern became a Semgrep rule."}],
}


def check(d):
    return jd_check.check_tailor(d, CAREER)


def test_good_tailoring_passes():
    assert check(GOOD) == ([], [])


@pytest.mark.parametrize("mutate,expect", [
    (lambda d: d["sections"][1]["bullets"].append({"source_id": "B42", "text": "Led red team ops"}), "[B42]"),
    (lambda d: d["sections"][1]["bullets"][0].update(text="Led 400+ code reviews finding auth bypass issues."), "numbers not in your original"),
    (lambda d: d["sections"][1]["bullets"][0].update(text="Reviewed code; portfolio at https://evil.example/cv"), "links you didn't write"),
    (lambda d: d["cover_letter"][0].update(text="Contact me at recruiter@evil.example about this."), "links you didn't write"),
    (lambda d: d.update(headline="Call +44 20 7946 0000 now"), "headline contains"),
    (lambda d: d["skills"].append("Kubernetes"), "doesn't appear in your career docs"),
    (lambda d: d["sections"][0]["bullets"].append({"source_id": "C01", "text": "x"}), "only B/E/P items"),
    (lambda d: d["cover_letter"].append({"source_id": "B01", "text": "x"}), "only C/S items"),
    (lambda d: d["sections"][2]["bullets"].append({"source_id": "P01", "text": "again"}), "lines used twice"),
    (lambda d: d.update(key="not-a-ref"), "role ID"),
    (lambda d: d["sections"][1]["bullets"][1].update(text="Ran threat-modeling workshops (STRIDE) for 12 product teams at Google."), "names things not in your career docs"),
    (lambda d: d.update(headline="SonarQube expert and AppSec engineer"), "headline names things"),
])
def test_rejections(mutate, expect):
    d = copy.deepcopy(GOOD)
    mutate(d)
    errs, _ = check(d)
    assert any(expect in e for e in errs), errs


def test_heavy_rewording_warns_but_passes():
    d = copy.deepcopy(GOOD)
    d["sections"][1]["bullets"][1]["text"] = "Security workshops."
    errs, warns = check(d)
    assert errs == [] and any("heavily reworded" in w for w in warns)


def test_own_links_are_allowed():
    d = copy.deepcopy(GOOD)
    d["headline"] = "AppSec engineer — https://github.com/alex-example"
    assert check(d)[0] == []


@pytest.fixture
def app(tmp_path, monkeypatch):
    monkeypatch.setattr(jd_check, "APPS", tmp_path)
    monkeypatch.setattr(render_resume, "APPS", tmp_path)
    folder = tmp_path / "2026-09-28-bridewell"
    folder.mkdir()
    (folder / "tailored.json").write_text(json.dumps(GOOD), encoding="utf-8")
    return folder


def test_render_requires_validation_of_this_exact_file(app, capsys):
    assert render_resume.main([app.name]) == 1                         # never validated
    assert jd_check.cmd_tailor(app.name) == 0
    assert "was: " in capsys.readouterr().out                          # shows the diff
    data = json.loads((app / "tailored.json").read_text())
    data["headline"] = "edited after validation"
    (app / "tailored.json").write_text(json.dumps(data))
    assert render_resume.main([app.name]) == 1                         # changed since validation
    (app / "tailored.json").write_text(json.dumps(GOOD), encoding="utf-8")
    assert jd_check.cmd_tailor(app.name) == 0


def test_invalid_file_removes_old_stamp(app):
    assert jd_check.cmd_tailor(app.name) == 0
    bad = copy.deepcopy(GOOD)
    bad["skills"].append("Kubernetes")
    (app / "tailored.json").write_text(json.dumps(bad))
    assert jd_check.cmd_tailor(app.name) == 1 and not (app / "validated.sha256").exists()


def test_render_writes_only_resume_and_cover_by_default(app):
    assert jd_check.cmd_tailor(app.name) == 0
    assert render_resume.main([app.name]) == 0
    assert sorted(p.name for p in app.iterdir()) == ["cover_letter.md", "resume.md", "tailored.json", "validated.sha256"]


def test_render_outputs(app):
    docx = pytest.importorskip("docx")
    assert jd_check.cmd_tailor(app.name) == 0
    assert render_resume.main([app.name, "--docx"]) == 0                 # the Word file is opt-in
    md = (app / "resume.md").read_text(encoding="utf-8")
    assert md.startswith("# Alex Example") and "alex.example@example.com" in md and "IDOR" in md
    doc = docx.Document(str(app / "resume.docx"))
    text = "\n".join(p.text for p in doc.paragraphs)
    assert "Alex Example" in text and "authorisation bypass" in text and "Semgrep" in text
    assert len(doc.tables) == 0 and len(doc.sections) == 1               # single column, no tables
    assert doc.sections[0]._sectPr.xpath("./w:cols[@w:num>1]") == []
    cover = (app / "cover_letter.md").read_text(encoding="utf-8")
    assert cover.startswith("Dear Hiring Manager,") and cover.rstrip().endswith("Alex Example")


def test_names_and_skills_must_match_whole_words():
    d = copy.deepcopy(GOOD)
    d["skills"] = ["Ja"]  # "ja" appears inside "Java" in the example CV, but not as a word
    assert any("skills[0]" in e for e in check(d)[0])
    assert jd_check._in_text("Go", "wrote go services") and not jd_check._in_text("Go", "a good engineer")


def test_cover_letter_paragraph_used_twice_is_rejected():
    d = copy.deepcopy(GOOD)
    d["cover_letter"].append(copy.deepcopy(d["cover_letter"][0]))
    assert any("used twice" in e for e in check(d)[0])
