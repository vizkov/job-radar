"""Job-alert email parser. Fixtures are SYNTHETIC (see fixtures/alert_email/make_fixtures.py)
until real exported alerts are added."""
import asyncio
import email
from email.policy import default
from pathlib import Path

import pytest

import radar
from jobradar.sources.alert_email import PROVIDERS, AlertEmailSource, dkim_ok, parse_html, parse_text, to_postings

FX = Path(__file__).parent / "fixtures" / "alert_email"
LI, INDEED, GD = PROVIDERS["linkedin"], PROVIDERS["indeed"], PROVIDERS["glassdoor"]


def load(name):
    return email.message_from_bytes((FX / name).read_bytes(), policy=default)


def test_linkedin_plain_text_cards():
    ps = to_postings(load("alert_text_and_html.eml"), LI)
    got = [(p.title, p.company, p.location, p.url) for p in ps]
    assert got == [
        ("Senior Application Security Engineer", "Deloitte", "London, England, United Kingdom",
         "https://www.linkedin.com/jobs/view/4012345678/"),
        ("Penetration Tester", "Pen Test Partners", "Buckingham, England, United Kingdom (Hybrid)",
         "https://www.linkedin.com/jobs/view/4012345679/"),
        ("Product Security Engineer", "Adyen", "Amsterdam, North Holland, Netherlands",
         "https://www.linkedin.com/jobs/view/4012345680/"),
    ]
    assert [p.countries for p in ps] == [{"GB"}, {"GB"}, {"NL"}]
    assert {p.source for p in ps} == {"linkedin_email"}


def test_linkedin_html_fallback_rebuilds_urls_from_job_id():
    ps = to_postings(load("alert_html_only.eml"), LI)
    assert [(p.title, p.company, p.url) for p in ps] == [
        ("Security Consultant", "MDSec", "https://www.linkedin.com/jobs/view/4099999999/"),
        ("Threat Modeling Lead", "Secura", "https://www.linkedin.com/jobs/view/4099999998/"),
    ]
    assert all("evil" not in p.url for p in ps)


def test_linkedin_html_and_text_agree():
    m = load("alert_text_and_html.eml")
    text = {j["id"]: (j["title"], j["company"]) for j in parse_text(LI, m.get_body(("plain",)).get_content())}
    html = {j["id"]: (j["title"], j["company"]) for j in parse_html(LI, m.get_body(("html",)).get_content())}
    assert html.items() <= text.items()


def test_indeed_job_keys_including_encoded_tracking_redirect():
    ps = to_postings(load("indeed_alert.eml"), INDEED)
    assert [(p.title, p.company, p.location, p.url) for p in ps] == [
        ("Application Security Engineer", "NCC Group", "Manchester", "https://www.indeed.com/viewjob?jk=0a1b2c3d4e5f6a7b"),
        ("Senior Security Consultant", "Bridewell", "London", "https://www.indeed.com/viewjob?jk=1122334455667788"),
    ]
    assert all(p.source == "indeed_email" for p in ps)


def test_glassdoor_listing_id():
    [p] = to_postings(load("glassdoor_alert.eml"), GD)
    assert (p.title, p.company, p.location) == ("Product Security Engineer", "Wise", "London")
    assert p.url == "https://www.glassdoor.com/partner/jobListing.htm?jobListingId=1009876543210"


def test_dkim_must_match_the_providers_domain():
    assert dkim_ok(load("alert_text_and_html.eml"), "linkedin.com")
    assert not dkim_ok(load("spoofed_no_dkim.eml"), "linkedin.com")
    assert dkim_ok(load("indeed_alert.eml"), "indeed.com")
    assert not dkim_ok(load("indeed_wrong_dkim.eml"), "indeed.com")  # signed by linkedin.com, claims Indeed
    assert not dkim_ok(load("alert_text_and_html.eml"), "indeed.com")


def test_source_rejects_spoofed_and_foreign_mail():
    src = AlertEmailSource({"eml_dir": str(FX), "providers": ["linkedin", "indeed", "glassdoor"]})
    res = asyncio.run(src.fetch())
    by_source = {}
    for p in res.postings:
        by_source.setdefault(p.source, set()).add(p.external_id)
    assert by_source == {
        "linkedin_email": {"4012345678", "4012345679", "4012345680", "4099999999", "4099999998"},
        "indeed_email": {"0a1b2c3d4e5f6a7b", "1122334455667788"},
        "glassdoor_email": {"1009876543210"},
    }
    assert not any(p.company == "Totally Real Bank" for p in res.postings)
    errors = {u.key: u.error for u in res.units if not u.ok}
    assert errors == {"linkedin:rejected": "1 of 3 linkedin emails failed DKIM",
                      "indeed:rejected": "1 of 2 indeed emails failed DKIM",
                      "foreign": "1 of 7 emails ignored (unknown sender)"}


def test_only_enabled_providers_are_read():
    res = asyncio.run(AlertEmailSource({"eml_dir": str(FX), "providers": ["glassdoor"]}).fetch())
    assert {p.source for p in res.postings} == {"glassdoor_email"}


def test_alert_postings_match_targets():
    res = asyncio.run(AlertEmailSource({"eml_dir": str(FX), "providers": ["linkedin", "indeed", "glassdoor"]}).fetch())
    kept, _ = radar.select([res], include_outside=False)
    assert {p.company_canonical for p in kept} >= {"Deloitte", "Pen Test Partners", "Adyen", "MDSec", "NCC Group",
                                                   "Bridewell", "Wise"}


def test_fetch_failure_is_surfaced(tmp_path):
    (tmp_path / "_status.json").write_text(
        '{"ok": false, "error": "RuntimeError: JOBALERT_IMAP_USER / JOBALERT_IMAP_PASSWORD not set"}')
    with pytest.raises(RuntimeError, match="mail fetch failed: .*JOBALERT_IMAP_USER"):
        asyncio.run(AlertEmailSource({"eml_dir": str(tmp_path)}).fetch())


def test_missing_mail_folder_says_what_to_run(tmp_path):
    with pytest.raises(RuntimeError, match="fetch_alert_emails.py"):
        asyncio.run(AlertEmailSource({"eml_dir": str(tmp_path / "nope")}).fetch())


def test_adapter_never_touches_imap():
    import jobradar.sources.alert_email as mod
    assert "imaplib" not in open(mod.__file__, encoding="utf-8").read()
