"""Company ATS boards (Greenhouse, Workday, …) from boards.json, fetched with ats-scrapers."""
from __future__ import annotations

import json
import re
from urllib.parse import urlsplit

import httpx

from jobradar.common import ROOT, countries_for, fetch_many, job_countries, title_matches
from jobradar.model import Posting, SourceResult, UnitStatus
from jobradar.sources import register


def job_to_posting(job, board: dict) -> Posting:
    gid = getattr(job, "global_id", "") or ""
    # ats-scrapers falls back to a random UUID when a board has no job id; that would
    # look new every run, so only trust ids of the documented "ats:id" form.
    ext = gid if ":" in gid else str(job.url)
    return Posting(
        source="ats",
        company=(getattr(job, "company", None) or board["companies"][0]).strip(),
        title=(job.title or "").strip(),
        location=(job.location or "").strip(),
        countries=frozenset(job_countries(job)),
        url=str(job.url),
        external_id=ext,
        posted_at=getattr(job, "posted_at", None),
        raw={"ats": board["ats"], "board": board["url"], "slug": board["slug"]},
        company_hint=tuple(board["companies"]),
    )


_ROLLUP = re.compile(r"^\s*\d+\s+Locations?\s*$", re.I)


def workday_detail_url(job_url: str) -> str | None:
    """https://co.wd3.myworkdayjobs.com/[en-US/]site/job/... -> the cxs detail API URL."""
    u = urlsplit(job_url)
    head, sep, tail = u.path.partition("/job/")
    if not sep or "myworkdayjobs.com" not in u.netloc:
        return None
    site = head.rstrip("/").split("/")[-1]
    company = u.netloc.split(".")[0]
    return f"https://{u.netloc}/wday/cxs/{company}/{site}/job/{tail}"


async def resolve_workday_rollups(postings: list[Posting], client: httpx.AsyncClient) -> int:
    """Workday lists multi-office jobs as "2 Locations" with no country, so they'd be
    dropped by the country filter. ats-scrapers only resolves these when fetching
    every description (thousands of requests), so resolve just the few whose title
    already matches. Returns how many were resolved."""
    todo = [p for p in postings
            if p.raw.get("ats") == "workday" and _ROLLUP.match(p.location) and title_matches(p.title)]
    done = 0
    for p in todo:
        url = workday_detail_url(p.url)
        if not url:
            continue
        try:
            r = await client.get(url, headers={"Accept": "application/json"})
            if r.status_code != 200:
                continue
            info = r.json().get("jobPostingInfo") or {}
        except (httpx.HTTPError, ValueError):
            continue
        locs = [info.get("location"), *(info.get("additionalLocations") or [])]
        locs = [l.strip() for l in locs if isinstance(l, str) and l.strip()]
        if locs:
            p.location = " | ".join(dict.fromkeys(locs))
            # info["country"] only describes the primary office, so use the text of all offices
            p.countries = frozenset(countries_for(None, p.location))
            done += 1
    return done


class AtsSource:
    name = "ats"

    def __init__(self, cfg: dict):
        self.timeout = float(cfg.get("timeout_seconds", 2700))
        self.boards_file = ROOT / cfg.get("boards_file", "boards.json")

    async def fetch(self) -> SourceResult:
        if not self.boards_file.exists():
            raise FileNotFoundError(f"{self.boards_file.name} missing — run verify_boards.py first")
        boards = json.loads(self.boards_file.read_text())
        results = await fetch_many([(b["ats"], b["slug"], b["url"]) for b in boards], progress=False)
        out = SourceResult(self.name)
        for b in boards:
            r = results[b["url"]]
            out.units.append(UnitStatus(b["url"], ok=r.ok, raw_count=len(r.jobs), error=r.error,
                                        label=f"{', '.join(b['companies'])}: {b['url']}"))
            out.postings += [job_to_posting(j, b) for j in r.jobs]
        async with httpx.AsyncClient(timeout=20.0, headers={"User-Agent": "Mozilla/5.0"}) as client:
            await resolve_workday_rollups(out.postings, client)
        return out


register("ats")(AtsSource)
