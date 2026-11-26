"""The general resume (profile/general-resume/): what master_drift.py reports after the master CV moves."""
import json
import sys
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))
import master_drift as md  # noqa: E402


def career(**lines):
    return SimpleNamespace(items={k: SimpleNamespace(text=v) for k, v in lines.items()})


def test_reports_new_changed_and_removed_lines_since_the_last_review(tmp_path):
    assert "no general resume" in md.general_report(career(B01="a"), tmp_path)[0]
    (tmp_path / "tailored.json").write_text(json.dumps({"sections": [{"bullets": [{"source_id": "B01"}, {"source_id": "B02"}]}]}))
    assert "never reviewed" in md.general_report(career(B01="a"), tmp_path)[0]
    md.general_done(career(B01="a", B02="b", B03="c", S01="story"), tmp_path)
    assert "no master CV change" in md.general_report(career(B01="a ", B02="b", B03="c", S01="rewritten"), tmp_path)[0]
    out = "\n".join(md.general_report(career(B01="a2", B03="c", B04="d"), tmp_path))
    assert "NEW master lines: B04" in out
    assert "B01 (on it)" in out
    assert "B02 (STILL ON IT)" in out
