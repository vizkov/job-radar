from jobradar.health import update_health
from jobradar.model import SourceResult, UnitStatus


def run(health, *results):
    return update_health(health, list(results))


def ok(src, key, n):
    return SourceResult(src, units=[UnitStatus(key, ok=True, raw_count=n, label=key)])


def test_board_that_went_silent_is_flagged_after_two_runs():
    h = {}
    assert run(h, ok("ats", "b1", 12)) == []
    assert run(h, ok("ats", "b1", 0)) == []
    broken = run(h, ok("ats", "b1", 0))
    assert broken == [("ats", "b1", "returned 0 results")]
    assert run(h, ok("ats", "b1", 5)) == []   # recovers


def test_never_worked_unit_is_not_flagged():
    h = {}
    for _ in range(3):
        broken = run(h, ok("ats", "dead", 0))
    assert broken == []


def test_whole_source_failure_flags_known_units_and_source():
    h = {}
    run(h, ok("eures", "q:security", 40))
    fail = SourceResult("eures", ok=False, error="timeout after 300s")
    assert run(h, fail) == []
    broken = run(h, fail)
    assert ("eures", "q:security", "timeout after 300s") in broken
    assert ("eures", "eures (whole source)", "timeout after 300s") in broken
    run(h, ok("eures", "q:security", 3))
    assert h["eures|*"]["bad_streak"] == 0


def test_error_unit():
    h = {}
    run(h, ok("ats", "b", 3))
    err = SourceResult("ats", units=[UnitStatus("b", ok=False, error="HTTP 404", label="b")])
    run(h, err)
    assert run(h, err) == [("ats", "b", "HTTP 404")]


def test_error_is_reported_even_if_the_unit_never_worked():
    h = {}
    bad = SourceResult("alert_email", units=[UnitStatus("linkedin:rejected", ok=False, error="3 of 3 failed DKIM",
                                                        label="linkedin DKIM", track_empty=False)])
    run(h, bad)
    assert run(h, bad) == [("alert_email", "linkedin DKIM", "3 of 3 failed DKIM")]
