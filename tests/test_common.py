

def test_prague_and_brno_are_czechia():
    from jobradar.common import countries_for
    assert countries_for(None, "Prague, Czech Republic") == {"CZ"} and countries_for(None, "Brno") == {"CZ"}


def test_places_seen_dropped_as_unrecognised_now_resolve_to_their_country():
    from jobradar.common import countries_for
    assert countries_for(None, "Barendrecht") == {"NL"}
    assert countries_for(None, "Driebergen-Rijsenburg") == {"NL"}
    assert countries_for(None, "Worcestershire") == {"GB"}
    assert countries_for(None, "East Lothian") == {"GB"}
    assert countries_for(None, "Katowice") == set()   # Poland is outside the user's countries: still not a target
