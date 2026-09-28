import asyncio
import re

import radar
from jobradar.dedupe import group_postings
from jobradar.matching import CompanyMatcher
from jobradar.model import Posting, SourceResult, UnitStatus
from jobradar.sources import run_sources


def P(source, company, title, countries, url):
    return Posting(source=source, company=company, title=title, location="", countries=frozenset(countries), url=url)


class Fake:
    def __init__(self, name, result=None, exc=None, sleep=0, timeout=5):
        self.name, self.result, self.exc, self.sleep, self.timeout = name, result, exc, sleep, timeout

    async def fetch(self):
        await asyncio.sleep(self.sleep)
        if self.exc:
            raise self.exc
        return self.result


def test_one_broken_source_does_not_stop_others():
    good = SourceResult("good", postings=[P("good", "X", "Pentester", {"GB"}, "u")],
                        units=[UnitStatus("q", ok=True, raw_count=1)])
    results = asyncio.run(run_sources([
        Fake("good", good),
        Fake("crashes", exc=RuntimeError("boom")),
        Fake("hangs", sleep=10, timeout=0.1),
    ]))
    by = {r.source: r for r in results}
    assert by["good"].ok and len(by["good"].postings) == 1
    assert not by["crashes"].ok and "RuntimeError: boom" in by["crashes"].error
    assert not by["hangs"].ok and "timeout" in by["hangs"].error


def test_select_filters_and_matches():
    m = CompanyMatcher(["Secura", "MDSec"], [])
    res = SourceResult("s", postings=[
        P("s", "Secura B.V.", "Penetration Tester", {"NL"}, "1"),
        P("s", "Secura", "Cloud Security Engineer", {"NL"}, "2"),       # excluded title
        P("s", "MDSec", "Penetration Tester", {"US"}, "3"),             # wrong country
        P("s", "Unknown Ltd", "Penetration Tester", {"GB"}, "4"),       # not on list
    ])
    kept, counts = radar.select([res], include_outside=False, matcher=m)
    assert [(p.url, p.company_canonical) for p in kept] == [("1", "Secura")]
    kept, _ = radar.select([res], include_outside=True, matcher=m)
    assert {p.url for p in kept} == {"1", "4"}


def test_diff_seen_uses_id_and_content_key():
    today = "2026-09-27"
    a = P("ats", "X", "Pentester", {"GB"}, "https://x/1"); a.company_canonical = "X"
    seen = {}
    assert len(radar.diff_seen(group_postings([a]), seen, today)) == 1
    # same role later seen via LinkedIn only: different id, same content key → not new
    b = P("linkedin_email", "X Ltd", "Pentester", {"GB"}, "https://li/9"); b.company_canonical = "X"
    assert radar.diff_seen(group_postings([b]), seen, today) == []


def test_digest_renders_sections():
    a = P("ats", "X", "Pentester", {"GB"}, "https://x/1"); a.company_canonical = "X"
    o = P("eures", "Acme", "Pentester", {"DE"}, "https://e/1")
    groups = group_postings([a, o])
    results = [SourceResult("ats", units=[UnitStatus("b", ok=True, raw_count=3)]),
               SourceResult("eures", ok=False, error="timeout after 300s")]
    d = radar.render_digest("2026-09-27", False, groups, [("eures", "q", "timeout")], results,
                            __import__("collections").Counter({"ats": 1}))
    assert "### X" in d and "## Outside your list" in d and "**Acme**" in d
    assert "| eures | FAILED: timeout after 300s |" in d
    assert "Sources that stopped returning results" in d


def test_per_source_outside_flag():
    m = CompanyMatcher(["Secura"], [])
    a = SourceResult("ats", postings=[P("ats", "Nobody Ltd", "Pentester", {"GB"}, "1")])
    e = SourceResult("eures", postings=[P("eures", "", "Pentester", {"NL"}, "2")])
    kept, _ = radar.select([a, e], include_outside={"eures": True}, matcher=m)
    assert [p.url for p in kept] == ["2"]


UNESCAPED_LINK = re.compile(r"(?<!\\)\]\(")  # "](" not preceded by a backslash


def test_markdown_injection_is_neutralized():
    evil = "Pentester](https://evil.example) ![x](http://t/p.png) <img src=x> **bold** | a"
    out = radar.md(evil)
    for ch in "[]<>*|!":
        assert "\\" + ch in out
    assert not UNESCAPED_LINK.search(out)
    assert radar.md("Senior AppSec Engineer (m/w/d)") == "Senior AppSec Engineer (m/w/d)"
    assert radar.md_url("javascript:alert(1)") == "#"
    assert radar.md_url("https://x/a b(c)") == "https://x/a%20b%28c%29"


def test_digest_line_escapes_title():
    a = P("careers_page", "X", "Pentester](https://evil.example)", {"GB"}, "https://x/1")
    a.company_canonical = "X"
    line = radar._line(group_postings([a])[0])
    assert line.startswith("- [Pentester\\](https://evil.example)](https://x/1)")
    assert len(UNESCAPED_LINK.findall(line)) == 1  # only the real link


def test_matches_csv_column_change_is_migrated(tmp_path, monkeypatch):
    import csv
    monkeypatch.setattr(radar, "DATA", tmp_path)
    (tmp_path / "matches.csv").write_text("date,company,title\n2026-09-01,Old Co,Old Role\n", encoding="utf-8")
    a = P("ats", "X", "Pentester", {"GB"}, "https://x/1"); a.company_canonical = "X"
    radar.append_matches(group_postings([a]), "2026-09-28")
    rows = list(csv.DictReader(open(tmp_path / "matches.csv", encoding="utf-8")))
    assert [r["company"] for r in rows] == ["Old Co", "X"]
    assert rows[0]["ref"] == "" and rows[1]["ref"] and rows[1]["title"] == "Pentester"


def test_drop_reasons_are_counted_per_source():
    from collections import Counter
    from jobradar.matching import CompanyMatcher
    from jobradar.model import Posting, SourceResult
    m = CompanyMatcher(["Bridewell"], [])
    ps = [Posting("linkedin_email", "Bridewell", "Senior Penetration Tester", "London", frozenset({"GB"}), "u1"),
          Posting("linkedin_email", "Acme", "Senior Penetration Tester", "London", frozenset({"GB"}), "u2"),
          Posting("linkedin_email", "Bridewell", "Sales Manager", "London", frozenset({"GB"}), "u3"),
          Posting("linkedin_email", "Bridewell", "Pentester", "Boston", frozenset({"US"}), "u4"),
          Posting("linkedin_email", "Bridewell", "Pentester (Contract)", "London", frozenset({"GB"}), "u5")]
    res = SourceResult("alert_email", postings=ps)
    dropped = Counter()
    kept, matched = radar.select([res], include_outside=False, matcher=m, dropped=dropped)
    assert len(kept) == 1 and dropped == Counter({("alert_email", "company"): 1, ("alert_email", "title"): 1,
                                                  ("alert_email", "country"): 1, ("alert_email", "employment"): 1,
                                                  ("alert_email", "where:US"): 1})
    line = radar.drop_lines([res], matched, dropped)[0]
    assert line.startswith("- **alert_email**: 5 found →") and "1 outside your countries (US 1)" in line and "**1 kept**" in line
