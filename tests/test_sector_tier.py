from jobradar import matching, tiering


def test_load_sectors_reads_optional_column(tmp_path):
    p = tmp_path / "targets.tsv"
    p.write_text("Company\tOffices\tFit\tSector\nAdyen\tAmsterdam\tHigh\tFintech, Payments\nCisco\tLondon\tHigh\t\n", encoding="utf-8")
    assert matching.load_sectors(p) == {matching.normalize("Adyen"): frozenset({"fintech", "payments"})}


def test_load_sectors_without_column_is_empty(tmp_path):
    p = tmp_path / "targets.tsv"
    p.write_text("Company\tOffices\nAdyen\tAmsterdam\n", encoding="utf-8")
    assert matching.load_sectors(p) == {}


def test_sector_bonus_applies_once_and_only_to_listed_employers(monkeypatch):
    monkeypatch.setitem(tiering._CFG, "sector_bonus", {"fintech": 1, "banking": 1})
    base, _ = tiering.score("Security Engineer", ["NL"], True)
    both, reasons = tiering.score("Security Engineer", ["NL"], True, sectors=frozenset({"fintech", "banking"}))
    assert both == base + 1 and any(r.startswith("sector:") for r in reasons)
    off_list, _ = tiering.score("Security Engineer", ["NL"], False, sectors=frozenset({"fintech"}))
    assert off_list == tiering.score("Security Engineer", ["NL"], False)[0]


def test_no_sector_bonus_configured_changes_nothing(monkeypatch):
    monkeypatch.setitem(tiering._CFG, "sector_bonus", {})
    assert tiering.score("Security Engineer", ["NL"], True, sectors=frozenset({"fintech"})) == tiering.score("Security Engineer", ["NL"], True)
