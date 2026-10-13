"""tools/sweep_plan.py: one plan, one cap, split by kind of company."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import careers_queue as cq  # noqa: E402
import post_leads as pl  # noqa: E402
import sweep_plan as sp  # noqa: E402

ROWS = [{"company": n, "status": "VERIFIED", "jobs_in_target_countries": "20"} for n in ("P1", "P2", "P3", "P4", "P5", "C1", "C2", "C3", "N1", "N2", "N3")] + [
    {"company": "P2", "status": "boards empty (stale / moved ATS)", "jobs_in_target_countries": "0"},
    {"company": "O1", "status": "not covered", "jobs_in_target_countries": ""}, {"company": "O2", "status": "not covered", "jobs_in_target_countries": ""}]
ROWS = [r for r in ROWS if not (r["company"] == "P2" and r["status"] == "VERIFIED")]


def s(**over):
    return {**pl.DEFAULTS, "dream_companies": ["P1", "P2", "P3", "P4", "P5"], "dream_consulting": ["C1", "C2", "C3"], "chrome_always": [],
            "careers_site_companies": [], "company_fit": "High", "max_searches": 10, **over}


def setup(monkeypatch):
    monkeypatch.setattr(pl, "network_companies", lambda: ["N1", "N2", "N3"])
    monkeypatch.setattr(pl, "fit_targets", lambda fit: ["O1", "O2"])


def test_the_pass_is_split_3_3_2_2_and_each_company_appears_once(monkeypatch):
    setup(monkeypatch)
    out = sp.plan(s(), ROWS, {}, {})
    assert len(out) == 10
    assert [c for _, c, _ in out].count("dream_product") == 3 and [c for _, c, _ in out].count("dream_consulting") == 3
    assert [c for _, c, _ in out].count("network") == 2 and [c for _, c, _ in out].count("other") == 2
    assert len({n for n, _, _ in out}) == 10
    assert {ln for n, c, ln in out if c == "other"} == {"careers"}          # chrome-only companies are read, not post-searched


def test_a_company_the_radar_reads_gets_the_post_search_only_and_one_the_radar_cannot_read_alternates(monkeypatch):
    setup(monkeypatch)
    lanes = {n: ln for n, _, ln in sp.plan(s(), ROWS, {}, {})}
    assert lanes["P1"] == "post"                                            # P1 is VERIFIED with jobs: the radar already has its roles
    assert lanes["P2"] == "post"                                            # never done either way: the post search goes first
    after_post = {n: ln for n, _, ln in sp.plan(s(dream_companies=["P2"]), ROWS, {"company|p2": {"last": "2026-10-13T10:00:00+00:00"}}, {})}
    assert after_post["P2"] == "careers"                                    # the careers read was done longer ago (never)
    both = {n: ln for n, _, ln in sp.plan(s(dream_companies=["P2"]), ROWS, {"company|p2": {"last": "2026-10-13T10:00:00+00:00"}}, {"p2": {"last": "2026-10-14T10:00:00+00:00"}})}
    assert both["P2"] == "post"                                             # now the post search is the older one


def test_spare_slots_flow_to_the_next_category_and_the_total_never_exceeds_the_cap(monkeypatch):
    setup(monkeypatch)
    out = sp.plan(s(dream_consulting=[]), ROWS, {}, {})                     # no consulting list yet: its 3 slots flow on
    assert len(out) == 10 and not [1 for _, c, _ in out if c == "dream_consulting"]
    assert len(sp.plan(s(max_searches=6), ROWS, {}, {})) == 6


def test_a_company_with_two_lanes_does_not_outrank_one_lane_companies(monkeypatch):
    """The independent review (2026-10-13): ranking by the OLDER lane put Google (two lanes) in every pass and Anthropic in half of them."""
    setup(monkeypatch)
    cfg = s(dream_companies=["P1", "P2", "P3", "P4", "P5"], max_searches=4, sweep_quotas={"dream_product": 4, "dream_consulting": 0, "network": 0, "other": 0})
    post, careers, covered, tick = {}, {}, {}, 0
    for n in range(15):
        for name, _, lane in sp.plan(cfg, ROWS, post, careers, total=4):
            tick += 1                                                            # every finished action gets its own, later timestamp
            stamp = f"2026-10-10T10:{tick // 60:02d}:{tick % 60:02d}+00:00"
            covered[name] = covered.get(name, 0) + 1
            (post.__setitem__(f"company|{name.lower()}", {"last": stamp}) if lane == "post" else careers.__setitem__(name.lower(), {"last": stamp}))
    assert max(covered.values()) - min(covered.values()) <= 2                    # P2 (two lanes) is covered about as often as the others


def test_spare_slots_flow_down_from_the_short_category_not_back_to_the_top(monkeypatch):
    setup(monkeypatch)
    out = sp.plan(s(dream_consulting=[]), ROWS, {}, {})
    cats = [c for _, c, _ in out]
    assert cats.count("network") == 3 and cats.count("other") == 2          # the spare slots went down first and used up the lists below...
    assert cats.count("dream_product") == 5                                 # ...and only the one slot nothing below could take wrapped back to the top (not +3)
