"""The draft experiment writes the A text and one brief per agent (two sets by default, a third on request); the briefs never say which draft is the tailored one."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import draft_experiment as de  # noqa: E402


def test_default_compares_two_sets_and_the_ad_only_draft_is_optional(tmp_path):
    b = de.briefs(tmp_path / "jd.txt", tmp_path / "experiment")
    assert set(b) == {"writer_with_record", "ats", "recruiter", "consistency", "copy_editor"}          # no ad-only writer by default
    assert "draft_B.json" in b["writer_with_record"] and "master_resume.md" in b["writer_with_record"]
    assert "A and B" in b["ats"] and "resume_A.txt" in b["ats"] and "resume_C.md" not in b["ats"] and "ignore C" not in b["consistency"]
    full = de.briefs(tmp_path / "jd.txt", tmp_path / "experiment", with_ad_only=True)
    assert set(full) == set(b) | {"writer_ad_only"}
    assert "resume_C.md" in full["writer_ad_only"] and "master_resume.md" not in full["writer_ad_only"]   # C gets no record
    assert "A, B and C" in full["ats"] and "ignore C" in full["consistency"]


def test_briefs_never_say_which_draft_is_the_tailored_one_and_name_every_report(tmp_path):
    for with_ad_only in (False, True):
        b = de.briefs(tmp_path / "jd.txt", tmp_path / "experiment", with_ad_only)
        for name, text in b.items():
            assert "tailored" not in text.lower().replace("tailored.json", ""), name
        assert "writing-rules.md" in b["copy_editor"]
        assert all(str(tmp_path / "experiment" / f"report_{n}.md") in b[n] for n in ("ats", "recruiter", "consistency", "copy_editor"))


def test_prep_refuses_an_unvalidated_application(tmp_path, monkeypatch, capsys):
    app = tmp_path / "app"
    app.mkdir()
    (app / "tailored.json").write_text("{}", encoding="utf-8")
    assert de.prep(str(app)) == 1 and "validate first" in capsys.readouterr().out


def test_cv_only_application_has_no_letter_in_the_briefs(tmp_path):
    """The user, 2026-11-02: a CV-only application (empty cover_letter) must not produce letter files, and the readers judge resumes alone."""
    b = de.briefs(tmp_path / "jd.txt", tmp_path / "experiment", letter=False)
    assert "letter_A.txt" not in b["ats"] and "letter_B.txt" not in b["ats"] and "CV-only" in b["ats"]
    assert "letter_A.txt" not in b["consistency"] and "CV only" in b["consistency"]
    assert "letter_A.txt" in de.briefs(tmp_path / "jd.txt", tmp_path / "experiment")["ats"]   # the default is unchanged
