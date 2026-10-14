"""Hacker News 'Who is hiring?' source against a small recorded-shape response."""
import asyncio

import httpx
import respx

from jobradar.sources import hn_hiring

STORY = "100"
THREADS = {"hits": [
    {"objectID": STORY, "title": "Ask HN: Who is hiring? (November 2026)"},
    {"objectID": "99", "title": "Ask HN: Who wants to be hired? (November 2026)"},
]}


def comment(oid, text, parent=STORY):
    return {"objectID": oid, "parent_id": int(parent), "comment_text": text, "created_at_i": 1794400000}


COMMENTS = {"nbPages": 1, "hits": [
    comment("1", "Acme Ltd | Senior Application Security Engineer | London, UK | REMOTE<p>We build things. Apply at x.example"),
    comment("2", "Beta GmbH | Backend Engineer | Berlin<p>Also looking for someone to own our security reviews"),
    comment("3", "Hey HN! We&#x27;re building a security thing, details inside"),
    comment("4", "Gamma | Chef | Paris"),
    comment("5", "reply to somebody", parent="1"),
]}


@respx.mock
def test_parse_and_fetch():
    respx.get(hn_hiring.API, params__contains={"tags": "story,author_whoishiring"}).mock(
        return_value=httpx.Response(200, json=THREADS))
    respx.get(hn_hiring.API, params__contains={"tags": f"comment,story_{STORY}"}).mock(
        return_value=httpx.Response(200, json=COMMENTS))
    res = asyncio.run(hn_hiring.HNHiringSource({"threads": 1}).fetch())
    assert res.ok and res.units[0].raw_count == 4          # the reply (parent 1) is not top level
    by = {p.external_id: p for p in res.postings}
    assert set(by) == {"1", "2"}                           # prose post and non-security post are dropped
    a = by["1"]
    assert a.company == "Acme Ltd" and a.title == "Senior Application Security Engineer"
    assert "GB" in a.countries and a.url == "https://news.ycombinator.com/item?id=1"
    assert by["2"].title.lower().startswith("also looking for someone to own our security")   # header names no query: body line


@respx.mock
def test_no_thread_is_a_failure():
    respx.get(hn_hiring.API).mock(return_value=httpx.Response(200, json={"hits": []}))
    res = asyncio.run(hn_hiring.HNHiringSource({}).fetch())
    assert not res.ok and "no 'Who is hiring?'" in res.error
