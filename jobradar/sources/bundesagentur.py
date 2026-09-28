"""Bundesagentur für Arbeit job search (Germany's public employment service).

Documented public API (https://jobsuche.api.bund.dev/), fixed public API key.
Heavy with staffing agencies (FERCHAU, Hays, …), so most results land outside
your target list. EURES mirrors these listings, so Germany is searched here and
excluded from the EURES adapter.
"""
from __future__ import annotations

from datetime import datetime

from jobradar.common import countries_for
from jobradar.model import Posting
from jobradar.sources import _http, register
from jobradar.sources.search import SearchSource

API = "https://rest.arbeitsagentur.de/jobboerse/jobsuche-service/pc/v6/jobs"
HEADERS = {"X-API-Key": "jobboerse-jobsuche"}  # public key published in the API docs
PAGE_SIZE = 50


def parse(item: dict) -> Posting:
    locs = item.get("stellenlokationen") or [{}]
    addr = locs[0].get("adresse") or {}
    location = ", ".join(x for x in [addr.get("ort"), (addr.get("land") or "").title()] if x)
    ref = item.get("referenznummer") or item.get("refnr") or ""
    posted = item.get("datumErsteVeroeffentlichung") or (item.get("veroeffentlichungszeitraum") or {}).get("von")
    return Posting(
        source="bundesagentur",
        company=(item.get("firma") or "").strip(),
        title=(item.get("stellenangebotsTitel") or item.get("titel") or "").strip(),
        location=location,
        countries=frozenset(countries_for(None, location) or ({"DE"} if not addr.get("land") else set())),
        url=f"https://www.arbeitsagentur.de/jobsuche/jobdetail/{ref}",
        external_id=ref,
        posted_at=datetime.fromisoformat(posted) if posted else None,
        raw={"hauptberuf": item.get("hauptberuf")},
    )


class BundesagenturSource(SearchSource):
    name = "bundesagentur"
    default_queries = ["Penetration Tester", "Pentester", "Application Security", "AppSec", "Product Security",
                       "Security Consultant", "Security Engineer", "DevSecOps", "Threat Modeling",
                       "Ethical Hacker"]

    async def _page(self, c, query, page, size):
        params = {"was": query, "angebotsart": 1, "veroeffentlichtseit": self.days, "size": size, "page": page}
        return (await _http.request(c, "GET", API, params=params, headers=HEADERS)).json()

    async def search(self, c, query):
        postings, total = [], 0
        for page in range(1, self.max_pages + 1):
            d = await self._page(c, query, page, PAGE_SIZE)
            total = int(d.get("maxErgebnisse") or 0)
            items = d.get("ergebnisliste") or d.get("stellenangebote") or []
            postings += [parse(i) for i in items]
            if not items or page * PAGE_SIZE >= total:
                break
        return postings, total

    async def count(self, c, query):
        return int((await self._page(c, query, 1, 1)).get("maxErgebnisse") or 0)


register("bundesagentur")(BundesagenturSource)
