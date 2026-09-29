import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import consistency_check as cc  # noqa: E402

CV = """---
name: A B
---
# Experience
- [B01] Led eight assessors delivering 100+ assessments a year using Burp Suite. Cut triage time by 50%. Jun 2021 to 2024.
"""
COVER = "I led eight assessors across 100+ assessments. It cut triage time by 50%. I also interviewed 10+ candidates."
STORIES = "## [S01] Story\nI led 8 assessors and used Burp Suite. Cut triage by 50%.\n"


def run(cv, cover, stories):
    return cc.compare({"cv": cc.facts(cv), "cover": cc.facts(cover), "stories": cc.facts(stories)})


def test_spelled_out_numbers_match_digits():
    assert cc.figures("led eight assessors") == {"8": "eight assessors"}


def test_consistent_documents_have_no_unsupported_items():
    assert run(CV, COVER.replace(" I also interviewed 10+ candidates.", ""), STORIES)["unsupported"] == []


def test_figure_only_in_the_cover_letter_is_flagged():
    items = [r["item"] for r in run(CV, COVER, STORIES)["unsupported"]]
    assert "10+ candidates" in items


def test_year_and_name_not_in_other_documents_are_flagged():
    f = run(CV, "I used LiteLLM in 2019.", STORIES)["unsupported"]
    assert {(r["kind"], r["item"]) for r in f} >= {("name", "LiteLLM"), ("year", "2019")}


def test_cv_figure_with_no_story_or_cover_backing():
    f = run(CV + "\n- Won 3 awards.", COVER, STORIES)["cv-only"]
    assert [r["item"] for r in f] == ["3 awards"]


def test_placeholders_are_reported():
    f = run(CV, "Dear [Hiring Manager], I am applying for [role] at {company}.", STORIES)["placeholders"]
    assert len(f) >= 2


def test_story_picker_table_numbers_are_ignored():
    stories = "WHICH STORY FOR WHICH QUESTION\nBiggest impact 1 - backup 7\nMistake or failure 6\n1 - The payment finding\n"
    assert cc.facts(stories)["figures"] == {}


def test_main_exit_code(tmp_path, monkeypatch, capsys):
    for name, text in {"cv.md": CV, "cover.md": COVER, "stories.md": STORIES}.items():
        (tmp_path / name).write_text(text, encoding="utf-8")
    argv = ["x", "--cv", str(tmp_path / "cv.md"), "--cover", str(tmp_path / "cover.md"),
            "--stories", str(tmp_path / "stories.md")]
    monkeypatch.setattr(sys, "argv", argv)
    assert cc.main() == 1
    assert "10+ candidates" in capsys.readouterr().out
    (tmp_path / "cover.md").write_text(COVER.replace(" I also interviewed 10+ candidates.", ""), encoding="utf-8")
    assert cc.main() == 0


def test_missing_file_exits(monkeypatch, tmp_path):
    monkeypatch.setattr(sys, "argv", ["x", "--cv", str(tmp_path / "no.md"), "--cover", str(tmp_path / "no.md"),
                                      "--stories", str(tmp_path / "no.md")])
    with pytest.raises(SystemExit):
        cc.main()
