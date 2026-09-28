"""Shared HTTP client for adapters that talk to public APIs directly.

Polite by default: one request at a time per source, a short pause between
requests, and a couple of retries with backoff on 429/5xx.
"""
from __future__ import annotations

import asyncio

import httpx

USER_AGENT = "job-radar/1.0 (personal job-alert tool; low volume, daily)"
PAUSE = 0.5      # seconds between requests; tests set these to 0
BACKOFF = 2.0    # base retry delay on 429/5xx


def client(timeout: float = 30.0, headers: dict | None = None) -> httpx.AsyncClient:
    return httpx.AsyncClient(timeout=timeout, follow_redirects=True,
                             headers={"User-Agent": USER_AGENT, "Accept": "application/json", **(headers or {})})


async def request(c: httpx.AsyncClient, method: str, url: str, *, retries: int = 2, **kw) -> httpx.Response:
    for attempt in range(retries + 1):
        r = await c.request(method, url, **kw)
        if r.status_code not in (429, 500, 502, 503, 504) or attempt == retries:
            r.raise_for_status()
            await asyncio.sleep(PAUSE)
            return r
        await asyncio.sleep(_retry_after(r) or BACKOFF * (attempt + 1))
    raise AssertionError("unreachable")


def _retry_after(r: httpx.Response) -> float:
    try:
        return min(float(r.headers.get("Retry-After", 0)), 60.0)
    except ValueError:  # HTTP-date form; not worth parsing
        return 0.0
