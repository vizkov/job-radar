"""Roles held back for a sponsor-register name lookup (jobradar/register_check.py, tools/register_check.py)."""
import sys
from datetime import datetime, timezone

import pytest

from jobradar import register_check as rc
from jobradar.board import outside_tier1_ok, register_holds
from jobradar.common import ROOT
from jobradar.dedupe import Group
from jobradar.model import Posting
from jobradar.sponsors import Register, Sponsors, _load_overrides

sys.path.insert(0, str(ROOT / "tools"))
import cadence  # noqa: E402
import register_check as tool  # noqa: E402

CFG = {"enabled": True, "tiers": [1, 2], "outside_tier1": {"min_title_weight": 3, "min_score": 7, "max_age_days": 30}}
TODAY = datetime.now(timezone.utc).date().isoformat()


def group(company="Brandname", country="GB", sponsor=None, score=8):
    p = Posting(source="linkedin_email", company=company, title="Application Security Engineer", location="London",
                countries=frozenset([country]), url="https://example.com/1", external_id="1",
                posted_at=datetime.now(timezone.utc))
    sponsor = sponsor or Sponsors(Register(["Other Ltd"]), Register(["Other B.V."])).tag(company)
    return Group(f"c:{company.lower()}|appsec|{country}", [p], {"sponsor": sponsor, "score": score, "tier": 1})


def test_only_a_register_miss_is_held():
    held = register_holds([group()], CFG, False, TODAY)
    assert [(r["company"], r["country"]) for r in held] == [("Brandname", "GB")]
    assert not outside_tier1_ok(group(), CFG)                          # held, not carded
    assert register_holds([group(score=3)], CFG, False, TODAY) == []   # fails another condition
    assert register_holds([group(country="IE")], CFG, False, TODAY) == []   # no register there
    listed = group(company="Other")
    assert register_holds([listed], CFG, False, TODAY) == []           # on the register: carded as usual
    pinned = Sponsors(Register(["Other Ltd"]), Register([]), {"brandname": {"uk": "no", "nl": ""}}).tag("Brandname")
    assert register_holds([group(sponsor=pinned)], CFG, False, TODAY) == []


def test_a_looked_up_name_is_remembered_and_used(tmp_path):
    holds, names = tmp_path / "holds.csv", tmp_path / "names.csv"
    paths = dict(holds=holds, names=names, issue_map=tmp_path / "m.json", queue=tmp_path / "q.json")
    rc.add_holds(register_holds([group()], CFG, False, TODAY), TODAY, 30, holds)
    assert len(rc.pending(TODAY, 30, **paths)) == 1
    rc.record("Brandname", "uk", "Legal Entity Ltd", "https://brandname.example/terms", TODAY, names)
    assert rc.pending(TODAY, 30, **paths) == []
    overrides = _load_overrides(tmp_path / "none.csv", names)
    tag = Sponsors(Register(["Legal Entity Ltd"]), Register([]), overrides).tag("Brandname")["uk"]
    assert (tag.status, tag.matched) == ("yes", "Legal Entity Ltd")


def test_a_manual_pin_beats_a_looked_up_name(tmp_path):
    manual, names = tmp_path / "overrides.csv", tmp_path / "names.csv"
    manual.write_text("company,uk,nl\nBrandname,no,\n", encoding="utf-8")
    rc.record("Brandname", "uk", "Legal Entity Ltd", "https://brandname.example", TODAY, names)
    assert _load_overrides(manual, names)["brandname"]["uk"] == "no"


def test_confirm_needs_a_real_entry_and_a_real_source(monkeypatch):
    monkeypatch.setattr(tool, "register_names", lambda country: ["Legal Entity Ltd"])
    with pytest.raises(ValueError):
        tool.confirm("Brandname", "uk", "Made Up Ltd", "https://brandname.example", TODAY)
    with pytest.raises(ValueError):
        tool.confirm("Brandname", "uk", "Legal Entity Ltd", "https://www.linkedin.com/company/x", TODAY)


def test_marking_matches_keeps_other_rows_and_line_endings(tmp_path):
    f = tmp_path / "matches.csv"
    f.write_bytes(b"ref,company,uk_sponsor\r\na,\"X, Y\",no\r\nb,Z,no\r\n")
    assert tool.mark_matches({"a"}, "uk_sponsor", "X Ltd", f) == 1
    assert f.read_bytes() == b"ref,company,uk_sponsor\r\na,\"X, Y\",yes (X Ltd)\r\nb,Z,no\r\n"


@pytest.mark.parametrize("pending,due", [(0, False), (2, True)])
def test_cadence_line(tmp_path, pending, due):
    lines, due_jobs = cadence.block(datetime(2026, 1, 2), tmp_path, radar_last="2026-01-02", new_total=0, new_on_board=0,
                                    new_skip=0, new_waiting=0, queued=0, unscored_cards=0, auto_picks=0, awaiting=0,
                                    posts_enabled=False, register_pending=pending)
    assert any("Sponsor register check" in line for line in lines)
    assert ("register_check" in due_jobs) is due
