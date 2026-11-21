"""The sweep yield ledger (the user, 2026-11-21: measure roles found per Chrome read)."""
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import sweep_yield as sy  # noqa: E402


def test_record_and_report(tmp_path):
    led = tmp_path / "y.jsonl"
    assert "no sweep reads" in sy.report(ledger=led)[0]
    sy.record("post", "netflix", hits=0, found=0, added=0, ledger=led)
    sy.record("careers", "Deloitte", found=2, added=1, ledger=led)
    sy.record("careers", "Deloitte", found=0, ledger=led)
    out = "\n".join(sy.report(ledger=led))
    assert "post     1 reads, 0 hiring posts, 0 roles found, 0 new cards" in out
    assert "careers  2 reads, 0 hiring posts, 2 roles found, 1 new cards" in out
    assert "Deloitte" in out


def test_old_rows_fall_out_of_the_window(tmp_path):
    led = tmp_path / "y.jsonl"
    old = datetime.now(timezone.utc) - timedelta(days=200)
    sy.record("post", "apple", found=5, ledger=led, now=old)
    assert "no sweep reads" in sy.report(90, led)[0] or sy.rows(90, led) == []


def test_marks_write_the_ledger(tmp_path, monkeypatch):
    import careers_queue as cq
    import post_leads as pl
    monkeypatch.setattr(cq, "STATE", tmp_path / "c.json")
    monkeypatch.setattr(pl, "QUERIES", tmp_path / "q.json")
    cq.done("Tesla", roles=3, added=1)
    pl.mark_searched(["company|apple"], hits=1, found=2, added=0)
    real = Path(sy.LEDGER)
    before = real.read_text(encoding="utf-8") if real.exists() else None
    rows = sy.rows(ledger=tmp_path / "sweep_yield.jsonl")
    assert [(r["lane"], r["company"], r["found"], r["added"]) for r in rows] == [("careers", "Tesla", 3, 1), ("post", "apple", 2, 0)]
    assert (real.read_text(encoding="utf-8") if real.exists() else None) == before   # tests never touch the real ledger
