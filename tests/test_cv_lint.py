import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import copy  # noqa: E402

import cv_lint  # noqa: E402
import test_tailor  # noqa: E402  (shares the valid example tailoring)


def errs(sid, text):
    return cv_lint.line_issues(sid, text)[0]


def test_user_reported_phrases_are_errors():
    for bad in ("built a workflow (too new for measured results).", "The LLM workflow came afterwards.",
                "cut triage from about a day to about half a day",
                "across passenger- and customer-data systems",
                "onboarding the first four assessors (from other teams)"):
        assert errs("B01", bad), bad
    assert errs("P09", "an LLM-based (RAG) workflow")
    assert not errs("S01", "a RAG workflow I built")[:0]


def test_my_own_is_a_warning_not_an_error():
    assert not errs("B05", "the assessment team of 4, my own team, reviewing")
    assert cv_lint.line_issues("B05", "the assessment team of 4, my own team, reviewing")[1]


def test_clean_line_passes():
    assert cv_lint.line_issues("B01", "Automated exploit revalidation in Python, cutting triage time by around 50%.") == ([], [])


def test_vague_category_warns():
    for bad in ("Familiar with endpoint tools.", "Scripting ability and networking skills.", "Holds security certifications."):
        assert any("vague" in w for w in cv_lint.line_issues("B01", bad)[1]), bad
    for good in ("Automated exploit revalidation in Python.", "Hold CompTIA Security+."):
        assert not any("vague" in w for w in cv_lint.line_issues("B01", good)[1]), good
    assert not any("vague" in w for w in cv_lint.line_issues("C03", "I have knowledge of this team.")[1])


def test_soft_skill_filler_warns():
    for bad in ("Team player with strong communication skills.", "Detail-oriented and self-motivated engineer."):
        assert any("filler" in w for w in cv_lint.line_issues("P01", bad)[1]), bad
    assert not any("filler" in w for w in cv_lint.line_issues("C03", "I am passionate about this team.")[1])
    assert not any("filler" in w for w in cv_lint.line_issues("B01", "Walked the VPs through the chain with live exploit demonstrations.")[1])


def test_briefed_without_impact_warns():
    assert cv_lint.line_issues("B06", "Briefed the Payments Senior VP and AppSec VPs.")[1]


def test_skill_capitalisation_and_language_list():
    assert cv_lint.skill_issues("K01", "Application security: Web, API, bug bounty triage", "Application security")
    assert cv_lint.skill_issues("K02", "Vulnerability management: Bug bounty triage, CVSS", "Vulnerability management")
    assert not cv_lint.skill_issues("K07", "Languages: Java, Python, JavaScript, TypeScript (Node.js)", "Languages")
    assert cv_lint.skill_issues("K07", "Languages: Java, JavaScript/TypeScript (Node.js)", "Languages")


def test_static_lines_skills_rows_and_role_floor():
    d = copy.deepcopy(test_tailor.GOOD)
    for sec in d["sections"]:
        sec["bullets"] = [b for b in sec["bullets"] if b["source_id"][0] not in "EK"]
    e, _ = cv_lint.tailored_issues(d, test_tailor.CAREER)
    assert any("static section line" in x for x in e)
    assert any("skills rows missing" in x for x in e)
    d2 = copy.deepcopy(test_tailor.GOOD)
    d2["sections"][-1]["bullets"] = [b for b in d2["sections"][-1]["bullets"] if b["source_id"][0] != "B"]
    e2, _ = cv_lint.tailored_issues(d2, test_tailor.CAREER)
    assert any("keep at least" in x for x in e2)


def test_location_destination_is_an_error():
    d = copy.deepcopy(test_tailor.GOOD)
    d["location"] = "Bengaluru, India · Open to relocation to Geneva"
    assert any("Open to relocation" in x for x in cv_lint.tailored_issues(d, test_tailor.CAREER)[0])
