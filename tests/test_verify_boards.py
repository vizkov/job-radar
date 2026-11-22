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


def test_unreachable_workday_board_keeps_its_entry_but_a_dead_board_does_not(tmp_path, monkeypatch):
    """A verify run that Workday refuses (429) must not wipe the Workday boards; a board that is really gone (not found) still drops."""
    import json
    from types import SimpleNamespace as NS
    wd, gone = "https://acme.wd3.myworkdayjobs.com/ext", "https://job-boards.greenhouse.io/moved"
    (tmp_path / "data").mkdir()
    (tmp_path / "boards.json").write_text(json.dumps([
        {"companies": ["Acme"], "ats": "workday", "slug": wd, "url": wd},
        {"companies": ["Moved"], "ats": "greenhouse", "slug": "moved", "url": gone}]))
    rows = [{"company": "Acme", "offices": "", "status": "", "source": "", "ats": "workday", "scraper_slug": wd, "board_url": wd, "board_name": "Acme"},
            {"company": "Moved", "offices": "", "status": "", "source": "", "ats": "greenhouse", "scraper_slug": "moved", "board_url": gone, "board_name": "Moved"}]
    results = {wd: NS(ats="workday", jobs=[], ok=False, error="Workday refuses this address (429)", url=wd),
               gone: NS(ats="greenhouse", jobs=[], ok=False, error="CompanyNotFoundError: not found", url=gone)}

    async def fake_fetch(boards, progress=False):
        return results
    for name, val in [("ROOT", tmp_path), ("DATA", tmp_path / "data"), ("load_candidates", lambda: rows), ("fetch_many", fake_fetch),
                      ("careers_page_companies", lambda: set()), ("profile_path", lambda n: tmp_path / n)]:
        monkeypatch.setattr(verify_boards, name, val)
    verify_boards.main(["--quiet"])
    urls = [b["url"] for b in json.loads((tmp_path / "boards.json").read_text())]
    assert urls == [wd]
