"""The draft experiment writes the A text and one brief per agent; the briefs never say which draft is the tailored one."""
import draft_experiment as de


def test_briefs_name_every_agent_job_and_keep_the_drafts_blind(tmp_path):
    b = de.briefs(tmp_path / "jd.txt", tmp_path / "experiment")
    assert set(b) == {"writer_ad_only", "writer_with_record", "ats", "recruiter", "consistency", "copy_editor"}
    assert "resume_B.md" in b["writer_ad_only"] and "resume_C.md" in b["writer_with_record"]
    assert "master_resume.md" in b["writer_with_record"] and "master_resume.md" not in b["writer_ad_only"]   # B gets no record
    for name, text in b.items():
        assert "tailored" not in text.lower().replace("tailored.json", ""), name        # the readers are never told which draft is the tailored one
    assert "ignore B" in b["consistency"] and "writing-rules.md" in b["copy_editor"]
    assert all(str(tmp_path / "experiment" / f"report_{n}.md") in b[n] for n in ("ats", "recruiter", "consistency", "copy_editor"))


def test_prep_refuses_an_unvalidated_application(tmp_path, monkeypatch, capsys):
    app = tmp_path / "app"
    app.mkdir()
    (app / "tailored.json").write_text("{}", encoding="utf-8")
    assert de.prep(str(app)) == 1 and "validate first" in capsys.readouterr().out
