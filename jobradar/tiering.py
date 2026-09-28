"""Rule-based fit score (no LLM). Rules live in config.json under "tiering".

score = best-matching title keyword weight
      + every matching seniority word
      + best target-country weight
      + on_target_list bonus (employer is in targets.tsv)
      + sponsor_yes bonus (licensed sponsor in the posting's UK/NL country)
      + fresh_bonus when the role was posted within fresh_days
Tier 1 when score >= tier1_min_score, else Tier 2.
"""
from __future__ import annotations

from jobradar.common import CONFIG, keyword_re

_CFG = CONFIG.get("tiering", {})
_TITLE = [(keyword_re([k]), w) for k, w in (_CFG.get("title_keywords") or {}).items()]
_SENIORITY = [(keyword_re([k]), w) for k, w in (_CFG.get("seniority_keywords") or {}).items()]


def score(title: str, countries, on_list: bool, sponsor: dict | None = None,
          age_days: int | None = None) -> tuple[int, list[str]]:
    """Returns (score, reasons); reasons go to data/matches.csv to make tuning debuggable."""
    reasons, total = [], 0
    t = max(((w, rx.pattern) for rx, w in _TITLE if rx.search(title or "")), default=(0, ""))
    total += t[0]
    if t[1]:
        reasons.append(f"title+{t[0]}")
    for rx, w in _SENIORITY:
        if rx.search(title or ""):
            total += w
            reasons.append(f"seniority{w:+d}")
    c = max((_CFG.get("country", {}).get(x, 0) for x in countries), default=0)
    total += c
    reasons.append(f"country+{c}")
    if on_list:
        total += _CFG.get("on_target_list", 0)
        reasons.append("on-list")
    sponsor = sponsor or {}
    relevant = []
    if "GB" in countries:
        relevant.append(sponsor.get("uk"))
    if "NL" in countries:
        relevant.append(sponsor.get("nl"))
    if any(getattr(s, "status", "") == "yes" for s in relevant):
        total += _CFG.get("sponsor_yes", 0)
        reasons.append("sponsor")
    # fresher listings get a nudge: applying in the first few days matters
    if age_days is not None and age_days <= _CFG.get("fresh_days", 3):
        total += _CFG.get("fresh_bonus", 0)
        reasons.append("fresh")
    return total, reasons


def tier(total: int) -> int:
    return 1 if total >= _CFG.get("tier1_min_score", 6) else 2
