"""state/dropped_alerts.csv: the alert-email listings the radar's filters drop, with every reason (radar.select, write_dropped_log)."""
import csv
from datetime import datetime, timedelta

import pytest

import radar
from jobradar.model import Posting, SourceResult


def post(source, company, title, location, countries):
    return Posting(source=source, company=company, title=title, location=location, countries=frozenset(countries),
                   url=f"https://example.test/{company}/{title}".replace(" ", "-"))


@pytest.fixture(autouse=True)
def _clean(monkeypatch):
    monkeypatch.setattr(radar, "DROPPED_ROWS", [])
    monkeypatch.setattr(radar, "LOG_DROPS", False)


def run(results):
    radar.LOG_DROPS = True
    try:
        return radar.select(results, include_outside=False)
    finally:
        radar.LOG_DROPS = False


def test_alert_drops_logged_with_every_reason():
    alerts = SourceResult("alert_email", postings=[
        post("alert_email", "Nobody Ltd", "Application Security Engineer", "London", {"GB"}),   # employer not on the list
        post("alert_email", "Nobody Ltd", "Marketing Manager", "London", {"GB"}),               # title and employer
        post("alert_email", "Nobody Ltd", "Application Security Engineer", "Mars", set()),      # location not recognised
    ])
    run([alerts])
    by_title = {(r["title"], r["location"]): r["reasons"].split(",") for r in radar.DROPPED_ROWS}
    assert by_title[("Application Security Engineer", "London")] == ["company"]
    assert set(by_title[("Marketing Manager", "London")]) == {"title", "company"}
    assert "country" in by_title[("Application Security Engineer", "Mars")]


def test_later_filters_are_logged_when_an_earlier_one_dropped_the_listing(monkeypatch):
    monkeypatch.setitem(radar.CONFIG, "max_age_days", 30)
    old_contract = post("alert_email", "Nobody Ltd", "Marketing Manager (Contract)", "London", {"GB"})
    old_contract.posted_at = datetime.now() - timedelta(days=90)
    run([SourceResult("alert_email", postings=[old_contract])])
    assert set(radar.DROPPED_ROWS[0]["reasons"].split(",")) == {"title", "company", "employment", "old"}


def test_other_sources_and_default_off_are_not_logged():
    ats = SourceResult("ats", postings=[post("ats", "Nobody Ltd", "Marketing Manager", "London", {"GB"})])
    run([ats])
    assert radar.DROPPED_ROWS == []
    alerts = SourceResult("alert_email", postings=[post("alert_email", "Nobody Ltd", "Marketing Manager", "London", {"GB"})])
    radar.select([alerts], include_outside=False)  # LOG_DROPS is off, as for jobradar/intake.py
    assert radar.DROPPED_ROWS == []


def test_write_merges_keeps_first_seen_and_expires(tmp_path):
    radar.DROPPED_ROWS.append({"company": "Nobody Ltd", "title": "Marketing Manager", "location": "London",
                               "reasons": "title,company", "source": "alert_email", "url": "https://example.test/a"})
    assert radar.write_dropped_log("2026-10-20") == 1
    radar.DROPPED_ROWS[:] = [{"company": "nobody ltd", "title": "marketing manager", "location": "london",
                              "reasons": "title", "source": "alert_email", "url": ""},
                             {"company": "Other", "title": "Pentester", "location": "Cork", "reasons": "company",
                              "source": "alert_email", "url": "https://example.test/b"}]
    assert radar.write_dropped_log("2026-10-27") == 2
    rows = {r["company"].lower(): r for r in csv.DictReader(open(radar.STATE / "dropped_alerts.csv", encoding="utf-8"))}
    assert rows["nobody ltd"]["first_seen"] == "2026-10-20" and rows["nobody ltd"]["last_seen"] == "2026-10-27"
    assert rows["nobody ltd"]["url"] == "https://example.test/a"  # an empty new url never wipes the old one
    radar.DROPPED_ROWS.clear()
    assert radar.write_dropped_log("2026-12-30") == 0  # everything is older than 45 days
