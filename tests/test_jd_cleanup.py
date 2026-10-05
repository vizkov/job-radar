import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import jd_cleanup as jc  # noqa: E402

NOW = datetime(2026, 10, 5, 12, 0)


def make(tmp_path, stages, skip_scored=(), roles=()):
    root = tmp_path
    (root / "data").mkdir()
    (root / "work" / "jd").mkdir(parents=True)
    (root / "data" / "pipeline_log.jsonl").write_text(
        "".join(json.dumps({"ref": r, "field": "Stage", "value": v, "at": at.isoformat()}) + "\n" for r, v, at in stages), encoding="utf-8")
    (root / "data" / "scores.jsonl").write_text(
        "".join(json.dumps({"ref": r, "recommendation": "skip"}) + "\n" for r in skip_scored), encoding="utf-8")
    for r in list(roles):
        d = root / "work" / "jd" / r
        d.mkdir()
        for f in ("jd.txt", "packet.md", "score.json", "meta.json"):
            (d / f).write_text("x" * 100, encoding="utf-8")
    return root


def test_skipped_and_rejected_are_trimmed_after_their_retention_and_verdicts_are_kept(tmp_path):
    root = make(tmp_path, [("a" * 16, "Skipped", NOW - timedelta(days=20)), ("b" * 16, "Skipped", NOW - timedelta(days=3)),
                           ("c" * 16, "Rejected", NOW - timedelta(days=20)), ("d" * 16, "Rejected", NOW - timedelta(days=40)),
                           ("e" * 16, "Applied", NOW - timedelta(days=90))], roles=["a" * 16, "b" * 16, "c" * 16, "d" * 16, "e" * 16])
    assert sorted(c["ref"] for c in jc.candidates(root, NOW)) == ["a" * 16, "d" * 16]
    assert "removed" in jc.run(root, NOW)
    jd = root / "work" / "jd"
    assert not (jd / ("a" * 16 / "x" if False else "a" * 16) / "jd.txt").exists()
    assert (jd / ("a" * 16) / "score.json").exists() and (jd / ("a" * 16) / "meta.json").exists()
    assert (jd / ("b" * 16) / "jd.txt").exists() and (jd / ("c" * 16) / "jd.txt").exists() and (jd / ("e" * 16) / "jd.txt").exists()
    assert jc.candidates(root, NOW) == []


def test_skip_scored_role_with_no_stage_is_trimmed_but_a_stage_protects_it(tmp_path):
    root = make(tmp_path, [("f" * 16, "Shortlisted", NOW - timedelta(days=60))], skip_scored=["f" * 16, "g" * 16], roles=["f" * 16, "g" * 16])
    old = (NOW - timedelta(days=30)).timestamp()
    import os
    for r in ("f" * 16, "g" * 16):
        os.utime(root / "work" / "jd" / r / "score.json", (old, old))
    assert [c["ref"] for c in jc.candidates(root, NOW)] == ["g" * 16]


def test_dry_run_changes_nothing(tmp_path):
    root = make(tmp_path, [("a" * 16, "Skipped", NOW - timedelta(days=20))], roles=["a" * 16])
    assert "would remove" in jc.run(root, NOW, dry=True)
    assert (root / "work" / "jd" / ("a" * 16) / "jd.txt").exists()
