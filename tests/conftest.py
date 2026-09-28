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
