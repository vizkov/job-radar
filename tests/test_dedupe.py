from jobradar.dedupe import group_postings, norm_title
from jobradar.model import Posting


def P(source, company, title, loc, countries, url, canonical=None):
    return Posting(source=source, company=company, title=title, location=loc,
                   countries=frozenset(countries), url=url, company_canonical=canonical)


def test_gender_suffixes_stripped():
    assert norm_title("AppSec Engineer (m/w/d)") == norm_title("AppSec Engineer (f/m/x)") == norm_title("AppSec Engineer")


def test_same_role_across_sources_collapses_and_prefers_ats():
    ps = [
        P("linkedin_email", "Deloitte LLP", "Application Security Engineer", "London", {"GB"},
          "https://www.linkedin.com/jobs/view/1/", "Deloitte"),
        P("ats", "Deloitte", "Application Security Engineer", "London, England, United Kingdom", {"GB"},
          "https://deloitte.wd3.myworkdayjobs.com/x/1", "Deloitte"),
        P("eures", "DELOITTE UK", "Application Security Engineer (m/w/d)", "UKI", {"GB"},
          "https://europa.eu/eures/1", "Deloitte"),
    ]
    groups = group_postings(ps)
    assert len(groups) == 1
    g = groups[0]
    assert g.best.source == "ats"
    assert [a.source for a in g.also] == ["eures", "linkedin_email"]


def test_different_country_or_title_stays_separate():
    ps = [
        P("ats", "X", "Security Consultant", "London", {"GB"}, "u1", "X"),
        P("ats", "X", "Security Consultant", "Amsterdam", {"NL"}, "u2", "X"),
        P("ats", "X", "Senior Security Consultant", "London", {"GB"}, "u3", "X"),
    ]
    assert len(group_postings(ps)) == 3


def test_outside_list_uses_raw_company():
    ps = [P("eures", "Acme GmbH", "Pentester", "Berlin", {"DE"}, "u1"),
          P("bundesagentur", "ACME", "Pentester", "Berlin", {"DE"}, "u2")]
    assert len(group_postings(ps)) == 1


def test_anonymous_employers_never_merge():
    ps = [P("eures", "", "Security Engineer", "NL", {"NL"}, "u1"),
          P("eures", "", "Security Engineer", "NL", {"NL"}, "u2")]
    ps[0].external_id, ps[1].external_id = "a", "b"
    assert len(group_postings(ps)) == 2
