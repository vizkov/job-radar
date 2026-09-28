"""EURES — the EU's cross-border job portal (aggregates national employment services).

Uses the portal's public search endpoint (no key). Findings from testing:
- Keyword search only filters properly with specificSearchCode=TITLE and one or
  two words; it is fuzzy ("appsec" also returns "Apple"), so config.json's title
  filter does the real work.
- The UK is not in EURES. German listings mirror the Bundesagentur feed, so DE
  is left out here by default (use the bundesagentur source).
"""
from __future__ import annotations

from datetime import datetime, timezone

from jobradar.common import CONFIG
from jobradar.model import Posting
from jobradar.sources import _http, register
from jobradar.sources.search import SearchSource

API = "https://europa.eu/eures/api/jv-searchengine/public/jv-search/search"
PAGE_SIZE = 50
_PERIODS = {1: "LAST_DAY", 3: "LAST_THREE_DAYS", 7: "LAST_WEEK", 30: "LAST_MONTH"}


def parse(jv: dict) -> Posting:
    countries = sorted((jv.get("locationMap") or {}).keys())
    regions = [r for rs in (jv.get("locationMap") or {}).values() for r in (rs or []) if r]  # regions can be null
    ms = jv.get("creationDate")
    return Posting(
        source="eures",
        company=((jv.get("employer") or {}).get("name") or "").strip(),
        title=(jv.get("title") or "").strip(),
        location=", ".join(countries) + (f" ({', '.join(regions[:3])})" if regions else ""),
        countries=frozenset("GB" if c == "UK" else c for c in countries),
        url=f"https://europa.eu/eures/portal/jv-se/jv-details/{jv.get('id')}?lang=en",
        external_id=str(jv.get("id") or ""),
        posted_at=datetime.fromtimestamp(ms / 1000, tz=timezone.utc) if ms else None,
    )


class EuresSource(SearchSource):
    name = "eures"
    default_queries = ["penetration", "pentest", "pentester", "appsec", "application security",
                       "product security", "security engineer", "security consultant", "devsecops",
                       "ethical hacker", "threat modeling"]

    def __init__(self, cfg: dict):
        super().__init__(cfg)
        default = [c for c in CONFIG["priority_countries"] if c not in ("GB", "DE")]
        self.countries = [c.lower() for c in cfg.get("countries") or default]
        self.period = _PERIODS.get(self.days) or "LAST_WEEK"

    def _body(self, query, page, size):
        return {"resultsPerPage": size, "page": page, "sortSearch": "MOST_RECENT",
                "keywords": [{"keyword": query, "specificSearchCode": "TITLE"}],
                "publicationPeriod": self.period, "locationCodes": self.countries,
                "occupationUris": [], "skillUris": [], "requiredExperienceCodes": [], "positionScheduleCodes": [],
                "sectorCodes": [], "educationAndQualificationLevelCodes": [], "positionOfferingCodes": [],
                "euresFlagCodes": [], "otherBenefitsCodes": [], "requiredLanguages": [], "minNumberPost": None,
                "sessionId": "job-radar"}

    async def search(self, c, query):
        postings, total = [], 0
        for page in range(1, self.max_pages + 1):
            d = (await _http.request(c, "POST", API, json=self._body(query, page, PAGE_SIZE))).json()
            total = int(d.get("numberRecords") or 0)
            jvs = d.get("jvs") or []
            postings += [parse(j) for j in jvs]
            if not jvs or page * PAGE_SIZE >= total:
                break
        return postings, total

    async def count(self, c, query):
        d = (await _http.request(c, "POST", API, json=self._body(query, 1, 1))).json()
        return int(d.get("numberRecords") or 0)


register("eures")(EuresSource)
