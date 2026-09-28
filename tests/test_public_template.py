import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
from public_template import is_public  # noqa: E402
import public_template as pt  # noqa: E402


@pytest.mark.parametrize("path", ["tools/radar_helper.py", "jobradar/board.py", ".claude/skills/manual/SKILL.md",
                                  "docs/wiki/Board.md", "examples/config.json", ".github/workflows/radar.yml",
                                  ".githooks/post-commit", "CLAUDE.md", "requirements.txt", "radar.py"])
def test_public_code(path):
    assert is_public(path)


@pytest.mark.parametrize("path", ["profile/config.json", "profile/career/master_resume.md", "state/seen.json",
                                  "data/matches.csv", "data/scores.jsonl", "data/pipeline_log.jsonl", "boards.json",
                                  "work/jd/abc/jd.txt", "digests/status.md", "docs/reviews.md", ".alert_mail/1.eml",
                                  ".claude/settings.local.json", "notes-about-my-interview.md", "some_new_dir/x.py"])
def test_private_or_unknown_never_published(path):
    assert not is_public(path)


def test_status_paths_keeps_both_sides_of_a_rename():
    lines = ["R  docs/wiki/Setup.md -> docs/design/Setup.md", " M tools/manual.py", '?? "docs/a b.md"']
    assert pt.status_paths(lines) == {"docs/wiki/Setup.md", "docs/design/Setup.md", "tools/manual.py", "docs/a b.md"}
