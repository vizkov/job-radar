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


def test_submitted_applications_are_listed_not_checked(tmp_path, monkeypatch, capsys):
    """An application that was applied to is a record of what was sent: no STALE / DIFFERS unless --all."""
    import os
    cd = tmp_path / "career"
    cd.mkdir()
    masters(cd)
    apps, log = tmp_path / "apps", tmp_path / "pipeline_log.jsonl"
    for key, stage in (("a" * 16, "Applied"), ("b" * 16, "Shortlisted"), ("c" * 16, "Rejected")):
        folder = apps / f"role-{stage.lower()}"
        folder.mkdir(parents=True)
        (folder / "tailored.json").write_text(json.dumps({"key": key, "headline": "h", "skills": [], "cover_letter": [],
                                                           "sections": [{"bullets": [{"source_id": "P01", "text": "an old wording"}]}]}), encoding="utf-8")
        (folder / "resume.pdf").write_bytes(b"%PDF")
        os.utime(folder / "resume.pdf", (1, 1))                       # rendered long before the masters changed
    log.write_text("\n".join(json.dumps(r) for r in [
        {"ref": "a" * 16, "field": "Stage", "value": "Shortlisted"}, {"ref": "a" * 16, "field": "Stage", "value": "Applied"},
        {"ref": "b" * 16, "field": "Stage", "value": "Shortlisted"}, {"ref": "c" * 16, "field": "Stage", "value": "Rejected"},
        {"ref": "c" * 16, "field": "Notes", "value": "ignored: not a stage"}]) + "\n", encoding="utf-8")
    assert master_drift.stages(log)["a" * 16] == "Applied"           # the last Stage entry wins
    monkeypatch.setattr(master_drift, "APPS", apps)
    monkeypatch.setattr(master_drift, "LOG", log)
    monkeypatch.setattr(master_drift, "career_dir", lambda: cd)
    monkeypatch.setattr(master_drift, "load_career", lambda: career.load_career(cd))
    monkeypatch.setattr(sys, "argv", ["master_drift.py"])
    master_drift.main()
    out = capsys.readouterr().out
    assert "role-applied: SUBMITTED (Applied)" in out and "role-rejected: SUBMITTED (Rejected)" in out
    assert "role-shortlisted: STALE" in out                          # not sent: still flagged
    assert "role-applied: STALE" not in out and "2 submitted application(s) listed" in out
    monkeypatch.setattr(sys, "argv", ["master_drift.py", "--all"])
    master_drift.main()
    assert "role-applied: STALE" in capsys.readouterr().out          # --all restores the full check
