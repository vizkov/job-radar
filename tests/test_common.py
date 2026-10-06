

def test_prague_and_brno_are_czechia():
    from jobradar.common import countries_for
    assert countries_for(None, "Prague, Czech Republic") == {"CZ"} and countries_for(None, "Brno") == {"CZ"}
