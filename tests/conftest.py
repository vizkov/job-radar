import os
import sys
from pathlib import Path

# Always test against the public sample settings, so results don't depend on
# whatever is in your private profile/. Must be set before jobradar is imported.
os.environ["JOBRADAR_PROFILE"] = "examples"

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest


@pytest.fixture(autouse=True)
def _no_politeness_delays(monkeypatch):
    from jobradar.sources import _http
    monkeypatch.setattr(_http, "PAUSE", 0)
    monkeypatch.setattr(_http, "BACKOFF", 0)


@pytest.fixture(autouse=True)
def _isolate_tool_state(tmp_path, monkeypatch):
    """No test may write into the real repo's state/, data/ or digests/ files."""
    import importlib.util
    import sys as _sys
    tools = Path(__file__).resolve().parent.parent / "tools"
    if str(tools) not in _sys.path:
        _sys.path.insert(0, str(tools))
    import board_sync
    for attr in ("QUEUE", "STATUS_MD", "ISSUE_MAP", "STALE", "FLAGGED", "PIPELINE_LOG", "BOARD_FILE", "MATCHES"):
        monkeypatch.setattr(board_sync, attr, tmp_path / f"_iso_{attr.lower()}")
    import jd_check, jd_prep
    monkeypatch.setattr(jd_check, "SCORES", tmp_path / "_iso_scores.jsonl")
    monkeypatch.setattr(jd_prep, "SCORES", tmp_path / "_iso_scores.jsonl")
    # the JD packets, applications and matches too: a test that forgets its own fixture still can't touch them
    monkeypatch.setattr(jd_prep, "WORK", tmp_path / "_iso_jd")
    monkeypatch.setattr(jd_prep, "MATCHES", tmp_path / "_iso_matches.csv")
    monkeypatch.setattr(jd_check, "WORK", tmp_path / "_iso_jd")
    monkeypatch.setattr(jd_check, "APPS", tmp_path / "_iso_apps")
    monkeypatch.setattr(jd_check, "masters_cleared", lambda *a, **k: (True, ""))  # tests that want the real guard override this
    monkeypatch.setattr(board_sync, "WORK_JD", tmp_path / "_iso_jd")
    import render_resume
    monkeypatch.setattr(render_resume, "APPS", tmp_path / "_iso_apps")
    monkeypatch.setattr(render_resume, "SCRATCH", tmp_path / "_iso_scratch")
    import calibrate, referrals, sponsorship
    for attr in ("SCORES", "MATCHES", "LOG"):
        monkeypatch.setattr(calibrate, attr, tmp_path / f"_iso_cal_{attr.lower()}")
    _cfg = tmp_path / "_iso_config.json"
    _cfg.write_text((Path(__file__).resolve().parent.parent / "examples" / "config.json").read_text(encoding="utf-8"), encoding="utf-8")
    monkeypatch.setattr(calibrate, "config_path", lambda: _cfg)
    monkeypatch.setattr(sponsorship, "LOG", tmp_path / "_iso_sponsorship.jsonl")
    monkeypatch.setattr(sponsorship, "WORK", tmp_path / "_iso_jd")
    monkeypatch.setattr(referrals, "NETWORK", tmp_path / "_iso_network.csv")
    monkeypatch.setattr(referrals, "LOG", tmp_path / "_iso_referrals.jsonl")
    import post_leads
    for attr, name in (('QUERIES', 'queries.json'), ('PEOPLE', 'people.jsonl'), ('LEADS', 'leads.jsonl'), ('MATCHES', 'matches.csv'), ('SCORES', 'scores.jsonl'), ('TARGETS', 'targets.tsv')):
        monkeypatch.setattr(post_leads, attr, tmp_path / f'_iso_post_{name}')
    import session_brief
    for attr in ("WORK", "LAST", "LAST_REVIEW", "LAST_DOCS_REVIEW", "LAST_CALIBRATION", "FILL_LOCK", "LAST_ARCHIVE", "SNAPSHOT", "PIPELINE_LOG"):
        monkeypatch.setattr(session_brief, attr, tmp_path / f"_iso_sb_{attr.lower()}")
