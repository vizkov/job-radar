"""Visa-sponsorship signal from the UK and Dutch public sponsor registers.

For a posting's employer, look it up in data/registers/{uk,nl}_sponsors.csv
(refreshed weekly by tools/refresh_registers.py) and return:

  yes      exact normalized match, a prefix match ("Adyen" -> "ADYEN N.V. LONDON
           BRANCH"), or a very close fuzzy match
  unknown  a plausible but uncertain fuzzy match, or no employer name
  no       nothing close in the register

The matched register name is always returned so you can sanity-check it: a
licensed sponsor under a different legal entity (parent/subsidiary) shows as
"no" here even though the group sponsors visas. sponsor_overrides.csv (profile/) pins
a company to a register name (or to "no") when the automatic match is wrong.
"""
from __future__ import annotations

import bisect
import csv
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from rapidfuzz import fuzz, process

from jobradar.common import CONFIG, ROOT
from jobradar.matching import normalize, normalize_words
from jobradar.paths import profile_path

REG_DIR = ROOT / "data" / "registers"
MIN_PREFIX = 4  # "ing" must not prefix-match "ingenieursbureau"


@dataclass(frozen=True)
class SponsorTag:
    status: str          # yes / no / unknown
    matched: str = ""    # register name the decision is based on
    how: str = ""        # exact / prefix / fuzzy:<score> / override

    def __str__(self):
        return f"{self.status} ({self.matched})" if self.matched else self.status


class Register:
    def __init__(self, names: list[str]):
        self.by_key: dict[str, str] = {}      # "adyenlondonbranch" -> register name
        by_words: dict[str, str] = {}         # "adyen london branch" -> register name
        for n in names:
            w = normalize_words(n)
            k = w.replace(" ", "")
            if k and (k not in self.by_key or len(n) < len(self.by_key[k])):
                self.by_key[k] = n
            if w and (w not in by_words or len(n) < len(by_words[w])):
                by_words[w] = n
        self.keys = sorted(self.by_key)
        self.words = sorted(by_words)
        self.by_words = by_words
        cfg = CONFIG.get("sponsorship", {})
        self.yes_score = cfg.get("fuzzy_yes", 94)
        self.unknown_score = cfg.get("fuzzy_unknown", 86)

    def lookup(self, company: str) -> SponsorTag:
        k = normalize(company)
        if not k:
            return SponsorTag("unknown")
        if k in self.by_key:
            return SponsorTag("yes", self.by_key[k], "exact")
        if len(k) >= MIN_PREFIX:
            # whole-word prefix: "adyen" -> "adyen london branch", but "amazon" !-> "amazonico"
            w = normalize_words(company) + " "
            i = bisect.bisect_left(self.words, w)
            hits = [self.words[j] for j in range(i, min(i + 50, len(self.words))) if self.words[j].startswith(w)]
            if len(hits) == 1:
                return SponsorTag("yes", self.by_words[hits[0]], "prefix")
            if hits:  # "Amazon" -> Amazon Filters Ltd, Amazon UK Services Ltd, …: can't tell which
                names = sorted((self.by_words[h] for h in hits), key=len)
                more = f" +{len(names) - 2} more" if len(names) > 2 else ""
                return SponsorTag("unknown", " / ".join(names[:2]) + more, f"prefix:{len(names)} entities")
        best = process.extractOne(k, self.keys, scorer=fuzz.ratio, score_cutoff=self.unknown_score)
        if best:
            name, score = self.by_key[best[0]], round(best[1])
            return SponsorTag("yes" if score >= self.yes_score else "unknown", name, f"fuzzy:{score}")
        return SponsorTag("no")


def _load_names(path: Path) -> list[str]:
    if not path.exists():
        return []
    with open(path, encoding="utf-8") as fh:
        return [r["name"] for r in csv.DictReader(fh)]


def _load_overrides(path: Path | None = None) -> dict[str, dict[str, str]]:
    path = path or profile_path("sponsor_overrides.csv")
    if not path.exists():
        return {}
    with open(path, encoding="utf-8") as fh:
        rows = csv.DictReader(line for line in fh if not line.lstrip().startswith("#"))
        return {normalize(r["company"]): {"uk": (r.get("uk") or "").strip(), "nl": (r.get("nl") or "").strip()}
                for r in rows if r.get("company")}


class Sponsors:
    def __init__(self, uk: Register, nl: Register, overrides: dict | None = None):
        self.registers = {"uk": uk, "nl": nl}
        self.overrides = overrides or {}

    def tag(self, company: str, canonical: str | None = None) -> dict[str, SponsorTag]:
        out = {}
        for country, reg in self.registers.items():
            if not reg.keys:
                out[country] = SponsorTag("unknown", how="register missing")
                continue
            pinned = next((self.overrides[k][country] for k in (normalize(company), normalize(canonical or ""))
                           if k in self.overrides and self.overrides[k][country]), None)
            if pinned:
                out[country] = SponsorTag("no", how="override") if pinned.lower() == "no" \
                    else SponsorTag("yes", pinned, "override")
                continue
            # The targets.tsv name is curated and usually more specific than what a source
            # reports ("Starling Bank" vs "Starling", which would hit an unrelated
            # STARLING GROUP LTD), so try it first and fall back to the raw employer name.
            first, second = (canonical, company) if canonical else (company, None)
            tag = reg.lookup(first)
            if tag.status != "yes" and second and normalize(second) != normalize(first):
                alt = reg.lookup(second)
                if alt.status == "yes" or tag.status == "no":
                    tag = alt
            out[country] = tag
        return out


@lru_cache(maxsize=1)
def default_sponsors() -> Sponsors:
    return Sponsors(Register(_load_names(REG_DIR / "uk_sponsors.csv")),
                    Register(_load_names(REG_DIR / "nl_sponsors.csv")), _load_overrides())
