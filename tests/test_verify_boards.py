import verify_boards


def test_careers_page_companies_counts_as_coverage(tmp_path, monkeypatch):
    (tmp_path / "careers_pages.yaml").write_text(
        "- company: MDSec\n  url: https://example.com/a\n- company: Old Co\n  url: https://example.com/b\n  enabled: false\n",
        encoding="utf-8")
    monkeypatch.setattr(verify_boards, "profile_path", lambda name: tmp_path / name)
    assert verify_boards.careers_page_companies() == {"mdsec"}
