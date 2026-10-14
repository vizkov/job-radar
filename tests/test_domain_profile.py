import importlib.util
from pathlib import Path

from jobradar.career import load_career

_spec = importlib.util.spec_from_file_location("domain_profile", Path(__file__).resolve().parent.parent / "tools" / "domain_profile.py")
dp = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(dp)

RESUME = """---
name: A B
---
# Summary
- [P01] Does payments security.
# Experience
## Role — Co — 2020 to Present
- [B01] Tested payment APIs.
"""


def _career(tmp_path):
    (tmp_path / "master_resume.md").write_text(RESUME, encoding="utf-8")
    return load_career(tmp_path)


def _domain(**kw):
    d = {"strength": "strong", "sectors": ["fintech"], "evidence": ["P01", "B01"], "lead_ids": ["B01"], "not_claimed": ["HSMs"]}
    d.update(kw)
    return {"quiz": {"api": {"answer": "yes"}}, "domains": {"payments": d}}


def test_valid_profile_has_no_problems(tmp_path):
    assert dp.problems(_domain(), _career(tmp_path)) == []


def test_unknown_id_is_rejected(tmp_path):
    assert any("B99" in p for p in dp.problems(_domain(evidence=["P01", "B99"]), _career(tmp_path)))


def test_strong_needs_two_pieces_of_evidence(tmp_path):
    assert any("at least two" in p for p in dp.problems(_domain(evidence=["P01"], lead_ids=["P01"]), _career(tmp_path)))


def test_lead_must_be_evidence_and_not_claimed_required(tmp_path):
    found = dp.problems(_domain(lead_ids=["B01", "P01", "K01"], not_claimed=[]), _career(tmp_path))
    assert any("K01" in p for p in found) and any("NOT claimed" in p for p in found)


def test_bad_quiz_answer_is_rejected(tmp_path):
    data = _domain()
    data["quiz"]["api"]["answer"] = "maybe"
    assert any("answer" in p for p in dp.problems(data, _career(tmp_path)))


def test_lead_ids_by_sector_strongest_first_no_repeats():
    data = {"domains": {
        "a": {"strength": "moderate", "sectors": ["fintech"], "lead_ids": ["P06", "B02"]},
        "b": {"strength": "strong", "sectors": ["Fintech", "banking"], "lead_ids": ["P05", "B02"]},
    }}
    assert dp.lead_ids(data, "fintech") == ["P05", "B02", "P06"]
    assert dp.lead_ids(data, "A") == ["P06", "B02"]
    assert dp.lead_ids(data, "crypto") == []
