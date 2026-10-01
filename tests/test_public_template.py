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


def test_wiki_text_rewrites_links():
    src = "[Board](Board.md) · [Sec](../design/Security-model.md#secrets) · [x](Using-it.md#costs) · https://a.b/c.md"
    out = pt.wiki_text(src, "https://github.com/o/r/blob/main")
    assert out == ("[Board](Board) · [Sec](https://github.com/o/r/blob/main/docs/design/Security-model.md#secrets)"
                   " · [x](Using-it#costs) · https://a.b/c.md")


def _git(cwd, *args):
    import subprocess
    env = {**__import__("os").environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}
    return subprocess.run(["git", *args], cwd=cwd, env=env, capture_output=True, text=True, check=True).stdout


def test_publish_uses_committed_content_only(tmp_path, monkeypatch):
    """Uncommitted edits to public files are not listed as drift and not copied: they are reported by dirty_public()."""
    tpl, mine = tmp_path / "tpl", tmp_path / "mine"
    (tpl / "tools").mkdir(parents=True)
    _git(tpl, "init", "-q", "-b", "main")
    (tpl / "tools" / "a.py").write_text("a = 1\n", encoding="utf-8")
    _git(tpl, "add", "-A")
    _git(tpl, "commit", "-q", "-m", "base")
    _git(tmp_path, "clone", "-q", str(tpl), str(mine))
    _git(mine, "remote", "rename", "origin", "template")
    (mine / "tools" / "b.py").write_text("b = 'committed'\n", encoding="utf-8")        # committed change: publishable
    _git(mine, "add", "-A")
    _git(mine, "commit", "-q", "-m", "add b")
    (mine / "tools" / "a.py").write_text("a = 'unfinished edit'\n", encoding="utf-8")   # uncommitted edit to a tracked public file
    (mine / "tools" / "c.py").write_text("c = 1\n", encoding="utf-8")                   # untracked public file
    (mine / "profile").mkdir()
    (mine / "profile" / "x.json").write_text("{}", encoding="utf-8")                    # private: never listed either way
    monkeypatch.setattr(pt, "ROOT", mine)
    assert pt.drift(fetch=False) == ["tools/b.py"]                                      # committed only
    assert pt.dirty_public() == ["tools/a.py", "tools/c.py"]                            # reported, not published
    assert pt.committed_bytes("tools/b.py") == b"b = 'committed'\n"
    assert pt.committed_bytes("tools/a.py") == b"a = 1\n"                                # HEAD's version, not the edit
    assert pt.committed_bytes("tools/c.py") is None
