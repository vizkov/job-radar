"""Collapse the same role seen on several sources into one digest entry.

Key = company + normalized title + primary country. City is left out on purpose:
sources spell locations differently ("London, England, GB" vs "London" vs EURES
region codes), and a consultancy advertising one role for London and Manchester
is one thing to apply to. The cost: two distinct openings with identical titles
in the same country at the same company show up once.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from jobradar.common import CONFIG
from jobradar.matching import normalize
from jobradar.model import Posting

# Canonical apply link comes from the most authoritative source present.
SOURCE_RANK = {"ats": 0, "careers_page": 1, "bundesagentur": 2, "jobtech": 2, "reed": 3, "eures": 3,
               "linkedin_email": 4, "indeed_email": 4, "glassdoor_email": 4}

_GENDER = re.compile(r"\(\s*[mwfdx]{1,2}\s*(?:/\s*[mwfdx*]{1,2}\s*){1,3}\)|\b[mwfd]/[mwfd]/[mwfdx]\b", re.I)


def norm_title(title: str) -> str:
    t = _GENDER.sub(" ", title or "")
    return "".join(ch for ch in t.lower() if ch.isalnum())


def primary_country(countries) -> str:
    order = list(CONFIG["priority_countries"]) + list(CONFIG["extra_countries"]) + ["REMOTE-EU"]
    for c in order:
        if c in countries:
            return c
    return min(countries) if countries else ""


def content_key(p: Posting) -> str:
    company = normalize(p.company_canonical or p.company)
    if not company:  # anonymised employer (common on EURES NL): never merge with other listings
        return f"c:?{p.id_key}"
    return f"c:{company}|{norm_title(p.title)}|{primary_country(p.countries)}"


@dataclass
class Group:
    key: str
    postings: list[Posting] = field(default_factory=list)
    tags: dict = field(default_factory=dict)   # enrichment: sponsor, score, tier (new groups only)

    @property
    def best(self) -> Posting:
        return min(self.postings, key=lambda p: SOURCE_RANK.get(p.source, 9))

    @property
    def also(self) -> list[Posting]:
        best = self.best
        seen, out = {best.url}, []
        for p in sorted(self.postings, key=lambda p: SOURCE_RANK.get(p.source, 9)):
            if p.url not in seen:
                seen.add(p.url); out.append(p)
        return out


def group_postings(postings: list[Posting]) -> list[Group]:
    groups: dict[str, Group] = {}
    for p in postings:
        k = content_key(p)
        groups.setdefault(k, Group(k)).postings.append(p)
    return list(groups.values())
