import json

from jobradar.bamboohr_json import parse_json_widget
from jobradar import common  # noqa: F401  (installs the patch)
from ats_scrapers.scrapers.bamboohr import BambooHRScraper

WIDGET = json.dumps({"departments": [
    {"id": 1, "label": "Security", "positions": [
        {"id": 7, "name": "Security Engineer", "url": "https://x.bamboohr.com/careers/7", "location": "Dublin"},
        {"id": 7, "name": "Duplicate", "url": "u", "location": "x"}]},
    {"id": "", "label": "", "positions": [{"id": 9, "name": "GRC Consultant", "location": None}]}]})


def test_json_widget_parsed():
    jobs = parse_json_widget("x", WIDGET)
    assert [(j.ats_id, j.title, j.department, j.location) for j in jobs] == [
        ("7", "Security Engineer", "Security", "Dublin"), ("9", "GRC Consultant", None, None)]
    assert str(jobs[1].url) == "https://x.bamboohr.com/careers/9"


def test_scraper_uses_json_and_keeps_html_path():
    s = BambooHRScraper("x")
    assert len(s._parse_widget(WIDGET)) == 2
    assert s._parse_widget("<ul></ul>") == []
