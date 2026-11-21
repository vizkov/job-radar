"""Workday requests at a pace Workday accepts (the user, 2026-11-21: ~40 boards had failed for 14 runs with 429s)."""
import asyncio
from types import SimpleNamespace

import pytest

from jobradar import workday_paced as wp


class FakeResp:
    def __init__(self, status, payload=None, headers=None):
        self.status_code, self._p, self.headers = status, payload, headers or {}

    def json(self):
        return self._p


class FakeClient:
    def __init__(self, statuses):
        self.statuses, self.bodies = list(statuses), []

    async def post(self, api, json=None, headers=None):
        self.bodies.append(json)
        st = self.statuses.pop(0)
        return FakeResp(st, {"total": 1, "jobPostings": []} if st == 200 else None)


def run(coro):
    return asyncio.run(coro)


@pytest.fixture(autouse=True)
def fast(monkeypatch):
    wp.BLOCKED[0] = False
    monkeypatch.setitem(wp.SETTINGS, "block_after", 99)   # the blocked-address breaker has its own tests below
    monkeypatch.setitem(wp.SETTINGS, "min_interval", 0.0)
    monkeypatch.setitem(wp.SETTINGS, "max_retries", 4)
    monkeypatch.setattr(wp, "retry_delay", lambda attempt, ra: 0.0)


def call(client, term=""):
    me = SimpleNamespace(company_slug="https://x.wd1.myworkdayjobs.com/site", _check_deadline=lambda: None)

    async def go():
        tok = wp.TERM.set(term)
        try:
            return await wp.paced_request(me, client, "api", None, applied_facets={}, offset=20)
        finally:
            wp.TERM.reset(tok)
    return run(go())


def test_retries_a_429_then_succeeds_and_sends_the_search_term():
    c = FakeClient([429, 429, 200])
    assert call(c, "security engineer")["total"] == 1
    assert len(c.bodies) == 3 and all(b["searchText"] == "security engineer" and b["offset"] == 20 for b in c.bodies)


def test_gives_up_after_the_retry_limit_with_a_clear_error():
    with pytest.raises(wp.ScraperError, match="gave up after 4 tries at offset=20: HTTP 429"):
        call(FakeClient([429] * 4))


def test_404_is_a_missing_board_not_a_retry():
    c = FakeClient([404])
    with pytest.raises(wp.CompanyNotFoundError):
        call(c)
    assert len(c.bodies) == 1


def test_a_refusal_pushes_the_shared_gate_back():
    async def go():
        g = wp.gate()
        before = g.next_at
        g.back_off(30)
        return g.next_at - before
    assert run(go()) >= 29


def test_retry_after_header_wins_and_is_capped():
    import importlib
    real = importlib.reload(wp)
    assert real.retry_delay(0, "7") == 7.0
    assert real.retry_delay(0, "9999") == 120.0
    assert real.retry_delay(0, None) == 30.0 and real.retry_delay(9, None) == 60.0


def test_a_refusal_doubles_the_spacing_and_successes_shrink_it():
    g = wp.Gate()
    g.interval = 2.0
    g.back_off(1)
    g.back_off(1)
    assert g.interval == 8.0
    for _ in range(15):
        g.success(2.0)
    assert 2.0 < g.interval < 8.0


def test_pages_past_the_cap_are_not_requested_for_a_search_term(monkeypatch):
    monkeypatch.setitem(wp.SETTINGS, "max_pages", 2)
    c = FakeClient([])
    assert call_offset(c, "security engineer", 40) == {"total": 40, "jobPostings": []} and c.bodies == []


def test_the_run_budget_defers_instead_of_failing(monkeypatch):
    import time
    wp.DEADLINE[0] = time.monotonic() - 1
    c = FakeClient([200])
    try:
        with pytest.raises(wp.Deferred):
            call(c)
        assert c.bodies == []
    finally:
        wp.DEADLINE[0] = None


def call_offset(client, term, offset):
    me = SimpleNamespace(company_slug="https://x.wd1.myworkdayjobs.com/site", _check_deadline=lambda: None)

    async def go():
        tok = wp.TERM.set(term)
        try:
            return await wp.paced_request(me, client, "api", None, applied_facets={}, offset=offset)
        finally:
            wp.TERM.reset(tok)
    return run(go())


def test_two_refusals_with_nothing_served_block_the_run_and_later_boards_defer():
    wp.BLOCKED[0] = False
    wp.SETTINGS["block_after"] = 2
    g = wp.Gate()
    g.back_off(0)
    assert not wp.BLOCKED[0]
    g.back_off(0)
    assert wp.BLOCKED[0]
    c = FakeClient([200])
    try:
        with pytest.raises(wp.Deferred):
            call(c)
        assert c.bodies == []
    finally:
        wp.BLOCKED[0] = False
        wp.SETTINGS["block_after"] = 99


def test_a_served_request_means_the_address_is_not_blocked():
    wp.BLOCKED[0] = False
    wp.SETTINGS["block_after"] = 2
    g = wp.Gate()
    g.success(2.0)
    g.back_off(0)
    g.back_off(0)
    assert not wp.BLOCKED[0]
