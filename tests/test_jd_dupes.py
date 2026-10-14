import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import jd_dupes  # noqa: E402

AD = " ".join(f"Sentence number {i} covers alpha beta gamma delta epsilon topic." for i in range(40))


def test_same_ad_under_a_different_title_is_same():
    assert jd_dupes.compare("Sr Security Engineer. " + AD, "Sr Product Security Engineer. " + AD + " Extra boilerplate line here.")["verdict"] == "same"


def test_a_different_role_sharing_boilerplate_is_not_same():
    other = " ".join(f"Different line {i} covers omega sigma tau upsilon phi subject." for i in range(40))
    c = jd_dupes.compare(AD[:600] + " " + other, AD)
    assert c["verdict"] != "same"


def test_a_short_snippet_is_never_same():
    snippet = "Senior Security Engineer. Remote. Threat modelling and risk assessment of real systems for the product."
    assert jd_dupes.compare(snippet, snippet + " " + AD)["verdict"] != "same"


def test_differing_sentences_are_reported_so_the_verdict_can_be_checked():
    c = jd_dupes.compare(AD + " Nice to have: Kubernetes and sandboxing experience across multi-tenant clusters.", AD)
    assert any("Kubernetes" in s for s in c["only_in_longer"])
