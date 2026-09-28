import pytest

from jobradar.matching import CompanyMatcher, default_matcher, normalize


@pytest.fixture(scope="module")
def m():
    return default_matcher()  # examples/targets.tsv + examples/aliases.csv


@pytest.mark.parametrize("raw,canonical", [
    ("Deloitte LLP", "Deloitte"),
    ("Deloitte UK", "Deloitte"),
    ("Deloitte Netherlands B.V.", "Deloitte"),
    ("Pen Test Partners LLP", "Pen Test Partners"),
    ("MDSec Ltd", "MDSec"),
    ("SySS GmbH", "SySS"),
    ("NCC Group plc", "NCC Group"),
    ("Fox-IT", "Fox-IT"),
    ("PricewaterhouseCoopers", "PwC"),
    ("Ernst & Young", "EY"),
    ("Amazon Web Services", "Amazon"),
    ("AWS", "Amazon"),
    ("J.P. Morgan", "JPMorgan Chase"),
    ("goldmansachs", "Goldman Sachs"),
    ("Checkpoint", "Check Point"),
    ("Zürich Insurance Company Ltd", "Zurich Insurance"),
    ("ASML Netherlands B.V.", "ASML"),
    ("GitHub", "GitHub"),
])
def test_alias_and_normalization(m, raw, canonical):
    assert m.match(raw) == canonical


@pytest.mark.parametrize("raw", ["Securam GmbH", "Random Staffing Agency GmbH", "Deloitte Touche Tohmatsu Fake Co X", ""])
def test_no_fuzzy_matches(m, raw):
    assert m.match(raw) is None


def test_resolve_prefers_company_field_then_hints():
    m = CompanyMatcher(["NCC Group", "Fox-IT / NCC Group"], [])
    assert m.resolve("Fox-IT B.V.", ("NCC Group",)) == "Fox-IT"      # own field wins
    assert m.resolve("NCC Group Security Services Ltd", ("Fox-IT / NCC Group",)) == "Fox-IT"  # falls back to board
    assert m.resolve("Unknown", ()) is None


def test_normalize():
    assert normalize("Pen Test Partners LLP") == "pentestpartners"
    assert normalize("Context Information Security (Accenture)") == "contextinformationsecurity"
    assert normalize("UK") == "uk"  # a name made only of qualifiers is kept
