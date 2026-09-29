import verify_boards


def test_blocklisted_boards_never_become_candidates(tmp_path, monkeypatch):
    data = tmp_path / "data"
    data.mkdir()
    header = "company,offices,status,source,ats,scraper_slug,board_url,board_name\n"
    (data / "candidates.csv").write_text(
        header + "Synthesia,,x,map,bamboohr,synthesia,https://synthesia.bamboohr.com/careers,Synthesia\n"
                 "Synthesia,,x,map,ashby,synthesia,https://jobs.ashbyhq.com/synthesia,Synthesia\n"
                 "Acme,,x,map,lever,acme,https://jobs.lever.co/acme/,Acme\n", encoding="utf-8")
    (tmp_path / "board_blocklist.csv").write_text(
        "ats,slug,board_url,reason\nBambooHR,Synthesia,,placeholder board\n,,https://jobs.lever.co/acme,wrong entity\n",
        encoding="utf-8")
    monkeypatch.setattr(verify_boards, "DATA", data)
    monkeypatch.setattr(verify_boards, "profile_path", lambda name: tmp_path / name)   # blocklist matches case-insensitively
    rows = verify_boards.load_candidates()
    assert [(r["company"], r["ats"]) for r in rows] == [("Synthesia", "ashby")]        # ashby kept; url match drops Acme
    monkeypatch.setattr(verify_boards, "profile_path", lambda name: tmp_path / "none" / name)
    assert len(verify_boards.load_candidates()) == 3                                    # no blocklist file: nothing dropped


def test_careers_page_companies_counts_as_coverage(tmp_path, monkeypatch):
    (tmp_path / "careers_pages.yaml").write_text(
        "- company: MDSec\n  url: https://example.com/a\n- company: Old Co\n  url: https://example.com/b\n  enabled: false\n",
        encoding="utf-8")
    monkeypatch.setattr(verify_boards, "profile_path", lambda name: tmp_path / name)
    assert verify_boards.careers_page_companies() == {"mdsec"}
