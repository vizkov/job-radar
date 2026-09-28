"""'Went silent' detection for every source.

Each thing a source polls (ATS board, search query, careers page) is a unit with a
streak counter. A unit is bad on a run when it errors or returns zero raw results
(before title filtering — a search that matched no AppSec roles today is fine, a
search that returned nothing at all is not). After BROKEN_AFTER_RUNS bad runs in a
row, a unit that has worked before is reported. A whole-source failure (crash or
timeout) is tracked as unit "*" and reported even if the source never worked.
"""
from __future__ import annotations

from jobradar.model import SourceResult, UnitStatus

BROKEN_AFTER_RUNS = 2


def update_health(health: dict, results: list[SourceResult]) -> list[tuple[str, str, str]]:
    """Mutates `health`; returns (source, unit label, reason) for units that went silent."""
    broken = []
    for res in results:
        whole = f"{res.source}|*"
        if res.ok:
            units = res.units
            if whole in health:
                health[whole]["bad_streak"] = 0
        else:
            prefix = f"{res.source}|"
            units = [UnitStatus(k[len(prefix):], ok=False, error=res.error, label=v.get("label", ""))
                     for k, v in health.items() if k.startswith(prefix) and k != whole]
            units.append(UnitStatus("*", ok=False, error=res.error, label=f"{res.source} (whole source)"))
        for u in units:
            h = health.setdefault(f"{res.source}|{u.key}", {"last_ok_count": 0, "bad_streak": 0})
            if u.label:
                h["label"] = u.label
            if u.ok and (u.raw_count > 0 or not u.track_empty):
                h["last_ok_count"], h["bad_streak"] = max(u.raw_count, 1), 0
                continue
            h["bad_streak"] += 1
            if h["bad_streak"] >= BROKEN_AFTER_RUNS and (h["last_ok_count"] > 0 or u.key == "*"):
                broken.append((res.source, h.get("label") or u.key, u.error or "returned 0 results"))
    return broken
