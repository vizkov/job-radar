"""ATS adapter against recorded board responses (tests/fixtures/ats/, recorded 2026-09-27)."""
import asyncio
import json
from pathlib import Path
from types import SimpleNamespace

import httpx
import respx

import radar
from jobradar.model import SourceResult
from jobradar.sources.ats import job_to_posting, resolve_workday_rollups, workday_detail_url

FX = Path(__file__).parent / "fixtures" / "ats"


def load(name):
    d = json.loads((FX / f"{name}.json").read_text(encoding="utf-8"))
    board = {**d["board"], "companies": [d["board"]["slug"].split("/")[-1].title()]}
    jobs = [SimpleNamespace(**{**j, "global_id": f"{j['ats_type']}:{j['ats_id']}", "posted_at": None}) for j in d["jobs"]]
    return board, jobs


def test_greenhouse_fixture_converts():
    board, jobs = load("monzo_greenhouse")
    board["companies"] = ["Monzo"]
    ps = [job_to_posting(j, board) for j in jobs]
    assert len(ps) == len(jobs) > 20
    assert all(p.source == "ats" and p.url.startswith("https://") for p in ps)
    assert all(p.external_id.startswith("greenhouse:") for p in ps)
    # every Monzo posting resolves to at least one country from its location text
    assert sum(1 for p in ps if p.countries) / len(ps) > 0.9
    res = SourceResult("ats", postings=ps)
    kept, _ = radar.select([res], include_outside=False)
    assert all(p.company_canonical == "Monzo" for p in kept)


def test_workday_detail_url():
    assert workday_detail_url("https://snyk.wd103.myworkdayjobs.com/external/job/X/Title_JR1") == \
        "https://snyk.wd103.myworkdayjobs.com/wday/cxs/snyk/external/job/X/Title_JR1"
    assert workday_detail_url("https://acme.wd3.myworkdayjobs.com/en-US/careers/job/London/T_1") == \
        "https://acme.wd3.myworkdayjobs.com/wday/cxs/acme/careers/job/London/T_1"
    assert workday_detail_url("https://example.com/job/1") is None


@respx.mock
def test_workday_rollup_resolved_from_detail():
    board, jobs = load("snyk_workday")
    board["companies"] = ["Snyk"]
    ps = [job_to_posting(j, board) for j in jobs]
    rollup = [p for p in ps if p.title == "Senior Product Security Engineer"][0]
    assert rollup.location == "2 Locations" and not rollup.countries
    detail = json.loads((FX / "snyk_workday_detail.json").read_text(encoding="utf-8"))
    respx.get(workday_detail_url(rollup.url)).mock(return_value=httpx.Response(200, json=detail))

    async def go():
        async with httpx.AsyncClient() as c:
            return await resolve_workday_rollups(ps, c)
    assert asyncio.run(go()) == 1
    assert rollup.location == "United States - Boston Office | Canada - Ottawa Local"
    assert rollup.countries == frozenset({"US", "CA"})  # named, not targets: correctly dropped


@respx.mock
def test_workday_rollup_in_europe_is_kept():
    board, jobs = load("snyk_workday")
    ps = [job_to_posting(j, board) for j in jobs]
    rollup = [p for p in ps if p.title == "Senior Product Security Engineer"][0]
    detail = {"jobPostingInfo": {"location": "United States - Boston Office",
                                 "additionalLocations": ["United Kingdom - London Office"]}}
    respx.get(workday_detail_url(rollup.url)).mock(return_value=httpx.Response(200, json=detail))

    async def go():
        async with httpx.AsyncClient() as c:
            await resolve_workday_rollups(ps, c)
    asyncio.run(go())
    assert "GB" in rollup.countries
