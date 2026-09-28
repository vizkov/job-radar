import pytest

from jobradar.career import load_career
from jobradar.paths import EXAMPLES


def test_example_career_parses():
    c = load_career(EXAMPLES / "career")
    assert c.contact["name"] == "Alex Example" and c.contact["email"] == "alex.example@example.com"
    assert c.items["B03"].text.startswith("Performed manual secure code review")
    assert c.items["B03"].section == "Experience" and "ExampleSec" in c.items["B03"].context
    assert c.items["K01"].section == "Skills" and c.items["P01"].section == "Summary"
    assert c.items["S01"].section == "Auth bypass found in code review before launch"
    assert "fallback path" in c.items["S01"].text
    assert c.items["C03"].text.startswith("I am based in India")
    assert "Z999" not in c.items


def test_contact_tokens_include_links_and_phone():
    toks = load_career(EXAMPLES / "career").contact_tokens()
    assert "https://github.com/alex-example" in toks and "alex.example@example.com" in toks
    assert "919000000000" in toks


def test_comments_are_ignored(tmp_path):
    (tmp_path / "master_resume.md").write_text("<!-- - [B09] commented out -->\n# Experience\n- [B01] Real\n")
    c = load_career(tmp_path)
    assert list(c.items) == ["B01"]


def test_duplicate_ids_rejected(tmp_path):
    (tmp_path / "master_resume.md").write_text("# Experience\n- [B01] One\n- [B01] Two\n")
    with pytest.raises(ValueError, match="duplicate ID"):
        load_career(tmp_path)


def test_missing_resume_says_what_to_do(tmp_path):
    with pytest.raises(FileNotFoundError, match="examples/career"):
        load_career(tmp_path)
