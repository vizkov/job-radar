"""One-off reminders in the cadence block: due on a date, shown until done, then gone for good."""
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import cadence  # noqa: E402


def test_reminder_lifecycle(tmp_path):
    cadence.reminder_add("alert-yield", "2026-10-17", "compare alert yield", tmp_path)
    before = cadence.reminder_lines(datetime(2026, 10, 12), tmp_path)
    assert before[1] == [] and "due 2026-10-17 · ok" in before[0][0]
    lines, due = cadence.reminder_lines(datetime(2026, 10, 17, 9), tmp_path)
    assert due == ["reminder:alert-yield"] and "DUE since 2026-10-17" in lines[0]
    assert "reminder done alert-yield" in lines[0]
    cadence.reminder_done("alert-yield", tmp_path)
    assert cadence.reminder_lines(datetime(2026, 11, 1), tmp_path) == ([], [])
    assert not (tmp_path / "work" / ".reminders.json").exists()


def test_reminder_add_replaces_same_id_and_rejects_bad_input(tmp_path):
    cadence.reminder_add("x", "2026-10-17", "one", tmp_path)
    cadence.reminder_add("x", "2026-10-20", "two", tmp_path)
    assert [(r["due"], r["text"]) for r in cadence.reminders(tmp_path)] == [("2026-10-20", "two")]
    for bad in (lambda: cadence.reminder_add("y", "not-a-date", "t", tmp_path),
                lambda: cadence.reminder_done("missing", tmp_path)):
        try:
            bad()
        except ValueError:
            continue
        raise AssertionError("expected ValueError")


def test_scoring_is_the_last_cadence_line(tmp_path):
    """The user, 2026-10-22: sweeps ran after scoring and left new roles unscored, so Scoring is listed after every other job."""
    cadence.reminder_add("r", "2026-10-01", "a reminder", tmp_path)
    for picks in (2, 0):
        lines, due = cadence.block(datetime(2026, 10, 22), tmp_path, radar_last="2026-10-22", new_total=0, new_on_board=0,
                                   new_skip=0, new_waiting=0, queued=0, unscored_cards=picks, auto_picks=picks, awaiting=0,
                                   posts_enabled=True)
        assert lines[-1].startswith("  - Scoring") and "--score-pick" in lines[-1]
        assert ("auto_score" in due) == bool(picks)


def test_stamps_sync_through_the_ledger_and_newest_wins(tmp_path):
    """A stamp made on another device arrives as a ledger line; the newest per job wins; jd_cleanup stays local."""
    from datetime import datetime
    (tmp_path / "state").mkdir()
    (tmp_path / "state" / "cadence.jsonl").write_text(
        '{"at": "2026-11-17T10:05:00", "job": "health"}\n'
        '{"at": "2026-11-17T09:05:00", "job": "health"}\n'      # older line merged in after the newer one
        'garbled {{\n', encoding="utf-8")
    assert cadence.last("health", tmp_path) == datetime(2026, 11, 17, 10, 5)
    cadence.done("inbox_check", tmp_path, datetime(2026, 11, 17, 11, 0))
    cadence.done("jd_cleanup", tmp_path, datetime(2026, 11, 17, 11, 0))
    ledger = (tmp_path / "state" / "cadence.jsonl").read_text(encoding="utf-8")
    assert "inbox_check" in ledger and "jd_cleanup" not in ledger
    assert cadence.last("jd_cleanup", tmp_path) == datetime(2026, 11, 17, 11, 0)
