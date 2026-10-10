"""BambooHR listing fix: the careers widget (`/jobs/embed2.php`) now answers with JSON, not the HTML list that
ats-scrapers 0.3.0 (the newest release, 2026-10) parses, so every tenant looked empty (Integrity360 went from 40 roles
to 0). This wraps the scraper's `_parse_widget` so JSON is read here and HTML still goes to the library.
Remove it once a release of ats-scrapers parses the JSON itself."""
from __future__ import annotations

import json
from datetime import UTC, datetime

from ats_scrapers.models import ATSType, Job
from ats_scrapers.scrapers.bamboohr import BambooHRScraper


def parse_json_widget(slug: str, text: str) -> list[Job]:
    data = json.loads(text)
    jobs, seen = [], set()
    for dept in data.get("departments") or []:
        for pos in dept.get("positions") or []:
            ats_id, title = str(pos.get("id") or ""), (pos.get("name") or "").strip()
            if not ats_id or not title or ats_id in seen:
                continue
            seen.add(ats_id)
            jobs.append(Job(url=pos.get("url") or f"https://{slug}.bamboohr.com/careers/{ats_id}", title=title,
                            company=slug, ats_type=ATSType.BAMBOOHR, ats_id=ats_id,
                            location=(pos.get("location") or None), department=(dept.get("label") or None),
                            posted_at=None, fetched_at=datetime.now(UTC)))
    return jobs


def install() -> None:
    original = BambooHRScraper._parse_widget
    if getattr(original, "_json_aware", False):
        return

    def _parse_widget(self, html: str):
        if html.lstrip().startswith("{"):
            return parse_json_widget(self.company_slug, html)
        return original(self, html)

    _parse_widget._json_aware = True
    BambooHRScraper._parse_widget = _parse_widget


install()
