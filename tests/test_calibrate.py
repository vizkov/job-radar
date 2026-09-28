"""Automatic tier tuning: only with enough evidence, one step, bounded, logged, reversible."""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import calibrate as cal  # noqa: E402

NOW = datetime(2026, 10, 5, tzinfo=timezone.utc)


def seed(rows):
    """rows: (title, fit, recommendation)"""
    cal.MATCHES.write_text("ref,title\n" + "".join(f"r{i:015d},{t}\n" for i, (t, _, _) in enumerate(rows)),
                           encoding="utf-8")
    cal.SCORES.write_text("".join(json.dumps({"key": f"r{i:015d}", "fit_score": f, "recommendation": r}) + "\n"
                                  for i, (_, f, r) in enumerate(rows)), encoding="utf-8")


def filler(n):
    return [("Senior Penetration Tester", 60, "maybe")] * n


def test_nothing_changes_below_the_evidence_threshold():
    seed([("Product Security Engineer", 30, "skip")] * 6 + filler(10))
    assert cal.apply(now=NOW) == []


def test_lowers_a_keyword_whose_roles_keep_scoring_skip_and_logs_it():
    seed([("Product Security Architect", 30, "skip")] * 6 + filler(24))
    before = cal.weights()["product security"]
    changes = cal.apply(now=NOW)
    assert [(c["keyword"], c["from"], c["to"]) for c in changes] == [("product security", before, before - 1)]
    assert cal.weights()["product security"] == before - 1
    assert '"_comment"' in cal.config_path().read_text(encoding="utf-8")   # layout and comments kept
    assert cal.apply(now=NOW) == []                                         # cooldown: one step per week
    assert "back to" in cal.revert("product security") and cal.weights()["product security"] == before


def test_raises_a_keyword_whose_roles_keep_scoring_apply_within_bounds():
    seed([("Security Engineer, AppSec team", 80, "apply")] * 3 + [("Cloud Security Engineer", 80, "apply")] * 5
         + filler(22))
    changes = {c["keyword"]: c for c in cal.apply(now=NOW)}
    assert changes["security engineer"]["to"] == changes["security engineer"]["from"] + 1
