"""The masters must pass the master-update check before any application draft is built or refreshed."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import jd_check  # noqa: E402
import master_drift  # noqa: E402
from jobradar import career  # noqa: E402
from test_tailor import GOOD  # noqa: E402


def masters(tmp_path, resume="- [P01] one\n"):
    (tmp_path / "master_resume.md").write_text(resume, encoding="utf-8")
    (tmp_path / "cover_blocks.md").write_text("## [C01] a\nhello\n", encoding="utf-8")
    (tmp_path / "stories.md").write_text("## [S01] a\nstory\n", encoding="utf-8")
    return tmp_path


def test_not_cleared_until_the_check_is_recorded(tmp_path):
    d = masters(tmp_path)
    ok, why = career.masters_cleared(d)
    assert not ok and "not been cleared" in why
    career.clear_masters(d)
    assert career.masters_cleared(d) == (True, "")


def test_any_master_edit_invalidates_the_clearance(tmp_path):
    d = masters(tmp_path)
    career.clear_masters(d)
    (d / "stories.md").write_text("## [S01] a\nstory, edited\n", encoding="utf-8")
    ok, why = career.masters_cleared(d)
    assert not ok and "changed after" in why


def test_line_endings_do_not_matter(tmp_path):
    d = masters(tmp_path, "- [P01] one\n")
    career.clear_masters(d)
    (d / "master_resume.md").write_bytes(b"- [P01] one\r\n")
    assert career.masters_cleared(d)[0]


def test_tailor_refuses_while_masters_are_not_cleared(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(jd_check, "masters_cleared", lambda *a, **k: (False, "the master documents changed"))
    app = jd_check.APPS / "x-app"
    app.mkdir(parents=True)
    (app / "tailored.json").write_text(json.dumps(GOOD), encoding="utf-8")
    (app / "validated.sha256").write_text("old", encoding="utf-8")
    assert jd_check.cmd_tailor(app.name) == 1
    assert "MASTERS NOT CLEARED" in capsys.readouterr().out
    assert not (app / "validated.sha256").exists()   # so render_resume refuses too


def test_master_drift_status_and_clear(tmp_path, monkeypatch, capsys):
    d = masters(tmp_path)
    monkeypatch.setattr(career, "career_dir", lambda: d)
    monkeypatch.setattr(master_drift, "masters_cleared", lambda *a, **k: career.masters_cleared(d))
    monkeypatch.setattr(master_drift, "clear_masters", lambda *a, **k: career.clear_masters(d))
    monkeypatch.setattr(sys, "argv", ["master_drift.py", "status"])
    assert master_drift.main() == 1
    monkeypatch.setattr(sys, "argv", ["master_drift.py", "clear"])
    assert master_drift.main() == 0
    monkeypatch.setattr(sys, "argv", ["master_drift.py", "status"])
    assert master_drift.main() == 0
    assert "cleared" in capsys.readouterr().out
