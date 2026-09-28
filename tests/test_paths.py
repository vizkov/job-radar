from jobradar import paths
from jobradar.matching import CompanyMatcher


def test_profile_file_wins_over_example(tmp_path, monkeypatch):
    (tmp_path / "config.json").write_text("{}")
    monkeypatch.setenv("JOBRADAR_PROFILE", str(tmp_path))
    assert paths.profile_path("config.json") == tmp_path / "config.json"
    assert paths.profile_path("targets.tsv") == paths.EXAMPLES / "targets.tsv"  # missing -> example


def test_examples_ship_every_profile_file():
    for name in paths.PROFILE_FILES:
        assert (paths.EXAMPLES / name).exists(), name


def test_alias_to_untracked_company_is_ignored():
    m = CompanyMatcher(["Deloitte UK Cyber"], [("Citigroup", "Citi"), ("Deloitte LLP", "Deloitte UK Cyber")])
    assert m.match("Citigroup") is None          # Citi isn't a target: stays off your list
    assert m.match("Deloitte LLP") == "Deloitte"
