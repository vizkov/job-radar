"""One door for roles that arrive by hand (a URL the user pastes, a LinkedIn hiring post): the same filters and bookkeeping as the daily run.

The daily run does: sources -> select() (country, title, permanent-only, max_age_days, employer list) -> dedupe + seen.json ->
enrich() (sponsor register tags, tier, score) -> data/matches.csv -> board queue. A role added by hand used to skip all of that
(2026-10-07: two Anthropic roles posted 89 and 623 days earlier went onto the board although max_age_days is 30).
`admit()` runs a Posting through the very same functions. A filter that would drop the role is reported, never silently
skipped: the role goes in only when the caller names the reason in `override` (the user's word), and the matches.csv
`origin` column records it ("manual-override:age,country").
"""
from __future__ import annotations

import json
import re
from collections import Counter
from datetime import date

from jobradar.model import Posting, SourceResult


def _load(path, default):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default


def admit(p: Posting, override: frozenset[str] | set[str] = frozenset(), dry_run: bool = False, baseline: bool = False) -> dict:
    """Run one posting through the radar's pipeline. Returns {"status": "added"|"dropped"|"known", "ref", "reasons", ...}.
    override: DROP_REASONS keys ("country", "title", "employment", "old", "company") the user agreed to bypass for this role."""
    import radar
    from jobradar.board import enqueue, load_queue, payload, role_ref, save_queue, select_for_board
    from jobradar.common import CONFIG
    from jobradar.dedupe import group_postings
    from jobradar.matching import default_matcher
    from jobradar.sources import load_sources_config

    scfg = load_sources_config()
    default_outside = bool(scfg.get("include_outside_list", False))
    outside = bool(((scfg.get("sources") or {}).get(p.source) or {}).get("include_outside_list", default_outside))
    original_countries = frozenset(p.countries)
    found: list[str] = []                      # every filter that would drop the role, one pass per filter (select() stops at the first)
    skip: set[str] = set()                     # filters already found to trigger: bypassed so the later ones are tested too
    for _ in range(len(radar.DROP_REASONS) + 1):
        dropped: Counter = Counter()
        kept, _m = radar.select([SourceResult(p.source, postings=[p])], outside, dropped=dropped, skip=skip)
        new_reasons = sorted({r for (_, r), _n in dropped.items() if r in radar.DROP_REASONS} - skip)
        if kept or not new_reasons:
            break
        found += new_reasons
        skip |= set(new_reasons)
    blocking = [r for r in found if r not in set(override)]
    if blocking:
        return {"status": "dropped", "reasons": blocking, "ref": "", "why": [radar.DROP_REASONS[r] for r in blocking]}
    if "country" in skip:
        p.countries = original_countries       # select() narrows countries only when it keeps the role on the real ones
    if not p.company_canonical:
        p.company_canonical = default_matcher().resolve(p.company, p.company_hint)
    reasons = sorted(set(found))
    p.raw["origin"] = "manual-override:" + ",".join(reasons) if reasons else "manual"
    today = date.today().isoformat()
    seen = _load(radar.STATE / "seen.json", {})
    groups = group_postings([p])
    new = radar.diff_seen(groups, seen, today)
    if not new:
        return {"status": "known", "reasons": reasons, "ref": role_ref(groups[0].key)}
    radar.enrich(new)
    g = new[0]
    ref = role_ref(g.key)
    carded = bool(select_for_board(new, CONFIG.get("board", {}), baseline))
    out = {"status": "added", "ref": ref, "reasons": reasons, "tier": g.tags.get("tier"), "score": g.tags.get("score"),
           "carded": carded, "overridden": reasons}
    if dry_run:
        out["dry_run"] = True
        return out
    radar.STATE.mkdir(exist_ok=True)
    (radar.STATE / "seen.json").write_text(json.dumps(seen, indent=0, sort_keys=True))
    radar.append_matches(new, today)
    if carded:
        queue = enqueue(load_queue(radar.STATE / "board_queue.json"), [payload(g)])
        save_queue(radar.STATE / "board_queue.json", queue)
    return out


_GH = re.compile(r"greenhouse\.io/(?:embed/job_app\?for=)?([A-Za-z0-9_-]+)/jobs/(\d+)")
_LEVER = re.compile(r"jobs\.lever\.co/([A-Za-z0-9_-]+)/([0-9a-f-]{36})")
_ASHBY = re.compile(r"jobs\.ashbyhq\.com/([A-Za-z0-9_.-]+)/([0-9a-f-]{36})")


def parse_job_url(url: str) -> tuple[str, str, str] | None:
    """(ats, board slug, job id) for a Greenhouse, Lever or Ashby job link; None for anything else."""
    for ats, rx in (("greenhouse", _GH), ("lever", _LEVER), ("ashby", _ASHBY)):
        if m := rx.search(url):
            return ats, m.group(1), m.group(2)
    return None


async def fetch_posting(url: str) -> Posting | None:
    """The role as the daily run would see it: the company's whole board through ats-scrapers, then the one posting."""
    import json as _json
    from jobradar.common import ROOT, fetch_many
    from jobradar.sources.ats import job_to_posting
    hit = parse_job_url(url)
    if not hit:
        return None
    ats, slug, jid = hit
    boards = _json.loads((ROOT / "boards.json").read_text(encoding="utf-8")) if (ROOT / "boards.json").exists() else []
    board = next((b for b in boards if b["ats"] == ats and b["slug"].lower() == slug.lower()), None)
    if board is None:
        board = {"companies": [slug.replace("-", " ").title()], "ats": ats, "slug": slug, "url": f"{ats}:{slug}"}
    res = (await fetch_many([(board["ats"], board["slug"], board["url"])], progress=False))[board["url"]]
    for job in res.jobs:
        if jid in str(job.url) or jid in str(getattr(job, "global_id", "")):
            return job_to_posting(job, board)
    return None


def manual_posting(url: str, company: str, title: str, location: str = "", posted: str = "", countries: str = "") -> Posting:
    """A posting built from fields the user gave (a link the ATS fetch cannot read: LinkedIn, a company site, a pasted ad).
    Countries default to what the radar would read from the location text."""
    from datetime import datetime
    from jobradar.common import countries_for
    cc = {c.strip().upper() for c in countries.split(",") if c.strip()} or countries_for(None, location)
    return Posting(source="manual", company=company.strip(), title=title.strip(), location=location.strip(), countries=frozenset(cc),
                   url=url, external_id=url, posted_at=datetime.fromisoformat(posted) if posted else None)
