import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import resume_diff as rd  # noqa: E402


def doc(*bullets, headline="H", skills=(), **extra):
    return {"headline": headline, "skills": list(skills), **extra,
            "sections": [{"heading": "Experience", "bullets": [{"source_id": i, "text": t} for i, t in bullets]}]}


def test_reworded_added_left_out_moved_and_skills_are_reported():
    general = doc(("B1", "one"), ("B2", "two"), ("B3", "three"), ("B4", "same"), skills=["Python", "Java"])
    tailored = doc(("B3", "three"), ("B1", "uno"), ("B4", "same"), ("B9", "new"), skills=["Python", "Go"],
                   dropped={"B2": "no JD match"})
    out = rd.diff(general, tailored)
    assert "1 reworded, 1 added, 1 left out, 2 unchanged" in out
    assert "general: one" in out and "tailored: uno" in out
    assert "**B9**: new" in out and "**B2**: two _(reason: no JD match)_" in out
    assert "B1, B3, B4 → B3, B1, B4" in out
    assert "Skills added: Go" in out and "Skills removed: Java" in out
    assert "same" not in out


def test_identical_resumes_report_only_the_count():
    d = doc(("B1", "one"))
    assert rd.diff(d, d) == "**Against the general resume:** 0 reworded, 0 added, 0 left out, 1 unchanged."
