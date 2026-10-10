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
