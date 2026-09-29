"""Careers-page adapter against pages recorded 2026-09-27 (tests/fixtures/careers/)."""
import asyncio
from pathlib import Path

import httpx
import pytest
import respx
import yaml

import radar
from jobradar.paths import profile_path
from jobradar.sources.careers_page import CareersPageSource, PARSERS, clean, parse_hash, parse_selector

ROOT = Path(__file__).parent.parent
FX = Path(__file__).parent / "fixtures" / "careers"
PAGES = {p["company"]: p for p in yaml.safe_load(profile_path("careers_pages.yaml").read_text(encoding="utf-8"))}


def page_html(company):
    return (FX / f"{company.lower().replace(' ', '_')}.html").read_text(encoding="utf-8")


def titles(company):
    p = PAGES[company]
    return [x.title for x in PARSERS[p["mode"]](page_html(company), p)]


def test_mdsec():
    ps = parse_selector(page_html("MDSec"), PAGES["MDSec"])
    assert [p.title for p in ps] == ["Application Security Consultant", "Security Consultant"]
    assert all(p.countries == {"GB"} for p in ps)          # "Flexible" -> default_location
    assert len({p.id_key for p in ps}) == 2                # same Indeed link, still two jobs


def test_code_white_uses_section_ids():
    ps = parse_selector(page_html("Code White"), PAGES["Code White"])
    urls = {p.title: p.url for p in ps}
    assert urls["Senior Penetration Tester (m/f/d)"] == "https://code-white.com/careers/#pentester"
    assert all(p.countries == {"DE"} for p in ps)


def test_syss_soft_hyphens_removed():
    ts = titles("SySS")
    assert len(ts) >= 5 and not any("\xad" in t for t in ts)
    assert clean("Werk\xadstu\xaddent") == "Werkstudent"


def test_sec_consult_locations():
    ps = parse_selector(page_html("SEC Consult"), PAGES["SEC Consult"])
    assert ps and all(p.url.startswith("https://sec-consult.com/career/detail/") for p in ps)
    assert any("Vienna" in p.location for p in ps)


def test_hash_is_stable_and_ignores_timestamps():
    p = PAGES["NSIDE Attack Logic"]
    html = page_html("NSIDE Attack Logic")
    a = parse_hash(html, p)[0]
    b = parse_hash(html.replace("2026-03-09T12:25:58+01:00", "2027-01-01T00:00:00+01:00"), p)[0]
    c = parse_hash(html.replace("leider alle besetzt", "offen: Pentester (m/w/d)"), p)[0]
    assert a.external_id == b.external_id != c.external_id
    assert a.raw["page_changed"] and a.countries == {"DE"}


def test_page_changed_notice_passes_title_filter():
    from jobradar.model import SourceResult
    p = parse_hash(page_html("NSIDE Attack Logic"), PAGES["NSIDE Attack Logic"])
    kept, _ = radar.select([SourceResult("careers_page", postings=p)], include_outside=False)
    assert len(kept) == 1 and kept[0].company_canonical == "NSIDE Attack Logic"


def test_missing_anchor_is_an_error_not_silence():
    with pytest.raises(ValueError, match="layout changed"):
        parse_selector("<html><body><p>redesigned</p></body></html>", PAGES["MDSec"])


def test_json_and_rss_feeds():
    page = {"company": "X", "url": "https://x.example/careers", "mode": "feed", "items_path": "data.jobs",
            "fields": {"title": "name", "url": "link"}, "default_location": "London, UK"}
    js = '{"data": {"jobs": [{"id": 1, "name": "AppSec Engineer", "link": "/j/1", "location": "Dublin"}]}}'
    [p] = PARSERS["feed"](js, page)
    assert (p.title, p.url, p.countries, p.external_id) == ("AppSec Engineer", "https://x.example/j/1", {"IE"}, "1")
    rss = ('<?xml version="1.0"?><rss><channel><item><title>Pentester</title>'
           '<link>https://x.example/j/2</link><guid>g2</guid></item></channel></rss>')
    [p] = PARSERS["feed"](rss, page)
    assert (p.title, p.url, p.external_id, p.countries) == ("Pentester", "https://x.example/j/2", "g2", {"GB"})


def test_feed_rejects_entity_expansion():
    bomb = ('<?xml version="1.0"?><!DOCTYPE r [<!ENTITY a "aaaa"><!ENTITY b "&a;&a;&a;&a;">]>'
            '<rss><channel><item><title>&b;</title></item></channel></rss>')
    with pytest.raises(Exception):
        PARSERS["feed"](bomb, {"company": "X", "url": "https://x.example/"})


@respx.mock
def test_source_isolates_pages_and_respects_robots(tmp_path):
    pages = [
        {"company": "MDSec", **{k: v for k, v in PAGES["MDSec"].items() if k != "company"}},
        {"company": "Blocked", "url": "https://blocked.example/jobs", "mode": "hash"},
        {"company": "Down", "url": "https://down.example/jobs", "mode": "hash"},
        {"company": "NeedsJS", "url": "https://js.example/jobs", "mode": "hash", "render": "js"},
    ]
    f = tmp_path / "pages.yaml"
    f.write_text(yaml.safe_dump(pages), encoding="utf-8")
    respx.get("https://www.mdsec.co.uk/robots.txt").mock(return_value=httpx.Response(403))
    respx.get("https://www.mdsec.co.uk/careers/").mock(return_value=httpx.Response(200, text=page_html("MDSec")))
    respx.get("https://blocked.example/robots.txt").mock(
        return_value=httpx.Response(200, text="User-agent: *\nDisallow: /jobs"))
    respx.get("https://down.example/robots.txt").mock(return_value=httpx.Response(404))
    respx.get("https://down.example/jobs").mock(return_value=httpx.Response(500))
    respx.get("https://js.example/robots.txt").mock(return_value=httpx.Response(404))

    src = CareersPageSource({"pages_file": str(f)})
    src.pages_file = f
    res = asyncio.run(src.fetch())
    by = {u.label.split(":")[0]: u for u in res.units}  # units are keyed by URL, labelled "Company: url"
    assert all(u.key.startswith("https://") for u in res.units)
    assert by["MDSec"].ok and by["MDSec"].raw_count == 2
    assert not by["Blocked"].ok and "robots.txt" in by["Blocked"].error
    assert not by["Down"].ok and "500" in by["Down"].error
    assert not by["NeedsJS"].ok and "Playwright" in by["NeedsJS"].error
    assert len(res.postings) == 2


def test_robots_rules_follow_rfc_9309():
    from jobradar.sources.careers_page import robots_rules
    assert robots_rules(404, "") is True          # no robots.txt: no rules
    assert robots_rules(503, "") is False         # server error: assume disallowed
    rp = robots_rules(200, "User-agent: *\nDisallow: /jobs")
    assert not rp.can_fetch("x", "https://a.example/jobs/1") and rp.can_fetch("x", "https://a.example/")


def test_json_feed_with_nested_fields_and_url_template():
    import json
    from jobradar.sources.careers_page import parse_feed
    body = json.dumps({"jobs": [{"data": {"title": "Product Security Engineer", "full_location": "United Kingdom",
                                          "req_id": "5773"}}]})
    page = {"company": "GitHub (Microsoft)", "url": "https://careers.example/jobs", "items_path": "jobs",
            "fields": {"title": "data.title", "location": "data.full_location", "id": "data.req_id"},
            "url_template": "https://careers.example/jobs/{id}"}
    [p] = parse_feed(body, page)
    assert (p.title, p.location, p.url, p.external_id) == (
        "Product Security Engineer", "United Kingdom", "https://careers.example/jobs/5773", "5773")
