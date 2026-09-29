import pytest

from jobradar.common import countries_for


@pytest.mark.parametrize("iso,loc,expected", [
    (None, "London, England, United Kingdom", {"GB"}),
    (None, "Amsterdam", {"NL"}),
    (None, "Dublin, Ireland", {"IE"}),
    (None, "Belfast, Northern Ireland", {"GB"}),          # not IE
    (None, "Zürich", {"CH"}),
    (None, "Berlin, DE", {"DE"}),                         # DE is not read as Delaware
    (None, "London; Amsterdam", {"GB", "NL"}),
    (None, "Remote - EMEA", {"REMOTE-EU"}),
    # US/Canada false positives the old substring matcher produced
    (None, "Cambridge, MA", {"OUTSIDE-EUROPE"}),   # never GB, never a target
    (None, "Durham, NC, United States", {"US"}),   # named, never a target
    (None, "Reading, PA", {"OUTSIDE-EUROPE"}),
    (None, "London, ON, Canada", {"CA"}),          # not GB: the city is ignored outside Europe
    ("US", "Cambridge, MA", {"US"}),
    ("US", "Cambridge", {"US"}),                          # non-European ISO beats the text
    # substring false positives
    (None, "Corktown, Detroit", set()),
    (None, "Hibernia Street", set()),
    # European ISO is extended by text for multi-location postings
    ("GB", "London; Amsterdam", {"GB", "NL"}),
    ("UK", "Manchester", {"GB"}),
])
def test_countries(iso, loc, expected):
    assert countries_for(iso, loc) == expected


@pytest.mark.parametrize("loc,expected", [
    ("Sydney, New South Wales, AUS", {"OUTSIDE-EUROPE"}),   # seen live on an Amazon board
    ("Cardiff, Wales, United Kingdom", {"GB"}),
    ("London, England, GBR", {"GB"}),
    ("Dublin, IRL", {"IE"}),
    ("Frankfurt, DEU", {"DE"}),
])
def test_live_regressions(loc, expected):
    assert countries_for(None, loc) == expected


@pytest.mark.parametrize("loc,want", [
    ("Harrow", {"GB"}), ("Frimley", {"GB"}), ("Milton Keynes", {"GB"}), ("Neath", {"GB"}),
    ("'s-Hertogenbosch", {"NL"}), ("Lüneburg, NDS, de", {"DE"}), ("Zug, ch", {"CH"}),
    # same-name places abroad stay abroad
    ("Portsmouth, NH", {"OUTSIDE-EUROPE"}), ("Newcastle, NSW", {"OUTSIDE-EUROPE"}), ("New York, NY", {"OUTSIDE-EUROPE"}),
])
def test_towns_and_trailing_country_codes(loc, want):
    assert countries_for(None, loc) == want
