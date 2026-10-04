"""LinkedIn post discovery bookkeeping: query rotation, the people list, lead status, and add-role."""
import csv
import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import board_sync as bs  # noqa: E402
import post_leads as pl  # noqa: E402


def write_matches(rows):
    pl.MATCHES.write_text("ref,company,title,location,countries,url,source,posted,tier\n" + "\n".join(rows) + "\n", encoding="utf-8")


def write_scores(rows):
    pl.SCORES.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")


def test_queries_rotate_and_do_not_repeat_until_the_grid_is_used():
    s = pl.settings()
    grid = len(s["titles"]) * len(s["places"])
    seen = []
    for _ in range(grid // 8):
        seen += pl.next_queries(8, now="2026-10-01T00:00:00+00:00")
    assert len(set(seen)) == len(seen)                   # nothing ran twice yet
    first = pl.next_queries(8, now="2026-10-09T00:00:00+00:00")   # a later pass: same pairs, next phrase
    assert not set(first) & set(seen)
    titles_in_first_session = {t for t in s["titles"] if any(t in q for q in seen[:8])}
    assert len(titles_in_first_session) > 1              # one session spans several titles


def test_grid_queries_use_the_title_as_written_and_exclude_contract_words():
    q = pl.next_queries(1, now="2026-10-01T00:00:00+00:00")[0]
    assert q.startswith('"we\'re hiring" ')
    assert q.endswith("NOT (contract OR contractor OR freelance)")


def test_company_queries_come_from_roles_the_user_scored_apply_or_maybe():
    write_scores([{"company": "Amazon", "recommendation": "apply", "fit_score": 85},
                  {"company": "Amazon UK", "recommendation": "apply", "fit_score": 70},
                  {"company": "Solaris", "recommendation": "maybe", "fit_score": 58},
                  {"company": "Nope Ltd", "recommendation": "skip", "fit_score": 90}])
    assert pl.fit_companies() == ["Amazon", "Solaris"]          # "Amazon UK" is the same employer
    out = pl.next_queries(4, now="2026-10-01T00:00:00+00:00")
    assert out[:2] == ['Amazon "we\'re hiring" security', 'Solaris "we\'re hiring" security'] and len(out) == 4
    out2 = pl.next_queries(3, now="2026-10-02T00:00:00+00:00")
    assert out2[0] == 'Amazon "we\'re hiring" security'           # least recently run company comes first


def test_companies_with_a_contact_are_searched_first_even_if_searched_recently(monkeypatch):
    write_scores([{"company": "Amazon", "recommendation": "apply", "fit_score": 85},
                  {"company": "Solaris", "recommendation": "maybe", "fit_score": 58},
                  {"company": "Nope Ltd", "recommendation": "skip", "fit_score": 90}])
    monkeypatch.setattr(pl, "network_companies", lambda: ["Solaris", "Palantir"])
    monkeypatch.setattr(pl, "_has_contact", lambda c: c in ("Solaris", "Palantir"))
    assert pl.ranked_companies() == [(1, "Solaris"), (1, "Palantir"), (2, "Amazon")]   # a contact makes any employer a fit
    pl.next_queries(1, now="2026-10-01T00:00:00+00:00")                 # Solaris searched
    out = pl.next_queries(1, now="2026-10-02T00:00:00+00:00")
    assert out[0].startswith("Palantir")                                  # still first: tier beats "least recently run"


def test_company_lines_use_the_author_company_filter_once_the_id_is_known(tmp_path):
    ids = tmp_path / "ids.json"
    url, hint = pl.search_url('Meta "we\'re hiring" security', ids)
    assert "authorCompany" not in url and "company-id" in hint            # no id yet: the old keyword search, plus how to get the id
    assert "recorded" in pl.set_company_id("Meta", "10667", ids)
    url, hint = pl.search_url('Meta "we\'re hiring" security', ids)
    assert url.endswith("&authorCompany=%5B%2210667%22%5D") and "keywords=hiring%20security&" in url and hint == ""
    url, _ = pl.search_url('"we\'re hiring" "security consultant" Amsterdam', ids)    # keyword grid lines are untouched
    assert "authorCompany" not in url
    try:
        pl.set_company_id("Meta", "not-a-number", ids)
        raise AssertionError("a non-numeric id must be refused")
    except SystemExit:
        pass


def test_people_are_read_longest_ago_first_and_marked_read():
    pl.add_person("Ana", "https://www.linkedin.com/in/ana/?trk=x", "Acme", "Security recruiter", "security")
    pl.add_person("Bo", "https://www.linkedin.com/in/bo", "Acme")
    assert pl.mark_read("https://www.linkedin.com/in/ana") == "marked read"
    assert [p["name"] for p in pl.next_people(2)] == ["Bo", "Ana"]
    assert pl.mark_read("https://www.linkedin.com/in/nobody").startswith("unknown")


def test_lead_status_known_stale_job_board_new():
    write_matches(["r" * 16 + ",Acme Ltd,Product Security Engineer,London,GB,u,ats,2026-09-20,1"])
    today = date(2026, 10, 1)
    msg, rec = pl.log_lead("https://x/p/1?utm=a", "Ana", "Acme", "Product Security Engineer (m/f)", today=today)
    assert rec["status"] == "known" and rec["ref"] == "r" * 16
    assert pl.log_lead("https://x/p/1", "Ana", "Acme", "Product Security Engineer", today=today)[1] == {}   # same post, once
    assert pl.log_lead("https://x/p/2", "Bo", "Globex", "AppSec Engineer", posted="2026-07-01", today=today)[1]["status"] == "stale"
    assert pl.log_lead("https://x/p/3", "Bo", "Globex", "AppSec Engineer", posted="2026-07-01", open_="yes", today=today)[1]["status"] == "new"
    assert pl.log_lead("https://x/p/4", "bot", "Initech", "Security Engineer", kind="job_board", today=today)[1]["status"] == "job_board"


def test_similar_title_at_another_company_is_not_known():
    write_matches(["r" * 16 + ",Acme Ltd,Product Security Engineer,London,GB,u,ats,,1"])
    assert pl.known_roles("Globex", "Product Security Engineer") == []
    assert pl.known_roles("Acme", "Sales Manager") == []


def test_add_role_writes_row_with_poster_and_queues_a_card(monkeypatch):
    queued = []
    monkeypatch.setattr(bs, "promote", lambda refs, dry_run=False: queued.append(refs) or "queued")
    _, rec = pl.log_lead("https://x/p/9", "Ana", "Globex", "Application Security Engineer", "Amsterdam", "2026-09-30",
                         author_url="https://www.linkedin.com/in/ana", today=date(2026, 10, 1))
    out = pl.add_role(rec["id"], "NL")
    row = list(csv.DictReader(pl.MATCHES.open(encoding="utf-8")))[0]
    assert row["source"] == "linkedin_post" and row["poster"] == "Ana" and row["countries"] == "NL"
    assert queued == [[row["ref"]]] and row["ref"] in out
    from jobradar.board import row_payload
    assert "Posted by: [Ana](https://www.linkedin.com/in/ana)" in row_payload(row)["body"]
    assert "not added" in pl.add_role(rec["id"], "NL")    # now status added: cannot be added twice
    assert pl.stats()["added"] == 1


def test_closest_title_wins_when_an_employer_has_several_similar_roles():
    write_matches(["a" * 16 + ",Solaris,Cyber Security Engineer - Vulnerability Management,Berlin,DE,u,ats,,1",
                   "b" * 16 + ",Solaris,Cyber Security Staff Engineer - Application Security,Berlin,DE,u,ats,,1"])
    assert pl.known_roles("Solaris", "Cyber Security Staff Engineer - Application Security")[0]["ref"] == "b" * 16


def test_company_rotation_survives_a_name_change_and_picks_up_new_employers():
    write_scores([{"company": "Amazon", "recommendation": "apply", "fit_score": 85},
                  {"company": "Solaris", "recommendation": "maybe", "fit_score": 58}])
    pl.next_queries(2, now="2026-10-01T00:00:00+00:00")   # both searched once
    write_scores([{"company": "Amazon UK", "recommendation": "apply", "fit_score": 90},   # same employer, new display name
                  {"company": "Solaris", "recommendation": "maybe", "fit_score": 58},
                  {"company": "Monzo", "recommendation": "apply", "fit_score": 70}])               # new employer
    out = pl.next_queries(3, now="2026-10-02T00:00:00+00:00")
    assert out[0].startswith("Monzo ")                       # never searched: first
    log = json.loads(pl.QUERIES.read_text(encoding="utf-8"))
    assert sorted(k for k in log if k.startswith("company|")) == ["company|amazon", "company|monzo", "company|solaris"]   # one entry per employer
    assert log["company|monzo"]["runs"] == 1 and log["company|amazon"]["runs"] in (1, 2)
    out2 = pl.next_queries(3, now="2026-10-03T00:00:00+00:00")
    assert sum(q.startswith("Amazon") for q in out + out2) == 2    # Amazon: once before the rename, once after, never twice in a row


def test_company_extra_is_searched_first_and_each_employer_once(monkeypatch):
    write_scores([{"company": "Amazon", "recommendation": "apply", "fit_score": 85}])
    real = pl.settings()
    monkeypatch.setattr(pl, "settings", lambda: {**real, "company_extra": ["Monzo", "Amazon UK"]})   # "Amazon UK" is the scored Amazon: not twice
    assert pl.search_companies() == ["Monzo", "Amazon UK"]
    assert pl.next_queries(2, now="2026-10-01T00:00:00+00:00")[0].startswith("Monzo ")


def test_high_fit_targets_follow_extras_and_scored_employers(monkeypatch):
    pl.TARGETS.write_text("Company\tEuropean City / Offices\tFit\nNCC Group\tManchester\tHigh\nSomeCo\tLondon\tMedium\n"
                          "Amazon UK\tLondon\thigh\nWatchCo\tParis\tWatch\n", encoding="utf-8")
    write_scores([{"company": "Amazon", "recommendation": "apply", "fit_score": 85}])
    assert pl.fit_targets("High") == ["NCC Group", "Amazon UK"]                  # case-insensitive, file order
    assert pl.search_companies() == ["Amazon", "NCC Group"]                      # scored first, High targets next, Amazon once
    assert pl.fit_targets("") == []
    pl.TARGETS.write_text("Company\tEuropean City / Offices\nNCC Group\tManchester\n", encoding="utf-8")   # an older file without Fit
    assert pl.fit_targets("High") == []
