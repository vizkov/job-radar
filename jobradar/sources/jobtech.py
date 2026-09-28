"""Arbetsförmedlingen / JobTech JobSearch API (Sweden's public employment service).

Open data, no key: https://jobsearch.api.jobtechdev.se. Queries are sent as
quoted phrases; unquoted multi-word queries are OR-ed and return thousands of
unrelated ads. Many Swedish ads use Swedish titles ("Pentestare",
"IT-säkerhetsspecialist"); config.json's title filter decides what survives.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from jobradar.common import countries_for
from jobradar.model import Posting
from jobradar.sources import _http, register
from jobradar.sources.search import SearchSource

API = "https://jobsearch.api.jobtechdev.se/search"
PAGE_SIZE = 100


def parse(hit: dict) -> Posting:
    addr = hit.get("workplace_address") or {}
    country = addr.get("country") or "Sverige"
    location = ", ".join(x for x in [addr.get("municipality") or addr.get("city"), country] if x)
    posted = hit.get("publication_date")
    return Posting(
        source="jobtech",
        company=((hit.get("employer") or {}).get("name") or "").strip(),
        title=(hit.get("headline") or "").strip(),
        location=location,
        countries=frozenset(countries_for(None, location)),
        url=hit.get("webpage_url") or f"https://arbetsformedlingen.se/platsbanken/annonser/{hit.get('id')}",
        external_id=str(hit.get("id") or ""),
        posted_at=datetime.fromisoformat(posted) if posted else None,
    )


class JobTechSource(SearchSource):
    name = "jobtech"
    default_queries = ["application security", "appsec", "product security", "penetration tester",
                       "penetrationstest", "pentest", "pentestare", "security engineer", "security consultant",
                       "devsecops", "threat modeling", "ethical hacker"]

    async def _get(self, c, query, offset, limit):
        since = (datetime.now(timezone.utc) - timedelta(days=self.days)).strftime("%Y-%m-%dT%H:%M:%S")
        q = f'"{query}"' if " " in query else query
        params = {"q": q, "published-after": since, "offset": offset, "limit": limit}
        return (await _http.request(c, "GET", API, params=params)).json()

    async def search(self, c, query):
        postings, total = [], 0
        for page in range(self.max_pages):
            d = await self._get(c, query, page * PAGE_SIZE, PAGE_SIZE)
            total = int((d.get("total") or {}).get("value") or 0)
            hits = d.get("hits") or []
            postings += [parse(h) for h in hits]
            if not hits or (page + 1) * PAGE_SIZE >= total:
                break
        return postings, total

    async def count(self, c, query):
        return int(((await self._get(c, query, 0, 0)).get("total") or {}).get("value") or 0)


register("jobtech")(JobTechSource)
