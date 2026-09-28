import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import board_sync as bs  # noqa: E402


class FakeGh:
    dry_run = False

    def __init__(self, open_status=""):
        self.calls, self.open_status, self.bodies = [], open_status, []

    def __call__(self, *args):
        self.calls.append(args)
        if "--body-file" in args:
            self.bodies.append(Path(args[args.index("--body-file") + 1]).read_text(encoding="utf-8"))
        if args[:2] == ("issue", "list"):
            return self.open_status
        if args[:2] == ("issue", "create"):
            return f"https://github.com/me/r/issues/{len(self.calls)}"
        return ""


@pytest.fixture
def paths(tmp_path, monkeypatch):
    monkeypatch.setattr(bs, "QUEUE", tmp_path / "board_queue.json")
    monkeypatch.setattr(bs, "STATUS_MD", tmp_path / "status.md")
    return tmp_path


def queue(paths, n):
    items = [{"ref": f"{i:016x}", "title": f"[T1] X — Role {i} (GB)", "body": f"body {i}; rm -rf / `$(id)`",
              "labels": ["role", "tier-1", "country-GB"]} for i in range(n)]
    bs.QUEUE.write_text(json.dumps(items))
    return items


def test_creates_issues_with_argv_and_caps(paths):
    queue(paths, 5)
    gh, slept = FakeGh(), []
    created, left = bs.sync_roles(gh, max_per_run=3, sleep=slept.append)
    assert (created, left) == (3, 2)
    creates = [c for c in gh.calls if c[:2] == ("issue", "create")]
    assert len(creates) == 3 and creates[0][creates[0].index("--title") + 1] == "[T1] X — Role 0 (GB)"
    assert "--label" in creates[0] and "country-GB" in creates[0]
    assert gh.bodies[0] == "body 0; rm -rf / `$(id)`"          # passed as a file, never through a shell
    assert slept == [bs.SPACING_SECONDS] * 3
    assert [q["ref"] for q in json.loads(bs.QUEUE.read_text())] == [f"{3:016x}", f"{4:016x}"]


def test_labels_created_once_per_run(paths):
    queue(paths, 2)
    gh = FakeGh()
    bs.sync_roles(gh, 10, sleep=lambda s: None)
    label_calls = [c for c in gh.calls if c[:2] == ("label", "create")]
    assert sorted(c[2] for c in label_calls) == ["country-GB", "role", "tier-1"]
    assert all("--force" in c for c in label_calls)


def test_crash_midway_keeps_the_rest_queued(paths):
    queue(paths, 3)

    class Flaky(FakeGh):
        def __call__(self, *args):
            if args[:2] == ("issue", "create") and sum(c[:2] == ("issue", "create") for c in self.calls) == 1:
                raise RuntimeError("secondary rate limit")
            return super().__call__(*args)
    with pytest.raises(RuntimeError):
        bs.sync_roles(Flaky(), 10, sleep=lambda s: None)
    assert len(json.loads(bs.QUEUE.read_text())) == 2   # first one done, no duplicate on retry


def test_empty_queue_is_a_no_op(paths):
    gh = FakeGh()
    assert bs.sync_roles(gh, 10) == (0, 0) and gh.calls == []


def test_status_creates_and_pins_then_edits(paths):
    bs.STATUS_MD.write_text("**Last run:** today")
    gh = FakeGh(open_status="")
    assert bs.sync_status(gh).startswith("created")
    assert any(c[:2] == ("issue", "pin") for c in gh.calls)
    gh2 = FakeGh(open_status="12")
    assert bs.sync_status(gh2) == "updated #12"
    assert ("issue", "edit", "12") == gh2.calls[1][:3] and gh2.bodies == ["**Last run:** today"]


def test_status_reports_actual_queue_length(paths):
    bs.STATUS_MD.write_text("**Waiting to be added to the board:** 49\n")
    queue(paths, 9)
    gh = FakeGh(open_status="41")
    bs.sync_status(gh)
    assert gh.bodies == ["**Waiting to be added to the board:** 9\n"]


@pytest.fixture
def state(tmp_path, monkeypatch):
    for name, attr in (("issue_map.json", "ISSUE_MAP"), ("stale_roles.json", "STALE"),
                       ("stale_flagged.json", "FLAGGED"), ("pipeline_log.jsonl", "PIPELINE_LOG")):
        monkeypatch.setattr(bs, attr, tmp_path / name)
    return tmp_path


def test_created_issues_are_mapped_and_backfill(paths, state):
    queue(paths, 2)
    bs.sync_roles(FakeGh(), 10, sleep=lambda s: None)
    m = json.loads(bs.ISSUE_MAP.read_text())
    assert set(m) == {f"{0:016x}", f"{1:016x}"} and all(isinstance(v, int) for v in m.values())

    class ListGh(FakeGh):
        def __call__(self, *args):
            if args[:2] == ("issue", "list"):
                return json.dumps([{"number": 77, "body": "x <!-- job-radar:ref=" + "e" * 16 + " -->"}])
            return super().__call__(*args)
    assert bs.backfill_map(ListGh()) == "issue map: 3 roles"


def test_stale_labels_added_once_and_removed_when_back(state):
    bs.ISSUE_MAP.write_text(json.dumps({"a" * 16: 5, "b" * 16: 6}))
    bs.STALE.write_text(json.dumps({"stale": ["a" * 16, "c" * 16], "alive": []}))
    gh = FakeGh()
    assert bs.sync_stale(gh) == "possibly-closed: +1 / -0 (now 1)"
    assert ("issue", "edit", "5", "--add-label", "possibly-closed") in gh.calls
    gh2 = FakeGh()
    bs.sync_stale(gh2)                                   # already flagged: no repeat edit
    assert not any(c[:2] == ("issue", "edit") for c in gh2.calls)
    bs.STALE.write_text(json.dumps({"stale": [], "alive": ["a" * 16]}))
    gh3 = FakeGh()
    assert bs.sync_stale(gh3) == "possibly-closed: +0 / -1 (now 0)"
    assert ("issue", "edit", "5", "--remove-label", "possibly-closed") in gh3.calls


def test_stage_changes_are_logged(state):
    bs.log_stage("a" * 16, "Stage", "Applied", "claude")
    rec = json.loads(bs.PIPELINE_LOG.read_text().splitlines()[0])
    assert (rec["ref"], rec["value"], rec["by"]) == ("a" * 16, "Applied", "claude") and rec["at"]
