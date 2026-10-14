

def test_recommendation_cannot_exceed_the_fit_band():
    from jd_check import recommendation_cap
    assert recommendation_cap(72, 0) == "apply" and recommendation_cap(69, 0) == "maybe" and recommendation_cap(49, 0) == "skip"
    assert recommendation_cap(80, 1) == "skip"
    assert recommendation_cap(70, 0, "unlikely") == "maybe" and recommendation_cap(70, 0, "no") == "skip"
