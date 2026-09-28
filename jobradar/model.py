"""Normalized posting model and the Source protocol every adapter implements."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Protocol


@dataclass
class Posting:
    source: str                      # adapter name, e.g. "ats", "bundesagentur"
    company: str                     # employer name as the source gave it
    title: str
    location: str
    countries: frozenset[str]
    url: str
    external_id: str = ""            # stable per-source ID; falls back to url
    posted_at: datetime | None = None
    raw: dict = field(default_factory=dict)
    company_hint: tuple[str, ...] = ()   # target names the source already knows (ATS boards)
    company_canonical: str | None = None  # set by matching; None = not on the target list

    @property
    def id_key(self) -> str:
        return f"{self.source}:{self.external_id or self.url}"


@dataclass
class UnitStatus:
    """Health of one thing a source polls (a board, a search query, a careers page)."""
    key: str
    ok: bool
    raw_count: int = 0               # results before title/country filtering
    error: str = ""
    label: str = ""                  # human-readable name for the digest
    track_empty: bool = True         # False: zero results is normal (narrow search query), only errors count


@dataclass
class SourceResult:
    source: str
    ok: bool = True
    error: str = ""
    postings: list[Posting] = field(default_factory=list)
    units: list[UnitStatus] = field(default_factory=list)
    seconds: float = 0.0


class Source(Protocol):
    name: str
    timeout: float                   # whole-source cap, enforced by the registry

    async def fetch(self) -> SourceResult: ...
