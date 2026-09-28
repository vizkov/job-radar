import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import check_doc_links  # noqa: E402


def test_repo_docs_have_no_broken_links():
    assert check_doc_links.main(Path(__file__).resolve().parent.parent) == 0


def test_space_in_target_and_missing_file_are_caught(tmp_path):
    (tmp_path / "docs" / "wiki").mkdir(parents=True)
    (tmp_path / "docs" / "wiki" / "A.md").write_text("[ok](A.md) [bad](The user's-part.md) [gone](B.md)", encoding="utf-8")
    assert check_doc_links.main(tmp_path) == 1
