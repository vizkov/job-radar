"""Match employer names from any source back to targets.tsv (profile/ or examples/).

Deliberately exact: a posting's company is normalized (case, accents, punctuation,
legal suffixes like Ltd/LLP/GmbH/B.V., regional qualifiers like "UK"/"NL"/"Cyber")
and looked up in an index built from targets.tsv plus aliases.csv. No fuzzy
matching here — "Secura" vs "Securam" style false positives would put strangers
in the digest. Add missing spellings to aliases.csv instead.
"""
from __future__ import annotations

import csv
import re
import unicodedata
from functools import lru_cache
from pathlib import Path

from jobradar.paths import profile_path

_LEGAL = {"ltd", "limited", "llp", "plc", "inc", "llc", "gmbh", "ag", "bv", "nv", "sa", "sas", "se",
          "ab", "as", "asa", "oy", "oyj", "kg", "co", "corp", "corporation", "holding", "holdings",
          "group", "ua", "srl", "spa", "sarl", "pty", "mbh", "the"}
# Words that only say which branch of a target this is. Stripped so "Deloitte UK Cyber",
# "Deloitte NL" and "Deloitte LLP" all fold into one company.
_QUALIFIERS = {"uk", "nl", "ie", "ch", "de", "se", "cyber", "ireland", "germany", "deutschland",
               "netherlands", "nederland", "switzerland", "schweiz", "sweden", "emea", "europe",
               "international", "global"}


def normalize(name: str) -> str:
    """Comparable key: 'Pen Test Partners LLP' -> 'pentestpartners'."""
    return normalize_words(name).replace(" ", "")


def normalize_words(name: str) -> str:
    """Same as normalize() but keeps word boundaries: 'Pen Test Partners LLP' -> 'pen test partners'."""
    s = unicodedata.normalize("NFKD", name or "").encode("ascii", "ignore").decode().lower()
    s = re.sub(r"\([^)]*\)", " ", s)
    s = s.replace("&", " and ")
    s = re.sub(r"\bb\.v\.|\bn\.v\.|\bs\.a\.", lambda m: m.group(0).replace(".", ""), s)
    words = re.findall(r"[a-z0-9]+", s)
    kept = [w for w in words if w not in _LEGAL]
    stripped = [w for w in kept if w not in _QUALIFIERS]
    return " ".join(stripped or kept or words)


def _display(target: str) -> str:
    """Canonical display name: 'Deloitte UK Cyber' -> 'Deloitte', 'Fox-IT / NCC Group' -> 'Fox-IT'."""
    first = re.sub(r"\([^)]*\)", "", target.split(" / ")[0]).strip()
    words = [w for w in first.split() if w.lower() not in _QUALIFIERS] or first.split()
    return " ".join(words)


class CompanyMatcher:
    def __init__(self, targets: list[str], aliases: list[tuple[str, str]]):
        self.index: dict[str, str] = {}
        for t in targets:
            disp = _display(t)
            for part in [t, *t.split(" / ")]:
                self.index.setdefault(normalize(part), disp)
        for alias, canonical in aliases:
            # aliases may point at a target name or a display name, but only at a real
            # target: an alias to a company you don't track must not put it on your list
            target_disp = self.index.get(normalize(canonical))
            if target_disp is None:
                continue
            self.index[normalize(alias)] = target_disp
        self.index.pop("", None)
        self.canonicals = set(self.index.values())

    def match(self, name: str) -> str | None:
        return self.index.get(normalize(name))

    def resolve(self, company: str, hints: tuple[str, ...] = ()) -> str | None:
        """Canonical name for a posting. The source's own company field wins when it
        matches a target; otherwise fall back to what the source knows (the verified
        board's target list)."""
        return self.match(company) or next((m for h in hints if (m := self.match(h))), None)


def load_targets(path: Path | None = None) -> list[str]:
    path = path or profile_path("targets.tsv")
    with open(path, encoding="utf-8") as fh:
        return [r["Company"].strip() for r in csv.DictReader(fh, delimiter="\t") if r.get("Company")]


def load_high_fit(path: Path | None = None) -> set[str]:
    """Normalised names of the targets.tsv companies whose Fit column is High (empty when there is no Fit column)."""
    path = path or profile_path("targets.tsv")
    with open(path, encoding="utf-8") as fh:
        return {normalize(r["Company"]) for r in csv.DictReader(fh, delimiter="	")
                if r.get("Company") and (r.get("Fit") or "").strip().lower() == "high"}


def load_aliases(path: Path | None = None) -> list[tuple[str, str]]:
    path = path or profile_path("aliases.csv")
    if not path.exists():
        return []
    with open(path, encoding="utf-8") as fh:
        rows = csv.DictReader(line for line in fh if not line.lstrip().startswith("#"))
        return [(r["alias"].strip(), r["canonical"].strip()) for r in rows if r.get("alias") and r.get("canonical")]


@lru_cache(maxsize=1)
def default_matcher() -> CompanyMatcher:
    return CompanyMatcher(load_targets(), load_aliases())
