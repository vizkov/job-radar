"""EU public sources against responses recorded 2026-09-27 (tests/fixtures/eu/)."""
import asyncio
import json
from pathlib import Path

import httpx
import respx

import radar
from jobradar.sources import bundesagentur, eures, jobtech

FX = Path(__file__).parent / "fixtures" / "eu"


def fx(name):
    return json.loads((FX / f"{name}.json").read_text(encoding="utf-8"))


def run(src):
    return asyncio.run(src.fetch())


@respx.mock
def test_bundesagentur():
    data = fx("bundesagentur")
    route = respx.get(bundesagentur.API).mock(return_value=httpx.Response(200, json=data))
    res = run(bundesagentur.BundesagenturSource({"queries": ["Penetration Tester"], "days": 30}))
    assert res.ok and len(res.postings) == len(data["ergebnisliste"]) > 5
    assert route.calls[0].request.headers["X-API-Key"] == "jobboerse-jobsuche"
    assert "was=Penetration+Tester" in str(route.calls[0].request.url)
    p = res.postings[0]
    assert p.countries == {"DE"} and p.url.startswith("https://www.arbeitsagentur.de/jobsuche/jobdetail/")
    assert p.company and p.external_id
    canary = [u for u in res.units if u.key == "canary"][0]
    assert canary.ok and canary.raw_count == data["maxErgebnisse"]


@respx.mock
def test_jobtech_quotes_phrases():
    data = fx("jobtech")
    route = respx.get(jobtech.API).mock(return_value=httpx.Response(200, json=data))
    res = run(jobtech.JobTechSource({"queries": ["security engineer"]}))
    assert "q=%22security+engineer%22" in str(route.calls[0].request.url)
    assert len(res.postings) == len(data["hits"])
    assert all("SE" in p.countries for p in res.postings)
    assert all(p.url.startswith("https://") for p in res.postings)


@respx.mock
def test_eures_title_search_and_countries():
    data = fx("eures")
    route = respx.post(eures.API).mock(return_value=httpx.Response(200, json=data))
    src = eures.EuresSource({"queries": ["pentest"]})
    assert "gb" not in src.countries and "de" not in src.countries  # UK not in EURES; DE via bundesagentur
    res = run(src)
    body = json.loads(route.calls[0].request.content)
    assert body["keywords"] == [{"keyword": "pentest", "specificSearchCode": "TITLE"}]
    assert len(res.postings) == len(data["jvs"])
    assert all(p.countries and p.url.startswith("https://europa.eu/eures/") for p in res.postings)
    # the fixture has fuzzy non-matches too; the central title filter removes them
    kept, _ = radar.select([res], include_outside=True)
    assert 0 < len(kept) < len(res.postings) or all("pentest" in p.title.lower() for p in kept)


@respx.mock
def test_one_failing_query_keeps_the_rest():
    data = fx("bundesagentur")
    calls = {"n": 0}

    def handler(request):
        calls["n"] += 1
        if "AppSec" in str(request.url):
            return httpx.Response(403, text="forbidden")
        return httpx.Response(200, json=data)
    respx.get(bundesagentur.API).mock(side_effect=handler)
    res = run(bundesagentur.BundesagenturSource({"queries": ["AppSec", "Pentester"]}))
    assert res.ok
    bad = [u for u in res.units if not u.ok]
    assert [u.key for u in bad] == ["q:AppSec"] and "403" in bad[0].error
    assert res.postings
