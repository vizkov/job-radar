"""Workday boards, fetched at a pace Workday accepts (the user, 2026-11-21: "fix this": about 40 Workday boards had failed for 14 runs).

Why: Workday answers 429 when requests come too fast. The ats-scrapers library fans out every page of every tenant at once (10 at a time per
tenant, 6 tenants in parallel) and retries for under a minute, so from about 2026-11-14 whole boards came back "Workday gave up after 6
retries". Measured on 2026-11-21: one request a second per host mostly gets 200; 0.3 s gets 429 on all of them, and a burst leaves the
address penalised for minutes. This module replaces the library's single-request method (`WorkdayScraper._request`) with one that:

* waits on ONE shared gate (all Workday tenants together, `workday_min_interval` seconds apart, default 2.0): the limit is per address, not per tenant;
* on a 429 / 403 / 5xx pushes the whole gate back (Retry-After, else 30 s) and DOUBLES the interval (30 s at most); 15 successes in a row shrink it again.
  Measured 2026-11-21: three requests two seconds apart got 200, the fourth 429, and requests made while blocked extended the block to 40-75 s;
* sends a search term (`workday_search_terms`) and stops after `workday_max_pages` pages per term (a board then costs a few requests, not hundreds;
  results are newest first, and older listings were seen by earlier runs);
* gives up for the run when the first two requests of the run are both refused ("blocked": measured 2026-11-21, GitHub's runner address got a 429
  for the whole 150 s budget on the first board, while the same code from a home address was served after a pause): `BLOCKED[0]` is set, every board is
  deferred and `AtsSource` reports one "Workday blocked" unit instead of a failure per board;
* stops asking once the run's time budget (`DEADLINE`, `workday_budget_seconds`) has passed: the board in progress and every board not yet tried are
  "deferred", tried first on the next run (`common.fetch_workday_boards`).

Everything else (pagination, parsing, the 404 / non-JSON handling) is the library's. Imported by `jobradar.common`, which also loops the terms.
"""
from __future__ import annotations

import asyncio
import contextvars
import time

import httpx
from ats_scrapers.exceptions import CompanyNotFoundError, ScraperError
from ats_scrapers.scrapers import workday as _wd

TERM: contextvars.ContextVar[str] = contextvars.ContextVar("workday_term", default="")
SETTINGS = {"min_interval": 2.0, "max_retries": 8, "max_pages": 2, "block_after": 2}
BLOCKED = [False]   # set when the run's first requests were all refused: the address is blocked, so stop asking
SENT = [0]   # requests sent so far (the caller compares before and after a board)
DEADLINE: list = [None]   # time.monotonic() value after which no request is sent; None = no budget


class Deferred(ScraperError):
    """The run's Workday time budget is spent: not a failure of the board."""
RETRYABLE = {403, 429, 502, 503, 504}

_gates: dict[int, "Gate"] = {}   # one per running event loop (asyncio primitives belong to a loop)


class Gate:
    """Spaces requests out and lets a refusal slow everybody down."""

    def __init__(self) -> None:
        self.lock = asyncio.Lock()
        self.next_at = 0.0
        self.interval = 0.0   # the current spacing; 0 = not set yet (SETTINGS["min_interval"])
        self.streak = 0       # successes since the last refusal
        self.refused = 0      # refusals in a row
        self.served = 0       # successes this run

    async def wait(self, base: float) -> None:
        async with self.lock:
            self.interval = self.interval or base
            now = time.monotonic()
            if self.next_at > now:
                await asyncio.sleep(self.next_at - now)
            self.next_at = max(self.next_at, time.monotonic()) + self.interval

    def back_off(self, seconds: float) -> None:
        """A refusal: everybody waits, and the spacing doubles (30 s at most)."""
        self.next_at = max(self.next_at, time.monotonic() + seconds)
        self.interval = min(30.0, (self.interval or SETTINGS["min_interval"]) * 2)
        self.streak = 0
        self.refused += 1
        if self.refused >= int(SETTINGS["block_after"]) and self.served == 0:
            BLOCKED[0] = True

    def success(self, base: float) -> None:
        self.streak += 1
        self.refused = 0
        self.served += 1
        if self.streak >= 15 and self.interval > base:
            self.interval, self.streak = max(base, self.interval * 0.7), 0


def gate() -> Gate:
    loop = asyncio.get_running_loop()
    g = _gates.get(id(loop))
    if g is None:
        _gates.clear()   # an old loop's gate is useless
        g = _gates[id(loop)] = Gate()
    return g


def retry_delay(attempt: int, retry_after: str | None) -> float:
    if retry_after and retry_after.isdigit():
        return min(120.0, float(retry_after))
    return min(60.0, 30.0 + 5.0 * attempt)


async def paced_request(self, client: httpx.AsyncClient, api: str, sem: asyncio.Semaphore, *, applied_facets: dict, offset: int) -> dict | None:
    if offset >= int(SETTINGS["max_pages"]) * _wd.PAGE_LIMIT and TERM.get():
        return {"total": offset, "jobPostings": []}   # newest-first results: the first pages hold what is new
    body = {"appliedFacets": applied_facets, "limit": _wd.PAGE_LIMIT, "offset": offset, "searchText": TERM.get()}
    g = gate()
    last: Exception | str | None = None
    for attempt in range(int(SETTINGS["max_retries"])):
        self._check_deadline()
        if BLOCKED[0]:
            raise Deferred("Workday refuses this address (429): skipped for this run")
        if DEADLINE[0] is not None and time.monotonic() >= DEADLINE[0]:
            raise Deferred("Workday time budget for this run is spent")
        await g.wait(float(SETTINGS["min_interval"]))
        SENT[0] += 1
        try:
            response = await client.post(api, json=body, headers={"Content-Type": "application/json"})
        except httpx.HTTPError as exc:
            last = exc
            g.back_off(retry_delay(attempt, None) / 2)
            continue
        if response.status_code == 404:
            raise CompanyNotFoundError(f"Workday site not found: {self.company_slug}")
        if response.status_code == 200:
            try:
                payload = response.json()
            except ValueError:
                last = "non-JSON success response"
                g.back_off(retry_delay(attempt, None) / 2)
                continue
            if isinstance(payload, dict):
                g.success(float(SETTINGS["min_interval"]))
                return payload
            last = "unexpected JSON payload"
            continue
        if response.status_code in RETRYABLE:
            last = f"HTTP {response.status_code}"
            g.back_off(retry_delay(attempt, response.headers.get("Retry-After")))
            continue
        raise ScraperError(f"Workday returned {response.status_code} for {self.company_slug} (offset={offset})")
    raise ScraperError(f"Workday gave up after {SETTINGS['max_retries']} tries at offset={offset}: {last}")


def install(min_interval: float = 2.0, max_retries: int = 8, max_pages: int = 2) -> None:
    SETTINGS.update(min_interval=float(min_interval), max_retries=int(max_retries), max_pages=int(max_pages))
    _wd.WorkdayScraper._request = paced_request   # type: ignore[method-assign]
    _wd.MAX_CONCURRENCY = 2   # pages in flight per tenant: the gate sets the real pace
