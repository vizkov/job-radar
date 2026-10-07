"""A role added by hand goes through the same filters and bookkeeping as the daily run (jobradar/intake.py)."""
import csv
from datetime import datetime, timedelta

import radar
from jobradar import intake
from jobradar.model import Posting


def posting(**kw):
    base = dict(source="ats", company="Globex", title="Application Security Engineer", location="Berlin", countries=frozenset({"DE"}),
                url="https://example.com/jobs/1", external_id="ats:1", posted_at=datetime.now() - timedelta(days=2),
                raw={"ats": "greenhouse", "slug": "globex", "board": "greenhouse:globex"})
    base.update(kw)
    return Posting(**base)


def test_every_filter_that_would_drop_the_role_is_named_and_nothing_is_written(monkeypatch):
    monkeypatch.setitem(radar.CONFIG, "max_age_days", 30)
    old = posting(countries=frozenset({"OUTSIDE-EUROPE"}), posted_at=datetime.now() - timedelta(days=600))
    r = intake.admit(old)
    assert r["status"] == "dropped" and {"country", "old"} <= set(r["reasons"])
    assert not (radar.DATA / "matches.csv").exists() and not (radar.STATE / "seen.json").exists()
    # overriding only one of them is not enough
    assert intake.admit(old, {"country"})["status"] == "dropped"


def test_override_adds_it_records_why_and_a_second_add_is_known(monkeypatch):
    monkeypatch.setitem(radar.CONFIG, "max_age_days", 30)
    old = posting(countries=frozenset({"OUTSIDE-EUROPE"}), posted_at=datetime.now() - timedelta(days=600))
    r = intake.admit(old, {"country", "old", "company"})
    assert r["status"] == "added" and r["overridden"]
    rows = list(csv.DictReader((radar.DATA / "matches.csv").open(encoding="utf-8")))
    assert rows[0]["ref"] == r["ref"] and rows[0]["origin"].startswith("manual-override:") and "old" in rows[0]["origin"]
    assert intake.admit(old, {"country", "old", "company"})["status"] == "known"


def test_dry_run_writes_nothing():
    r = intake.admit(posting(), {"company"}, dry_run=True)
    assert r["status"] == "added" and r["dry_run"]
    assert not (radar.DATA / "matches.csv").exists()


def test_job_links_are_parsed_for_the_three_supported_ats():
    assert intake.parse_job_url("https://job-boards.greenhouse.io/anthropic/jobs/5311463008?gh_src=LinkedIn") == ("greenhouse", "anthropic", "5311463008")
    assert intake.parse_job_url("https://jobs.lever.co/acme/123e4567-e89b-12d3-a456-426614174000")[:2] == ("lever", "acme")
    assert intake.parse_job_url("https://jobs.ashbyhq.com/acme/123e4567-e89b-12d3-a456-426614174000")[:2] == ("ashby", "acme")
    assert intake.parse_job_url("https://www.linkedin.com/jobs/view/1/") is None


def test_manual_fields_build_a_posting_the_same_filters_judge(monkeypatch):
    p = intake.manual_posting("https://example.com/j", "Globex", "Application Security Engineer", "London, UK", "2026-10-05")
    assert p.source == "manual" and p.countries == frozenset({"GB"}) and p.posted_at.date().isoformat() == "2026-10-05"
    assert intake.manual_posting("u", "G", "T", "Berlin", countries="de,nl").countries == frozenset({"DE", "NL"})
    old = intake.manual_posting("https://example.com/j2", "Globex", "Application Security Engineer", "London, UK", "2020-01-01")
    import radar
    monkeypatch.setitem(radar.CONFIG, "max_age_days", 30)
    r = intake.admit(old, {"company"})
    assert r["status"] == "dropped" and "old" in r["reasons"]
