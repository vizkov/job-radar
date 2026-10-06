"""Job-alert email parser. Fixtures are SYNTHETIC (see fixtures/alert_email/make_fixtures.py)
until real exported alerts are added."""
import asyncio
import json
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
                      "indeed:rejected": "1 of 2 indeed emails failed DKIM"}
    foreign = next(u for u in res.units if u.key == "foreign")
    assert foreign.ok and foreign.raw_count == 1  # a recruiter's mail is not a fault


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


def test_empty_mailbox_is_explained_not_silent(tmp_path):
    (tmp_path / "_status.json").write_text(json.dumps({"ok": True, "fetched": 0, "mailbox": "[Gmail]/All Mail",
        "providers": {"linkedin": {"from_domain": 0, "alert_senders": 0, "other_senders": {}},
                      "indeed": {"from_domain": 0, "alert_senders": 0, "other_senders": {}}}}))
    res = asyncio.run(AlertEmailSource({"eml_dir": str(tmp_path), "providers": ["linkedin", "indeed"]}).fetch())
    unit = next(u for u in res.units if u.key == "mailbox:none")
    assert not unit.ok and "no emails at all from linkedin, indeed" in unit.error and "All Mail" in unit.error


def test_changed_alert_sender_is_named(tmp_path):
    (tmp_path / "_status.json").write_text(json.dumps({"ok": True, "fetched": 0, "mailbox": "INBOX",
        "providers": {"linkedin": {"from_domain": 4, "alert_senders": 0,
                                   "other_senders": {"jobs-alerts@linkedin.com": 4}}}}))
    res = asyncio.run(AlertEmailSource({"eml_dir": str(tmp_path), "providers": ["linkedin"]}).fetch())
    unit = next(u for u in res.units if u.key == "linkedin:senders")
    assert "jobs-alerts@linkedin.com" in unit.error and not any(u.key == "mailbox:none" for u in res.units)


def test_real_linkedin_layout_insight_lines_are_not_titles():
    """Sanitised from real alerts (2026-09): cards are title / company / location, then an optional
    blank line and an insight ("This company is actively hiring", "1 connection", "Fast growing")."""
    jobs = to_postings(load("real/linkedin_real_2026_09.eml"), LI)
    assert len(jobs) >= 8
    assert not any("actively hiring" in j.title.lower() or j.title.lower() in ("fast growing", "1 connection") for j in jobs)
    assert all(j.company and j.location and j.countries for j in jobs)
    by_title = {(j.title, j.company): j for j in jobs}
    assert by_title[("Cloud Security Specialist", "Alliander")].countries == frozenset({"NL"})
    assert by_title[("Infrastructure Security Engineer", "ElevenLabs")].location == "London"
    assert all(j.url.startswith("https://www.linkedin.com/jobs/view/") for j in jobs)


def test_real_indeed_layout_without_job_ids():
    """Sanitised from a real Indeed alert (2026-09): no job IDs, only engage.indeed.com tracking redirects.
    Jobs are keyed by title/company/location; boilerplate links and off-host links are not jobs."""
    msg = load("real/indeed_real_2026_09.eml")
    assert dkim_ok(msg, PROVIDERS["indeed"].dkim_domain)
    jobs = to_postings(msg, PROVIDERS["indeed"])
    assert [(j.title, j.company, j.location) for j in jobs] == [
        ("Junior Application Software Engineer", "One Big Circle", "Bristol"),
        ("Cyber Security Engineer", "Tai Tarian", "Neath"),
        ("Senior IT Security Analyst", "Synthomer (UK) Limited", "London")]
    assert all(j.url.startswith("https://engage.indeed.com/f/a/") for j in jobs)  # the spoofed host is dropped
    assert jobs[1].countries == frozenset({"GB"})  # unknown town: country from the alert's subject
    again = to_postings(load("real/indeed_real_2026_09.eml"), PROVIDERS["indeed"])
    assert [j.external_id for j in again] == [j.external_id for j in jobs]  # stable across emails
    assert len({j.external_id for j in jobs}) == 3


def test_account_mail_with_no_jobs_is_not_a_layout_change(tmp_path):
    (tmp_path / "_status.json").write_text(json.dumps({"ok": True, "fetched": 2, "mailbox": "INBOX", "providers": {}}))
    head = ("From: Indeed <donotreply@jobalert.indeed.com>\nTo: alerts@example.com\nSubject: {s}\n"
            "Authentication-Results: mx.google.com; dkim=pass header.i=@jobalert.indeed.com\n"
            "Content-Type: text/plain; charset=utf-8\n\n{b}\n")
    (tmp_path / "a.eml").write_text(head.format(s="Your job alert for pen tester jobs in United Kingdom is now active",
                                                b="Your job alert is active"), encoding="utf-8")
    (tmp_path / "b.eml").write_text(head.format(s="5 new pen tester jobs in United Kingdom",
                                                b="A layout the parser doesn't know"), encoding="utf-8")
    res = asyncio.run(AlertEmailSource({"eml_dir": str(tmp_path), "providers": ["indeed"]}).fetch())
    unit = next(u for u in res.units if u.key == "indeed:parse")
    assert unit.error.startswith("1 indeed emails yielded no jobs")  # only the real alert counts
    assert unit.error.endswith("5 new pen tester jobs in United Kingdom")  # names the subject to chase


def test_unknown_sender_naming_a_job_site_is_a_fault(tmp_path):
    (tmp_path / "_status.json").write_text(json.dumps({"ok": True, "fetched": 1, "mailbox": "INBOX", "providers": {}}))
    mail = ["From: Indeed <alerts@new-sender.indeed.example>", "Subject: 5 new jobs", "", "body", ""]
    (tmp_path / "a.eml").write_text(chr(10).join(mail), encoding="utf-8")
    res = asyncio.run(AlertEmailSource({"eml_dir": str(tmp_path), "providers": ["indeed"]}).fetch())
    unit = next(u for u in res.units if u.key == "foreign")
    assert not unit.ok and "naming a job site" in unit.error


def test_indeed_html_only_card_uses_redirect_and_shortest_title():
    """Real Indeed HTML (2026-09): the whole card sits inside the job link, then a title link with the same
    URL; company, rating and "- Location" are separate elements. Other links are the email's own."""
    job = "https://engage.indeed.com/f/a/AAAAjob1~~/AAR9hBA~/job1Token"
    html = (f'<a href="https://engage.indeed.com/f/a/AAAAbrowse~~/AAR9hBA~/browseTok">Browse jobs</a>'
            f'<table><tr><td><a href="{job}"><table><tr><td><a href="{job}">Cyber Security Engineer</a></td></tr>'
            '<tr><td>Tai Tarian</td><td>3.7</td><td>- Neath</td></tr><tr><td>£53,966 a year</td></tr>'
            '<tr><td>Just posted</td></tr></table></a></td></tr></table>'
            '<a href="https://evil.example/f/a/x~~/y~/z">Phishing Role</a>')
    jobs = parse_html(PROVIDERS["indeed"], html)
    assert [(j["title"], j["company"], j["location"], j["link"]) for j in jobs] == [
        ("Cyber Security Engineer", "Tai Tarian", "Neath", job)]


def test_indeed_match_mail_is_one_job_and_other_links_are_not_jobs():
    """Sanitised from a real Indeed job-match email (2026-09, donotreply@match.indeed.com): title / company / location, then
    'View job:'. The sender used to be ignored as unknown; profile, settings and feedback links are never jobs."""
    msg = load("real/indeed_match_2026_09.eml")
    assert PROVIDERS["indeed"] is not None and dkim_ok(msg, PROVIDERS["indeed"].dkim_domain)
    jobs = to_postings(msg, PROVIDERS["indeed"])
    assert [(j.title, j.company, j.location) for j in jobs] == [("Security Engineer II (Offensive)", "Flywire", "Bengaluru, Karnataka")]
    assert jobs[0].url == "https://cts.indeed.com/v3/FAKE_TOKEN_view-1/FAKE_SIG_a"
    assert jobs[0].countries == frozenset({"IN"})
    assert [j.external_id for j in to_postings(load("real/indeed_match_2026_09.eml"), INDEED)] == [jobs[0].external_id]


def test_indeed_match_mail_with_a_benefits_paragraph():
    """2026-10: Indeed put "Benefits:" and its bullets in a paragraph of their own between the card and "View job:",
    so the parser took the bullet as the card and found no job (health: 'indeed alert emails with no jobs')."""
    from jobradar.sources.alert_email import parse_match
    link = "https://cts.indeed.com/v3/FAKE_TOKEN_view-1/FAKE_SIG_a"
    body = ("Hi A,\n\nYour background could be a strong match for this role at Example Ltd. Apply now.\n\n"
            "Penetration Tester (India)\nExample Ltd\nIndia\nJob type: Full-time\n\n"
            f"Benefits:\n  - Health insurance\n\nView job: {link}\nApply now: {link}\n\n"
            "Keep your Indeed profile up to date\nA B\n")
    jobs = parse_match(body)
    assert [(j["title"], j["company"], j["location"], j["link"]) for j in jobs] == [
        ("Penetration Tester (India)", "Example Ltd", "India", link)]


def test_indeed_sign_in_code_mail_is_not_a_layout_change(tmp_path):
    (tmp_path / "_status.json").write_text(json.dumps({"ok": True, "fetched": 1, "mailbox": "INBOX", "providers": {}}))
    (tmp_path / "a.eml").write_text(
        "From: Indeed <login@indeed.com>\nTo: alerts@example.com\nSubject: Sign in to Indeed with code: 000000\n"
        "Authentication-Results: mx.google.com; dkim=pass header.i=@indeed.com\n"
        "Content-Type: text/plain; charset=utf-8\n\nYour code.\n")
    res = asyncio.run(AlertEmailSource({"eml_dir": str(tmp_path), "providers": ["indeed"]}).fetch())
    assert not [u for u in res.units if u.key.endswith(":parse") and not u.ok]


def test_clean_run_reports_parse_and_foreign_units_ok_so_old_streaks_reset(tmp_path):
    """A unit written only when it fails never resets: Indeed ':parse' sat at a 21-run streak after the parser was fixed."""
    from jobradar.health import update_health
    from jobradar.model import SourceResult
    (tmp_path / "_status.json").write_text(json.dumps({"ok": True, "fetched": 1, "mailbox": "INBOX", "providers": {}}))
    (tmp_path / "a.eml").write_bytes((FX / "real/indeed_match_2026_09.eml").read_bytes())
    res = asyncio.run(AlertEmailSource({"eml_dir": str(tmp_path), "providers": ["indeed"]}).fetch())
    keys = {u.key: u.ok for u in res.units}
    assert keys.get("indeed:parse") is True and keys.get("indeed:rejected") is True and keys.get("foreign") is True
    health = {"alert_email|indeed:parse": {"bad_streak": 21, "last_ok_count": 0},
              "alert_email|foreign": {"bad_streak": 5, "last_ok_count": 0}}
    update_health(health, [res])
    assert health["alert_email|indeed:parse"]["bad_streak"] == 0 and health["alert_email|foreign"]["bad_streak"] == 0
