"""Reed.co.uk: the UK job board's official Jobs API (https://www.reed.co.uk/developers).

Needs a free API key (the user registers with their own account). It is sent as the HTTP Basic
username with an empty password, read from the REED_API_KEY environment variable: a GitHub Actions
secret passed to the radar step only. A Reed key can only search jobs, so it isn't isolated like the
mailbox password.

Searches are UK-only and ask the API for permanent roles (permanent=true). Many Reed listings are
posted by recruitment agencies, whose name then appears as the employer, so they rarely match the
target list; the status card's per-source breakdown shows what Reed actually adds.
"""
from __future__ import annotations

import os
from datetime import datetime

import httpx

from jobradar.common import countries_for
from jobradar.model import Posting
from jobradar.sources import _http, register
from jobradar.sources.search import SearchSource

API = "https://www.reed.co.uk/api/1.0/search"
PAGE_SIZE = 100


def parse(job: dict) -> Posting:
    location = (job.get("locationName") or "").strip()
    posted = job.get("date") or ""
    try:
        when = datetime.strptime(posted, "%d/%m/%Y") if posted else None
    except ValueError:
        when = None
    jid = str(job.get("jobId") or "")
    return Posting(
        source="reed",
        company=(job.get("employerName") or "").strip(),
        title=(job.get("jobTitle") or "").strip(),
        location=location,
        # Reed is a UK board: a bare town name ("Reading") still means the UK
        countries=frozenset(countries_for("GB", location)),
        url=job.get("jobUrl") or f"https://www.reed.co.uk/jobs/{jid}",
        external_id=jid,
        posted_at=when,
        raw={"employment": "permanent"},
    )


class ReedSource(SearchSource):
    name = "reed"
    default_queries = ["application security", "appsec", "product security", "penetration tester",
                       "security consultant", "security engineer", "devsecops", "threat modelling"]

    def __init__(self, cfg: dict):
        super().__init__(cfg)
        self.location = cfg.get("location", "United Kingdom")

    def _auth(self) -> httpx.BasicAuth:
        key = os.environ.get("REED_API_KEY", "")
        if not key:
            raise RuntimeError("REED_API_KEY not set (add it as a GitHub Actions secret)")
        return httpx.BasicAuth(key, "")

    async def _page(self, c, query, skip, take):
        params = {"keywords": query, "locationName": self.location, "permanent": "true",
                  "resultsToTake": take, "resultsToSkip": skip}
        return (await _http.request(c, "GET", API, params=params, auth=self._auth())).json()

    async def search(self, c, query):
        postings, total = [], 0
        for page in range(self.max_pages):
            d = await self._page(c, query, page * PAGE_SIZE, PAGE_SIZE)
            total = int(d.get("totalResults") or 0)
            items = d.get("results") or []
            postings += [parse(j) for j in items]
            if not items or (page + 1) * PAGE_SIZE >= total:
                break
        return postings, total

    async def count(self, c, query):
        return int((await self._page(c, query, 0, 1)).get("totalResults") or 0)


register("reed")(ReedSource)
