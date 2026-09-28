"""Company careers pages that have no supported ATS (careers_pages.yaml in profile/).

Three modes per page:
  selector  CSS selectors pick job items, title, link and (optionally) location.
  feed      RSS/Atom or JSON feed of jobs.
  hash      Can't parse the page into jobs: hash the listing section and report
            "careers page changed" when the hash changes.

Pages are fetched with plain httpx (one request per page per run, identifying
User-Agent, robots.txt respected). `render: js` pages need Playwright, which is
an optional extra (requirements-browser.txt) and not installed in GitHub Actions;
those pages are reported as errors there instead of being silently skipped.

Hash mode needs no extra state: the hash is the posting's ID, so the normal
seen-diff reports it exactly once per change.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import re
from urllib.parse import urljoin, urlsplit
from urllib.robotparser import RobotFileParser

import httpx
import yaml
from selectolax.parser import HTMLParser

from jobradar.common import ROOT, countries_for
from jobradar.paths import profile_path
from jobradar.model import Posting, SourceResult, UnitStatus
from jobradar.sources import _http, register

PAGE_CHANGED = "page_changed"


def clean(text: str) -> str:
    """Collapse whitespace and drop soft hyphens (SySS titles are full of U+00AD)."""
    return " ".join((text or "").replace("\xad", "").split())


def parse_selector(html: str, page: dict) -> list[Posting]:
    tree = HTMLParser(html)
    # "No openings" and "selector broke after a redesign" both yield zero items. The
    # anchor is something that exists even when there are no jobs (the jobs section),
    # so a missing anchor is reported as an error instead of silence.
    if page.get("anchor") and tree.css_first(page["anchor"]) is None:
        raise ValueError(f"page layout changed: anchor {page['anchor']!r} not found")
    out, seen = [], set()
    for item in tree.css(page["item"]):
        tnode = item.css_first(page["title"]) if page.get("title") else item
        title = clean(tnode.text()) if tnode else ""
        if page.get("link") == "#id":  # one-page listings: each job is a section with an id
            href = f"#{item.attributes.get('id')}" if item.attributes.get("id") else ""
        else:
            lnode = item if item.tag == "a" else item.css_first(page.get("link", "a"))
            href = (lnode.attributes.get("href") if lnode else None) or ""
        url = urljoin(page["url"], href) if href else page["url"]
        lcss = page.get("location")
        loc_node = item.css(lcss) if lcss else []
        location = clean(", ".join(n.text() for n in loc_node)) or page.get("default_location", "")
        if not title or (title, url) in seen:
            continue
        seen.add((title, url))
        # several jobs can share one link (MDSec: all roles -> the same Indeed page)
        out.append(_posting(page, title, location, url, external_id=f"{url}|{title}"))
    return out


def parse_feed(body: str, page: dict) -> list[Posting]:
    fields = page.get("fields") or {}
    out = []
    if body.lstrip().startswith(("{", "[")):
        data = json.loads(body)
        for key in (page.get("items_path") or "").split("."):
            if key:
                data = data[key]
        for it in data:
            title = clean(str(it.get(fields.get("title", "title"), "")))
            url = urljoin(page["url"], str(it.get(fields.get("url", "url"), "")))
            loc = clean(str(it.get(fields.get("location", "location"), "") or page.get("default_location", "")))
            if title:
                out.append(_posting(page, title, loc, url, external_id=str(it.get(fields.get("id", "id")) or url)))
        return out
    from defusedxml import ElementTree  # untrusted XML: block entity-expansion attacks
    root = ElementTree.fromstring(body.encode())
    for el in root.iter():
        tag = el.tag.rsplit("}", 1)[-1]
        if tag not in ("item", "entry"):
            continue
        kids = {c.tag.rsplit("}", 1)[-1]: c for c in el}
        title = clean(kids["title"].text if "title" in kids else "")
        link = kids.get("link")
        url = (link.get("href") or link.text or "") if link is not None else ""
        guid = kids.get("guid") if "guid" in kids else kids.get("id")
        if title:
            out.append(_posting(page, title, page.get("default_location", ""), urljoin(page["url"], url.strip()),
                                external_id=(guid.text if guid is not None else None) or url or title))
    return out


def parse_hash(html: str, page: dict) -> list[Posting]:
    tree = HTMLParser(html)
    for sel in ("script", "style", "noscript", "svg"):
        for n in tree.css(sel):
            n.decompose()
    node = tree.css_first(page.get("container", "body"))
    if node is None:
        raise ValueError(f"container {page.get('container')!r} not found")
    text = clean(node.text(separator=" "))
    for pattern in page.get("ignore_patterns") or []:  # e.g. dates, counters that change daily
        text = re.sub(pattern, "", text)
    digest = hashlib.sha256(text.encode()).hexdigest()[:16]
    p = _posting(page, f"Careers page changed: {page['company']}", page.get("default_location", ""),
                 page["url"], external_id=f"hash:{digest}")
    p.raw[PAGE_CHANGED] = True
    return [p]


def _posting(page, title, location, url, external_id) -> Posting:
    countries = countries_for(None, location) or countries_for(None, page.get("default_location", ""))
    return Posting(source="careers_page", company=page["company"], title=title, location=location,
                   countries=frozenset(countries), url=url, external_id=external_id,
                   company_hint=(page["company"],))


PARSERS = {"selector": parse_selector, "feed": parse_feed, "hash": parse_hash}


def robots_rules(status: int, text: str) -> RobotFileParser | bool:
    """RFC 9309: 200 = follow the rules; 4xx = no rules (allowed); anything else (5xx,
    redirect loops) = assume everything is disallowed until the site answers properly."""
    if status == 200:
        rp = RobotFileParser()
        rp.parse(text.splitlines())
        return rp
    return 400 <= status < 500


async def render_js(url: str) -> str:
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        raise RuntimeError("render: js needs Playwright (pip install -r requirements-browser.txt; "
                           "playwright install chromium) — not available in GitHub Actions by design")
    async with async_playwright() as pw:
        browser = await pw.chromium.launch()
        try:
            page = await browser.new_page(user_agent=_http.USER_AGENT)
            await page.goto(url, wait_until="networkidle", timeout=45_000)
            return await page.content()
        finally:
            await browser.close()


class CareersPageSource:
    name = "careers_page"

    def __init__(self, cfg: dict):
        self.timeout = float(cfg.get("timeout_seconds", 300))
        self.pages_file = ROOT / cfg["pages_file"] if cfg.get("pages_file") else profile_path("careers_pages.yaml")
        self.respect_robots = cfg.get("respect_robots", True)
        self._robots: dict[str, RobotFileParser | bool] = {}  # parser, True = no rules, False = deny

    def load_pages(self) -> list[dict]:
        pages = yaml.safe_load(self.pages_file.read_text(encoding="utf-8")) or []
        return [p for p in pages if p.get("enabled", True)]

    async def allowed(self, c: httpx.AsyncClient, url: str) -> bool:
        if not self.respect_robots:
            return True
        host = "{0.scheme}://{0.netloc}".format(urlsplit(url))
        if host not in self._robots:
            try:
                r = await c.get(f"{host}/robots.txt", timeout=15)
                self._robots[host] = robots_rules(r.status_code, r.text)
            except httpx.HTTPError:
                self._robots[host] = False  # RFC 9309: unreachable robots.txt = assume disallowed
        rp = self._robots[host]
        return rp if isinstance(rp, bool) else rp.can_fetch(_http.USER_AGENT, url)

    async def fetch_page(self, c, page: dict) -> list[Posting]:
        if not await self.allowed(c, page["url"]):
            raise PermissionError("disallowed by robots.txt")
        mode = page.get("mode", "selector")
        if page.get("render") == "js":
            body = await render_js(page["url"])
        else:
            url = page.get("feed_url") if mode == "feed" and page.get("feed_url") else page["url"]
            accept = {"Accept": "application/json, application/rss+xml, application/atom+xml, */*"} if mode == "feed" \
                else {"Accept": "text/html,application/xhtml+xml"}
            body = (await _http.request(c, "GET", url, headers=accept)).text
        return PARSERS[mode](body, page)

    async def fetch(self) -> SourceResult:
        out = SourceResult(self.name)
        async with _http.client(timeout=45.0) as c:
            for page in self.load_pages():
                label = f"{page['company']}: {page['url']}"
                try:
                    postings = await asyncio.wait_for(self.fetch_page(c, page), timeout=90)
                    out.postings += postings
                    # a hash page always yields 1; selector/feed pages may legitimately list no jobs
                    # keyed by URL: two pages for one company must not share a health record
                    out.units.append(UnitStatus(page["url"], ok=True, raw_count=len(postings), label=label,
                                                track_empty=bool(page.get("expect_jobs", False))))
                except Exception as e:
                    msg = "timeout after 90s" if isinstance(e, asyncio.TimeoutError) else f"{type(e).__name__}: {str(e)[:150]}"
                    out.units.append(UnitStatus(page["url"], ok=False, error=msg, label=label))
        return out


register("careers_page")(CareersPageSource)
