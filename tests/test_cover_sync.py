import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from jobradar import career as cr  # noqa: E402

EXAMPLES = Path(__file__).resolve().parent.parent / "examples" / "career"


def make(tmp_path):
    d = tmp_path / "career"
    shutil.copytree(EXAMPLES, d)
    blocks = d / "cover_blocks.md"
    blocks.write_text(blocks.read_text(encoding="utf-8").rstrip() + "\n\n## [C50] Test block\n<!-- rank 1 | anchor B01 | sources S01 -->\nA block text.\n",
                      encoding="utf-8")
    return d


def test_block_goes_stale_when_its_story_changes(tmp_path):
    d = make(tmp_path)
    assert cr.cover_blocks_stale(d) == [("C50", ["not recorded yet"])]
    assert cr.record_cover_sync(d) == 1
    assert cr.cover_blocks_stale(d) == []
    stories = d / "stories.md"
    lines = stories.read_text(encoding="utf-8").splitlines()
    idx = next(i for i, ln in enumerate(lines) if ln.startswith("## [S01]"))
    lines.insert(idx + 1, "Also true: a new fact.")
    stories.write_text("\n".join(lines) + "\n", encoding="utf-8")
    assert cr.cover_blocks_stale(d) == [("C50", ["S01"])]
    cr.record_cover_sync(d)
    assert cr.cover_blocks_stale(d) == []


def test_blocks_without_metadata_are_ignored():
    assert cr.cover_blocks_stale(EXAMPLES) == []
