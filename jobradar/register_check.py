"""Roles held back only because the sponsor register has no entry under the employer's name. STANDARD LIBRARY ONLY.

The registers list legal names, so "not found" means "unknown", not "not a sponsor" (the user, 2026-11-26: an employer can be
registered under another company name). Instead of dropping such a role, the daily run writes it to state/register_check.csv
(written by the run only). Claude finds the legal name on the company's own pages and records the answer in
profile/sponsor_names.csv (`tools/register_check.py`), which jobradar/sponsors.py also reads, so each company is looked up once.
"""
from __future__ import annotations

import csv
import json
from datetime import date, timedelta
from pathlib import Path

from jobradar.matching import normalize
from jobradar.paths import profile_path

ROOT = Path(__file__).resolve().parent.parent
HOLDS = ROOT / "state" / "register_check.csv"
ISSUE_MAP = ROOT / "state" / "issue_map.json"
QUEUE = ROOT / "state" / "board_queue.json"
HOLD_FIELDS = ["ref", "found", "posted", "company", "country", "title", "url", "register"]
NAME_FIELDS = ["company", "country", "legal_name", "evidence", "checked"]   # empty legal_name: checked, not on the register
COUNTRY_KEY = {"GB": "uk", "NL": "nl"}


def names_path() -> Path:
    return profile_path("sponsor_names.csv")


def _read(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with open(path, encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def _write(path: Path, fields: list[str], rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fields, extrasaction="ignore", lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


def decided(names: Path | None = None) -> dict[tuple[str, str], str]:
    """(normalised company, "uk"/"nl") -> legal register name, or "" when the lookup found none."""
    return {(normalize(r["company"]), r["country"]): (r.get("legal_name") or "").strip()
            for r in _read(names or names_path()) if r.get("company") and r.get("country")}


def record(company: str, country: str, legal_name: str, evidence: str, today: str, names: Path | None = None) -> None:
    """Save one lookup's answer, replacing an earlier one for the same company and country."""
    path = names or names_path()
    rows = [r for r in _read(path) if (normalize(r["company"]), r["country"]) != (normalize(company), country)]
    rows.append({"company": company, "country": country, "legal_name": legal_name, "evidence": evidence, "checked": today})
    _write(path, NAME_FIELDS, rows)


def _fresh(row: dict, today: str, keep_days: int) -> bool:
    cutoff = (date.fromisoformat(today) - timedelta(days=keep_days)).isoformat()
    return (row.get("posted") or row.get("found") or "") > cutoff


def add_holds(rows: list[dict], today: str, keep_days: int = 30, holds: Path = HOLDS) -> int:
    """Merge new held roles into the file and drop those past the board rule's age limit. Returns the rows kept."""
    old = {r["ref"]: r for r in _read(holds)}
    for r in rows:
        old.setdefault(r["ref"], r)
    kept = sorted((r for r in old.values() if _fresh(r, today, keep_days)),
                  key=lambda r: (r["found"], r["company"]), reverse=True)
    if kept or holds.exists():
        _write(holds, HOLD_FIELDS, kept)
    return len(kept)


def pending(today: str, keep_days: int = 30, holds: Path = HOLDS, names: Path | None = None,
            issue_map: Path = ISSUE_MAP, queue: Path = QUEUE) -> list[dict]:
    """Held roles still waiting for a lookup: not answered, not carded or queued since, not too old."""
    done = decided(names)
    carded = set(json.loads(issue_map.read_text(encoding="utf-8"))) if issue_map.exists() else set()
    if queue.exists():
        carded |= {q["ref"] for q in json.loads(queue.read_text(encoding="utf-8"))}
    return [r for r in _read(holds) if r["ref"] not in carded and _fresh(r, today, keep_days)
            and (normalize(r["company"]), COUNTRY_KEY.get(r["country"], "")) not in done]
