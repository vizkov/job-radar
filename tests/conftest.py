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
    for attr in ("QUEUE", "STATUS_MD", "ISSUE_MAP", "STALE", "FLAGGED", "PIPELINE_LOG", "BOARD_FILE"):
        monkeypatch.setattr(board_sync, attr, tmp_path / f"_iso_{attr.lower()}")
    import jd_check, jd_prep
    monkeypatch.setattr(jd_check, "SCORES", tmp_path / "_iso_scores.jsonl")
    monkeypatch.setattr(jd_prep, "SCORES", tmp_path / "_iso_scores.jsonl")
    import session_brief
    for attr in ("WORK", "LAST", "LAST_REVIEW", "FILL_LOCK", "SNAPSHOT", "PIPELINE_LOG"):
        monkeypatch.setattr(session_brief, attr, tmp_path / f"_iso_sb_{attr.lower()}")
