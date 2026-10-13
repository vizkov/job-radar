"""tools/careers_queue.py: the Chrome careers-site queue."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import careers_queue as cq  # noqa: E402
import post_leads as pl  # noqa: E402

ROWS = [
    {"company": "Alpha", "status": "VERIFIED", "jobs_in_target_countries": "40"},
    {"company": "Beta", "status": "boards empty (stale / moved ATS)", "jobs_in_target_countries": "0"},
    {"company": "Gamma Group", "status": "VERIFIED", "jobs_in_target_countries": "0"},
    {"company": "Delta / Co", "status": "not covered", "jobs_in_target_countries": ""},
]


def setup(monkeypatch, tmp_path, **over):
    base = {**pl.DEFAULTS, "dream_companies": ["Alpha", "Beta", "Gamma"], "dream_consulting": ["Delta"], "chrome_always": ["Tesla"],
            "careers_site_companies": ["Tesla"], "company_fit": "High", **over}
    monkeypatch.setattr(pl, "settings", lambda: base)
    monkeypatch.setattr(pl, "network_companies", lambda: ["Epsilon"])
    monkeypatch.setattr(pl, "fit_targets", lambda fit: ["Zeta", "Alpha"])
    monkeypatch.setattr(cq, "STATE", tmp_path / "chrome.json")


def test_only_companies_the_radar_cannot_read_are_queued_in_tier_order(monkeypatch, tmp_path):
    setup(monkeypatch, tmp_path)
    q = cq.queue(ROWS, {})
    assert [n for _, n in q] == ["Beta", "Gamma", "Delta", "Tesla", "Epsilon", "Zeta"]   # Alpha is VERIFIED with jobs: not queued
    assert [t for t, _ in q] == [0, 0, 0, 1, 1, 2]
    # Tesla is always read though careers_site_companies lists it; Epsilon and Zeta have no coverage row: unknown means read


def test_a_read_counts_only_when_it_is_recorded_and_moves_the_company_to_the_back_of_its_tier(monkeypatch, tmp_path):
    setup(monkeypatch, tmp_path)
    assert [n for _, n in cq.queue(ROWS)][:3] == ["Beta", "Gamma", "Delta"]
    assert [n for _, n in cq.queue(ROWS)][:3] == ["Beta", "Gamma", "Delta"]        # asking twice marks nothing
    cq.done("Beta", roles=0, now="2026-10-13T10:00:00+00:00")
    assert [n for _, n in cq.queue(ROWS)][:3] == ["Gamma", "Delta", "Beta"]        # Beta finished: back of the dream tier; a tier-1 company never jumps it


def test_url_is_remembered_and_listed(monkeypatch, tmp_path, capsys):
    setup(monkeypatch, tmp_path)
    monkeypatch.setattr(cq, "_coverage_rows", lambda path=None: ROWS)
    cq.set_url("Beta", "https://example.test/jobs?q=security")
    cq.main(["next", "--n", "1"])
    assert "Beta\tdream\thttps://example.test/jobs?q=security" in capsys.readouterr().out


def test_the_dream_lists_never_take_every_slot(monkeypatch, tmp_path):
    q = [(0, f"D{i}") for i in range(9)] + [(1, "N1"), (1, "N2"), (2, "T1")]
    assert [n for _, n in cq.pick(q, 6, 2)] == ["D0", "D1", "D2", "D3", "N1", "N2"]       # four dream, two reserved for the rest
    assert [n for _, n in cq.pick(q[:3] + [(2, "T1")], 6, 2)] == ["D0", "D1", "D2", "T1"]  # a short dream list: nothing is wasted
    assert [n for _, n in cq.pick(q[9:], 6, 2)] == ["N1", "N2", "T1"]                      # no dream companies: all slots go to the rest
