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


def test_queries_rotate_and_do_not_repeat_until_the_grid_is_used():
    s = pl.settings()
    grid = len(s["titles"]) * len(s["places"])
    seen = []
    for _ in range(grid // 8):
        seen += pl.next_queries(8, now="2026-10-01T00:00:00+00:00")
    pairs = {(q.split('" "')[1].split('"')[0], q.rsplit('" ', 1)[1]) for q in seen}
    assert len(pairs) == len(seen)                       # nothing ran twice yet
    assert len({q.split('" "')[1].split('"')[0] for q in seen[:8]}) > 1   # one session spans several titles


def test_phrase_changes_when_a_pair_comes_round_again():
    pl.next_queries(100000, now="2026-10-01T00:00:00+00:00")
    first = pl.next_queries(1, now="2026-10-02T00:00:00+00:00")[0]
    assert first.startswith('"hiring"')                  # second phrase in the list


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
