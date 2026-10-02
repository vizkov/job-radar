import re
from collections import Counter
from datetime import datetime

import radar
from jobradar.board import MARKER_RE, enqueue, payload, role_ref, select_for_board
from jobradar.dedupe import group_postings
from jobradar.model import Posting, SourceResult
from jobradar.sponsors import SponsorTag


def G(title, company, countries, tier, canonical=True, url="https://x.example/1", sponsor=None, source="ats"):
    p = Posting(source=source, company=company, title=title, location="London", countries=frozenset(countries),
                url=url, company_canonical=company if canonical else None, posted_at=datetime(2026, 9, 20))
    [g] = group_postings([p])
    g.tags = {"tier": tier, "score": 9 if tier == 1 else 3, "reasons": ["title+4", "country+2"],
              "sponsor": sponsor or {}}
    return g


def test_payload_title_labels_and_marker():
    g = G("Senior Penetration Tester", "Bridewell", {"GB"}, 1, sponsor={"uk": SponsorTag("yes", "Bridewell Consulting Limited")})
    p = payload(g)
    assert p["title"] == "Bridewell — Senior Penetration Tester (GB)"
    assert p["labels"] == ["role"]
    assert MARKER_RE.search(p["body"]).group(1) == p["ref"] == role_ref(g.key)
    assert "UK sponsor: yes (Bridewell Consulting Limited)" in p["body"]
    assert "[Open the job posting](https://x.example/1)" in p["body"]


def test_payload_neutralizes_hostile_text():
    g = G("Pentester](https://evil.example)\n<img src=x>", "Acme\r\nInjected", {"NL"}, 2,
          url="javascript:alert(1)")
    p = payload(g)
    assert "\n" not in p["title"] and "\r" not in p["title"]
    assert not re.search(r"(?<!\\)\]\(https://evil", p["body"])  # the injected "](" is escaped
    assert "javascript:" not in p["body"]
    assert "<img" not in p["body"]


def test_long_titles_are_capped():
    assert len(payload(G("A" * 500, "X", {"GB"}, 1))["title"]) == 200


def test_ref_is_the_same_across_sources():
    a = G("Pentester", "X", {"GB"}, 1, source="ats")
    b = G("Pentester (m/w/d)", "X", {"GB"}, 1, source="linkedin_email", url="https://www.linkedin.com/jobs/view/1/")
    assert payload(a)["ref"] == payload(b)["ref"]


def test_selection_baseline_vs_daily():
    cfg = {"enabled": True, "tiers": [1, 2], "baseline_tiers": [1], "include_outside": False}
    groups = [G("A", "X", {"GB"}, 1), G("B", "X", {"GB"}, 2), G("C", "Y", {"GB"}, 1, canonical=False)]
    assert [g.best.title for g in select_for_board(groups, cfg, baseline=True)] == ["A"]
    assert [g.best.title for g in select_for_board(groups, cfg, baseline=False)] == ["A", "B"]
    assert select_for_board(groups, {**cfg, "enabled": False}, baseline=False) == []
    assert len(select_for_board(groups, {**cfg, "include_outside": True}, baseline=False)) == 3


def test_enqueue_dedupes_by_ref():
    p = payload(G("A", "X", {"GB"}, 1))
    q = enqueue([], [p])
    assert enqueue(q, [p]) == q


def test_status_has_counts_but_no_job_titles():
    groups = [G("Secret Role Title", "X", {"GB"}, 1), G("Other", "Y", {"GB"}, 2, canonical=False)]
    s = radar.render_status("2026-09-28", False, groups, [("ats", "b1", "HTTP 404")],
                            [SourceResult("ats")], Counter({"ats": 2}), queued=1)
    assert "Secret Role Title" not in s
    assert "1 on your list (Tier 1: 1, Tier 2: 0), 1 outside it" in s
    assert "Waiting to be added to the board:** 1" in s and "HTTP 404" in s
    b = radar.render_status("2026-09-28", True, groups, [], [], Counter(), queued=1)
    assert "First run (baseline)" in b


def test_stale_refs_from_seen():
    from jobradar.board import stale_refs
    k_old, k_new = "c:acme|pentester|GB", "c:acme|appsec|GB"
    seen = {k_old: "2026-09-20", k_new: "2026-09-28", "ats:x": "2026-09-28"}
    refs = [role_ref(k_old), role_ref(k_new), "f" * 16]      # last one was pruned from seen.json
    stale, alive = stale_refs(refs, seen, "2026-09-28", 5)
    assert stale == sorted([role_ref(k_old), "f" * 16]) and alive == [role_ref(k_new)]
