"""Base for keyword-search sources (public job APIs).

A search source runs each configured query, paginates up to max_pages, and
reports one health unit per query (errors only — a narrow query returning
nothing this week is normal) plus one canary unit for `health_query`, a broad
search whose result count should never be zero. Title/country filtering happens
centrally in radar.py, so queries only need to be good enough to narrow the
result set.
"""
from __future__ import annotations

from jobradar.model import Posting, SourceResult, UnitStatus
from jobradar.sources import _http


class SearchSource:
    name = "search"
    default_queries: list[str] = []

    def __init__(self, cfg: dict):
        self.timeout = float(cfg.get("timeout_seconds", 300))
        self.days = int(cfg.get("days", 7))
        self.max_pages = int(cfg.get("max_pages", 5))
        self.queries = list(cfg.get("queries") or self.default_queries)
        self.health_query = cfg.get("health_query", "security")
        self.cfg = cfg

    async def search(self, c, query: str) -> tuple[list[Posting], int]:
        """Return (postings, total results reported by the API) for one query."""
        raise NotImplementedError

    async def count(self, c, query: str) -> int:
        """Total results for the canary query; default runs a normal search."""
        return (await self.search(c, query))[1]

    async def fetch(self) -> SourceResult:
        out = SourceResult(self.name)
        async with _http.client() as c:
            for q in self.queries:
                try:
                    postings, total = await self.search(c, q)
                    out.postings += postings
                    out.units.append(UnitStatus(f"q:{q}", ok=True, raw_count=total, label=f"query {q!r}",
                                                track_empty=False))
                except Exception as e:  # one bad query must not lose the others
                    out.units.append(UnitStatus(f"q:{q}", ok=False, error=f"{type(e).__name__}: {str(e)[:150]}",
                                                label=f"query {q!r}", track_empty=False))
            try:
                n = await self.count(c, self.health_query)
                out.units.append(UnitStatus("canary", ok=True, raw_count=n, label=f"canary query {self.health_query!r}"))
            except Exception as e:
                out.units.append(UnitStatus("canary", ok=False, error=f"{type(e).__name__}: {str(e)[:150]}",
                                            label=f"canary query {self.health_query!r}"))
        if out.units and not any(u.ok for u in out.units):
            out.ok, out.error = False, out.units[0].error
        return out
