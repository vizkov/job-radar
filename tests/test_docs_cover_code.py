"""The overview docs must list what the code has, so per-change edits can't silently skip them."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import board_sync  # noqa: E402

DESIGN, WIKI = ROOT / "docs" / "design", ROOT / "docs" / "wiki"


def read(p):
    return p.read_text(encoding="utf-8")


def test_every_board_field_is_explained():
    for field in board_sync.FIELDS:
        assert f"*{field}*" in read(DESIGN / "01-Concepts.md"), f"01-Concepts: board field {field}"
        assert f"| {field} |" in read(WIKI / "Board.md"), f"wiki/Board.md: board field {field}"


def test_every_skill_is_listed():
    for skill in sorted(p.parent.name for p in (ROOT / ".claude" / "skills").glob("*/SKILL.md")):
        assert f"`{skill}`" in read(ROOT / "CLAUDE.md") or skill == "manual" and "`manual`" in read(ROOT / "CLAUDE.md"), \
            f"CLAUDE.md skill table: {skill}"
        assert f"`{skill}`" in read(DESIGN / "04-Claude-session.md"), f"04-Claude-session skill table: {skill}"


def test_every_tool_is_in_the_code_reference():
    ref = read(DESIGN / "05-Code-reference.md")
    for tool in sorted((ROOT / "tools").glob("*.py")):
        assert f"`tools/{tool.name}`" in ref, f"05-Code-reference: tools/{tool.name}"


def test_every_config_section_is_documented():
    cfg = json.loads(read(ROOT / "examples" / "config.json"))
    doc = read(DESIGN / "10-Configuration.md")
    for key in cfg:
        if not key.startswith("_"):
            assert key in doc, f"10-Configuration: config key {key}"


# How each skill shows up in the user guide's "Things you can say" (docs/wiki/Using-it.md).
# A new skill must get a row there and an entry here, or this test fails.
USER_PHRASES = {
    "apply-assist": "Help me apply", "consultant-brief": "What's new?", "cv-review": "How do I strengthen my CV?",
    "docs-review": "Are the docs still right?", "health": "Is anything broken?", "interview-prep": "I have an interview",
    "manual": "/manual", "referrals": "Who do I know at", "score-roles": "Which of these fit me?",
    "setup": "Set this up for me", "sponsorship-check": "sponsor my visa", "system-review": "What could be better?",
    "tailor-application": "Tailor my CV", "track": "I applied to", "tune-radar": "Stop showing",
}


def test_every_skill_has_a_row_in_the_user_guide():
    guide = read(WIKI / "Using-it.md")
    skills = sorted(p.parent.name for p in (ROOT / ".claude" / "skills").glob("*/SKILL.md"))
    for skill in skills:
        assert skill in USER_PHRASES, f"add {skill} to USER_PHRASES and a row in docs/wiki/Using-it.md"
        assert USER_PHRASES[skill] in guide, f"docs/wiki/Using-it.md has no row for {skill} ({USER_PHRASES[skill]!r})"
