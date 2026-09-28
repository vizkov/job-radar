import csv
from pathlib import Path

import pytest

import radar
from jobradar.dedupe import group_postings
from jobradar.model import Posting
from jobradar.sponsors import REG_DIR, Register, SponsorTag, Sponsors
from jobradar.tiering import score, tier

UK = Register(["Deloitte LLP", "MDSec Consulting Limited", "ADYEN N.V. LONDON BRANCH", "Amazon Filters Ltd",
               "Amazon UK Services Ltd", "Amazonico UK Limited", "Revolut Ltd", "ING Services Limited",
               "Monzo Bank Ltd"])
NL = Register(["Adyen N.V.", "Gradyent B.V.", "Northwave Nederland B.V.", "Fox-IT", "ING Bank N.V."])


@pytest.mark.parametrize("company,status,matched,how", [
    ("Deloitte LLP", "yes", "Deloitte LLP", "exact"),
    ("Deloitte", "yes", "Deloitte LLP", "exact"),               # LLP stripped on both sides
    ("MDSec", "yes", "MDSec Consulting Limited", "prefix"),
    ("Adyen", "yes", "ADYEN N.V. LONDON BRANCH", "prefix"),
    ("Amazon", "unknown", "Amazon Filters Ltd / Amazon UK Services Ltd", "prefix:2 entities"),  # ambiguous
    ("Revolutt", "unknown", "Revolut Ltd", "fuzzy:93"),         # typo: close but not certain
    ("Pen Test Partners", "no", "", ""),
    ("ING", "no", "", ""),                                      # too short for prefix matching
    ("", "unknown", "", ""),
])
def test_uk_lookup(company, status, matched, how):
    assert UK.lookup(company) == SponsorTag(status, matched, how)


def test_word_boundary_prefix():
    assert UK.lookup("Amazonico").status == "yes"
    assert "Amazonico" not in UK.lookup("Amazon").matched     # not a word-prefix of "amazonico"
    assert NL.lookup("Adyen") == SponsorTag("yes", "Adyen N.V.", "exact")  # not "Gradyent"


def test_overrides_and_canonical_fallback():
    s = Sponsors(UK, NL, {"ing": {"uk": "ING Services Limited", "nl": "ING Bank N.V."},
                          "amazon": {"uk": "Amazon UK Services Ltd", "nl": ""},
                          "codewhite": {"uk": "no", "nl": ""}})
    ing = s.tag("ING", "ING")
    assert ing["uk"] == SponsorTag("yes", "ING Services Limited", "override") and ing["nl"].matched == "ING Bank N.V."
    assert s.tag("Amazon Development Centre", "Amazon")["uk"].how == "override"   # via canonical name
    assert s.tag("Code White", "Code White")["uk"] == SponsorTag("no", how="override")
    # raw employer name unknown to the register, canonical name matches
    assert s.tag("Northwave Cyber Security B.V.", "Northwave")["nl"].matched == "Northwave Nederland B.V."


def test_missing_register_is_unknown():
    s = Sponsors(Register([]), NL)
    assert s.tag("Adyen")["uk"] == SponsorTag("unknown", how="register missing")


def test_real_registers_are_present_and_plausible():
    if not (REG_DIR / "uk_sponsors.csv").exists():
        pytest.skip("registers not fetched yet (python tools/refresh_registers.py)")
    for name, minimum in (("uk_sponsors.csv", 50_000), ("nl_sponsors.csv", 5_000)):
        with open(REG_DIR / name, encoding="utf-8") as fh:
            assert sum(1 for _ in csv.reader(fh)) > minimum


@pytest.mark.parametrize("title,countries,on_list,sponsor,expected_tier", [
    ("Senior Application Security Engineer", {"GB"}, True, {"uk": SponsorTag("yes", "X")}, 1),  # 4+1+2+1+1
    ("Penetration Tester", {"NL"}, True, {}, 1),                                                # 4+2+1
    ("Security Engineer", {"DE"}, True, {}, 2),                                                 # 1+1+1
    ("Junior Pentester", {"SE"}, False, {}, 2),                                                 # 4-2+1
    ("Threat Modeling Lead", {"IE"}, False, {}, 1),                                             # 4+1+2
])
def test_tiering(title, countries, on_list, sponsor, expected_tier):
    total, reasons = score(title, countries, on_list, sponsor)
    assert tier(total) == expected_tier, (total, reasons)


def test_sponsor_bonus_only_counts_for_the_postings_country():
    uk_yes = {"uk": SponsorTag("yes", "X"), "nl": SponsorTag("no")}
    assert score("Pentester", {"GB"}, False, uk_yes)[0] == score("Pentester", {"GB"}, False, {})[0] + 1
    assert score("Pentester", {"DE"}, False, uk_yes)[0] == score("Pentester", {"DE"}, False, {})[0]


def test_digest_tiers_and_sponsor_notes():
    def P(title, company, countries, url):
        return Posting(source="ats", company=company, title=title, location="", countries=frozenset(countries),
                       url=url, company_canonical=company)
    groups = group_postings([P("Senior AppSec Engineer", "Adyen", {"NL"}, "u1"),
                             P("Security Engineer", "Monzo", {"DE"}, "u2")])
    radar.enrich(groups, sponsors=Sponsors(UK, NL))
    d = radar.render_digest("2026-09-28", False, groups, [], [], __import__("collections").Counter())
    t1, t2 = d.index("## Tier 1"), d.index("## Tier 2")
    assert t1 < d.index("### Adyen") < t2 < d.index("### Monzo")
    assert "NL sponsor: yes (Adyen N.V.)" in d
    assert "UK sponsor" not in d  # neither posting is in GB


def test_curated_target_name_beats_vague_source_name():
    uk = Register(["STARLING BANK LIMITED", "STARLING GROUP LTD"])
    s = Sponsors(uk, NL)
    # the ATS reports just "Starling"; "Group" is stripped, so "Starling" alone would hit the wrong firm
    assert s.tag("Starling", "Starling Bank")["uk"].matched == "STARLING BANK LIMITED"
