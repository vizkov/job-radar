"""Daily poller: run every enabled source (sources.yaml), keep matching roles in
target countries, match employers to your targets.tsv, collapse cross-source
duplicates, and report only postings not seen before.

Writes (not with --dry-run):
  digests/YYYY-MM-DD.md   human-readable digest (also copied to digests/latest.md)
  digests/status.md       counts + source health, posted as the "Radar status" issue
  state/board_queue.json  new roles waiting to become board cards (tools/board_sync.py roles)
  data/matches.csv        running log of every match ever surfaced
  state/seen.json         posting IDs already reported (pruned after 120 days)
  state/health.json       per-unit result counts, to catch sources that silently break

Usage:
  python radar.py                              # normal run
  python radar.py --dry-run --source ats       # one source, live, no state/digest writes
  python radar.py --quiet                      # counts only on stdout (used in CI)
"""
from __future__ import annotations

import argparse
import asyncio
import csv
import json
import os
import re
import sys
from collections import Counter, defaultdict
from datetime import date, timedelta
from pathlib import Path

from jobradar import register_check
from jobradar.board import (enqueue, load_queue, payload, register_holds, role_ref, save_queue, select_for_board,
                            stale_refs)
from jobradar.common import CONFIG, ROOT, not_permanent, target_countries, title_matches
from jobradar.dedupe import Group, group_postings
from jobradar.health import BROKEN_AFTER_RUNS, update_health
from functools import lru_cache

from jobradar.matching import default_matcher, load_high_fit, load_sectors, normalize
from jobradar.mdsafe import md, md_url  # noqa: F401 (tests use radar.md)
from jobradar.model import Posting, SourceResult
from jobradar.sources import build_sources, load_sources_config, run_sources
from jobradar.tiering import score as fit_score, tier as fit_tier

STATE, DIGESTS, DATA = ROOT / "state", ROOT / "digests", ROOT / "data"


def load(p: Path, default):
    return json.loads(p.read_text()) if p.exists() else default


UNRECOGNISED: defaultdict = defaultdict(list)  # source -> sample locations (title matched, no country found)
UNRECOGNISED_N: Counter = Counter()  # source -> how many title-matching listings that cost
DROP_REASONS = {"country": "outside your countries", "title": "titles not matching",
                "employment": "not permanent", "old": "posted too long ago",
                "company": "employers not on your list"}
# Dropped listings of these sources are kept in state/dropped_alerts.csv, so the filters can be audited (main() turns it on;
# jobradar/intake.py and tests never do). Alert emails only: the ATS sources drop 100k+ listings a run.
LOG_DROPS_SOURCES = {"alert_email"}
LOG_DROPS = False
DROPPED_ROWS: list[dict] = []
DROPPED_FIELDS = ["first_seen", "last_seen", "company", "title", "location", "reasons", "source", "url"]


def _log_drop(res, p, matcher, tgt, first: str) -> None:
    """Record a dropped listing with every filter it fails, not only the first (select() stops at the first)."""
    reasons = [first]
    if first != "country" and not (p.countries & tgt):
        reasons.append("country")
    if first != "title" and not (p.raw.get("page_changed") or title_matches(p.title)):
        reasons.append("title")
    if first != "company" and matcher.resolve(p.company, p.company_hint) is None:
        reasons.append("company")
    if first != "employment" and (not_permanent(p.title) or not_permanent(p.raw.get("employment", ""))):
        reasons.append("employment")
    max_age = int(CONFIG.get("max_age_days") or 0)
    if first != "old" and max_age and p.posted_at and (date.today() - p.posted_at.date()).days > max_age:
        reasons.append("old")
    DROPPED_ROWS.append({"company": p.company or "", "title": p.title or "", "location": p.location or "",
                         "reasons": ",".join(reasons), "source": res.source, "url": p.url or ""})


def select(results: list[SourceResult], include_outside, matcher=None,
           dropped: Counter | None = None, skip: frozenset | set = frozenset()) -> tuple[list[Posting], Counter]:
    """Country + title filter, then company matching. Returns kept postings and per-source match counts.
    include_outside: bool for all sources, or {source: bool}. `dropped`, if given, counts why each
    listing was dropped, keyed (source, reason) with reasons from DROP_REASONS. `skip`: reasons not to filter on (jobradar/intake.py,
    for a role added by hand that the user agreed to bring in despite that filter; the daily run never passes it)."""
    dropped = dropped if dropped is not None else Counter()
    matcher = matcher or default_matcher()
    tgt = target_countries() | {"REMOTE-EU"}
    kept, matched = [], Counter()
    for res in results:
        outside_ok = include_outside.get(res.source, False) if isinstance(include_outside, dict) else include_outside
        for p in res.postings:
            countries = p.countries & tgt
            if not countries and "country" in skip:
                countries = set(p.countries)
            if not countries:
                dropped[(res.source, "country")] += 1
                if LOG_DROPS and res.source in LOG_DROPS_SOURCES:
                    _log_drop(res, p, matcher, tgt, "country")
                dropped[(res.source, "where:" + (",".join(sorted(p.countries)) or "location not recognised"))] += 1
                # only roles you'd want can be real losses: count and sample those, for the digest
                if not p.countries and title_matches(p.title):
                    UNRECOGNISED_N[res.source] += 1
                    sample = p.location or "(empty)"
                    if len(UNRECOGNISED[res.source]) < 30 and sample not in UNRECOGNISED[res.source]:
                        UNRECOGNISED[res.source].append(sample)
                continue
            # a hash-watched careers page has no job titles to filter; its change notice always passes
            if "title" not in skip and not (p.raw.get("page_changed") or title_matches(p.title)):
                dropped[(res.source, "title")] += 1
                if LOG_DROPS and res.source in LOG_DROPS_SOURCES:
                    _log_drop(res, p, matcher, tgt, "title")
                continue
            if "employment" not in skip and (not_permanent(p.title) or not_permanent(p.raw.get("employment", ""))):
                dropped[(res.source, "employment")] += 1
                if LOG_DROPS and res.source in LOG_DROPS_SOURCES:
                    _log_drop(res, p, matcher, tgt, "employment")
                continue  # permanent roles only (config.json: employment_exclude)
            max_age = int(CONFIG.get("max_age_days") or 0)  # 0 = no limit; roles with no posted date always pass
            if "old" not in skip and max_age and p.posted_at and (date.today() - p.posted_at.date()).days > max_age:
                dropped[(res.source, "old")] += 1
                if LOG_DROPS and res.source in LOG_DROPS_SOURCES:
                    _log_drop(res, p, matcher, tgt, "old")
                continue  # posted more than max_age_days ago (config.json: max_age_days)
            p.countries = frozenset(countries)
            p.company_canonical = matcher.resolve(p.company, p.company_hint)
            if p.company_canonical is None and not outside_ok and "company" not in skip:
                dropped[(res.source, "company")] += 1
                if LOG_DROPS and res.source in LOG_DROPS_SOURCES:
                    _log_drop(res, p, matcher, tgt, "company")
                continue
            kept.append(p)
            matched[res.source] += 1
    return kept, matched


def diff_seen(groups: list[Group], seen: dict, today: str) -> list[Group]:
    """Groups with no ID and no content key seen before. Marks all of them seen."""
    new = []
    for g in groups:
        keys = {p.id_key for p in g.postings} | {g.key}
        if not any(k in seen for k in keys):
            new.append(g)
        for k in keys:
            seen[k] = today  # last-seen date; pruning uses this
    return new


def follow_retitles(groups: list[Group], unseen: set[str], seen: dict, rows: list[dict], carded: set[str],
                    today: str) -> list[Group]:
    """A listing keeps its ID when its title (or country) changes, so diff_seen calls it already reported. For a group whose
    posting ID is on an earlier matches.csv row under another ref:
    - that earlier role has a card (or one queued): keep it marked as seen, so it isn't labelled possibly-closed; no new card;
    - otherwise, the first time the new title appears (its key is in `unseen`): return the group, to be recorded and
      considered for the board like any new role (the user, 2026-11-26: a "Lead" role retitled "Senior" vanished).
    Mutates `seen`."""
    by_id: dict[tuple[str, str], set[str]] = {}
    for row in rows:
        if row.get("external_id"):
            by_id.setdefault((row.get("source") or "", row["external_id"]), set()).add(row["ref"])
    keys_of: dict[str, str] = {}
    out = []
    for g in groups:
        earlier = set().union(*(by_id.get((p.source, p.external_id), set()) for p in g.postings)) - {role_ref(g.key)}
        if not earlier:
            continue
        if earlier & carded:
            keys_of = keys_of or {role_ref(k): k for k in seen if k.startswith("c:")}
            for ref in earlier & carded:
                if ref in keys_of:
                    seen[keys_of[ref]] = today
        elif g.key in unseen:
            out.append(g)
    return out


def read_matches_rows(path) -> list[dict]:
    if not path.exists():
        return []
    with open(path, encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


@lru_cache(maxsize=1)
def high_fit_targets() -> frozenset:
    """Companies marked Fit = High in targets.tsv (read once per run)."""
    try:
        return frozenset(load_high_fit())
    except OSError:
        return frozenset()


@lru_cache(maxsize=1)
def sector_targets() -> dict:
    """Sector tags per company from targets.tsv (read once per run; empty without a Sector column)."""
    try:
        return load_sectors()
    except OSError:
        return {}


def enrich(new: list[Group], sponsors=None) -> None:
    """Sponsor-register tags and fit tier for each new group (after dedupe, so only a few lookups)."""
    if not new:
        return
    if sponsors is None:
        from jobradar.sponsors import default_sponsors  # loads ~135k register rows; only when needed
        sponsors = default_sponsors()
    for g in new:
        p = g.best
        sp = sponsors.tag(p.company, p.company_canonical)
        age = (date.today() - p.posted_at.date()).days if p.posted_at else None
        high = bool(p.company_canonical) and normalize(p.company_canonical) in high_fit_targets()
        total, reasons = fit_score(p.title, p.countries, bool(p.company_canonical), sp, age_days=age, high_fit=high,
                                   sectors=sector_targets().get(normalize(p.company_canonical or ""), frozenset()))
        g.tags = {"sponsor": sp, "score": total, "tier": fit_tier(total), "reasons": reasons}


def _sponsor_note(g: Group) -> str:
    sp, parts = g.tags.get("sponsor") or {}, []
    for cc, key, label in (("GB", "uk", "UK sponsor"), ("NL", "nl", "NL sponsor")):
        if cc in g.best.countries and key in sp:
            parts.append(f"{label}: {md(str(sp[key]))}")
    return (" · " + " · ".join(parts)) if parts else ""


def _line(g: Group) -> str:
    p = g.best
    posted = f" · posted {p.posted_at.date().isoformat()}" if p.posted_at else ""
    also = ""
    if g.also:
        also = " · also on " + ", ".join(f"[{a.source}]({md_url(a.url)})" for a in g.also[:3])
    where = md(p.location) or ",".join(sorted(p.countries))
    return f"- [{md(p.title)}]({md_url(p.url)}) — {where}{posted}{_sponsor_note(g)}{also}"


def _by_score(groups):
    return sorted(groups, key=lambda g: (-g.tags.get("score", 0), g.best.title))


def render_digest(today, baseline, new: list[Group], broken, results: list[SourceResult], matched: Counter) -> str:
    listed = [g for g in new if g.best.company_canonical]
    outside = [g for g in new if not g.best.company_canonical]
    companies = {g.best.company_canonical for g in listed}
    lines = [f"# Job radar — {today}", ""]
    if baseline:
        lines += [f"**First run (baseline):** {len(new)} matching roles currently open. "
                  "From tomorrow, only new postings are listed.", ""]
    else:
        lines += [f"**{len(listed)} new matching roles** across {len(companies)} companies"
                  + (f", plus {len(outside)} outside your list" if outside else "") + ".", ""]

    for t, heading in ((1, "## Tier 1 — strongest fit"), (2, "## Tier 2")):
        tier_groups = [g for g in listed if g.tags.get("tier", 2) == t]
        if not tier_groups:
            continue
        lines += [heading, ""]
        by_co = defaultdict(list)
        for g in tier_groups:
            by_co[g.best.company_canonical].append(g)
        # companies with the best-scoring role first
        for company in sorted(by_co, key=lambda c: (-max(g.tags.get("score", 0) for g in by_co[c]), c.lower())):
            lines.append(f"### {md(company)}")
            lines += [_line(g) for g in _by_score(by_co[company])]
            lines.append("")

    if outside:
        lines += ["## Outside your list", "Employers not in your targets.tsv. Add real ones there, "
                  "or a spelling to aliases.csv.", ""]
        by_co = defaultdict(list)
        for g in outside:
            by_co[g.best.company or "(employer not disclosed)"].append(g)
        for company in sorted(by_co, key=lambda c: (-max(g.tags.get("score", 0) for g in by_co[c]), c.lower())):
            lines.append(f"**{md(company)}**")
            lines += [_line(g) for g in _by_score(by_co[company])]
        lines.append("")

    if broken:
        lines += ["## ⚠️ Sources that stopped returning results",
                  f"These used to return results and have been empty or erroring for {BROKEN_AFTER_RUNS}+ runs. "
                  "For ATS boards the company may have moved ATS — re-run verify_boards.py.", ""]
        lines += [f"- **{src}** — {md(label)} ({md(why[:120])})" for src, label, why in broken]
        lines.append("")

    if UNRECOGNISED:
        lines += ["## Locations not recognised (title matches)", "Listings with a matching title dropped because no "
                  "country was found in the location: possible real losses. Add missing places to "
                  "`jobradar/common.py`.", ""]
        lines += [f"- **{src}** ({UNRECOGNISED_N[src]} listings): " + "; ".join(md(x) for x in samples)
                  for src, samples in UNRECOGNISED.items()]
        lines.append("")
    lines += ["## Sources", "", "| Source | Status | Units erroring | Raw results | Matches | Time |",
              "|---|---|---|---|---|---|"]
    for r in results:
        bad = sum(1 for u in r.units if not u.ok)
        raw = sum(u.raw_count for u in r.units)
        status = "ok" if r.ok else f"FAILED: {r.error[:80]}"
        lines.append(f"| {r.source} | {status} | {bad}/{len(r.units)} | {raw} | {matched[r.source]} | {r.seconds:.0f}s |")
    return "\n".join(lines) + "\n"


def drop_lines(results: list[SourceResult], matched: Counter, dropped: Counter) -> list[str]:
    """One line per source that found listings: how many, why they were dropped, how many kept."""
    out = []
    for r in results:
        found = len(r.postings)
        if not found:
            continue
        why = [f"{dropped[(r.source, k)]} {label}" for k, label in DROP_REASONS.items() if dropped[(r.source, k)]]
        where = sorted(((n, k[1][6:]) for k, n in dropped.items() if k[0] == r.source and k[1].startswith("where:")),
                       reverse=True)[:3]
        if where and why:
            why[0] += " (" + ", ".join(f"{place} {n}" for n, place in where) + ")"
        out.append(f"- **{r.source}**: {found} found" + (" → " + " · ".join(why) if why else "")
                   + f" · **{matched[r.source]} kept**")
    return out


def render_status(today, baseline, new: list[Group], broken, results: list[SourceResult],
                  matched: Counter, queued: int, dropped: Counter | None = None) -> str:
    """Body of the single "Radar status" issue: counts and health, no job titles."""
    on_list = [g for g in new if g.best.company_canonical]
    t1 = sum(1 for g in on_list if g.tags.get("tier") == 1)
    lines = [f"**Last run:** {today}", ""]
    if baseline:
        lines += [f"**First run (baseline):** {len(new)} open roles recorded in `data/matches.csv` "
                  f"({t1} Tier 1 on your list go to the board). From tomorrow only new roles appear.", ""]
    else:
        lines += [f"**New today:** {len(on_list)} on your list (Tier 1: {t1}, Tier 2: {len(on_list) - t1}), "
                  f"{len(new) - len(on_list)} outside it.", ""]
    lines.append(f"**Waiting to be added to the board:** {queued}")
    lines.append("")
    if broken:
        lines += ["### ⚠️ Sources that stopped returning results", ""]
        lines += [f"- **{src}** — {md(label)} ({md(why[:120])})" for src, label, why in broken]
        lines.append("")
    lines += ["### Sources", "", "| Source | Status | Units erroring | Raw results | Matches | Time |",
              "|---|---|---|---|---|---|"]
    for r in results:
        bad = sum(1 for u in r.units if not u.ok)
        raw = sum(u.raw_count for u in r.units)
        status = "ok" if r.ok else f"FAILED: {md(r.error[:80])}"
        lines.append(f"| {r.source} | {status} | {bad}/{len(r.units)} | {raw} | {matched[r.source]} | {r.seconds:.0f}s |")
    if dropped is not None and (dl := drop_lines(results, matched, dropped)):
        lines += ["", "### What each source found, and why listings were dropped", "", *dl]
    lines += ["", "_Ask Claude for a briefing; open the Project board to track applications._"]
    return "\n".join(lines) + "\n"


def append_matches(new: list[Group], today: str):
    rows = [{"ref": role_ref(g.key), "date": today, "company": g.best.company_canonical or g.best.company, "title": g.best.title,
             "location": g.best.location, "countries": ",".join(sorted(g.best.countries)),
             "url": g.best.url, "source": g.best.source,
             "posted": g.best.posted_at.date().isoformat() if g.best.posted_at else "",
             "on_list": "yes" if g.best.company_canonical else "no",
             "tier": g.tags.get("tier", ""), "score": g.tags.get("score", ""),
             "score_reasons": " ".join(g.tags.get("reasons", [])),
             "uk_sponsor": str((g.tags.get("sponsor") or {}).get("uk", "")),
             "nl_sponsor": str((g.tags.get("sponsor") or {}).get("nl", "")),
             "also_on": " ".join(a.url for a in g.also),
             # what tools/jd_prep.py needs to fetch the full description via the ATS scraper
             "ats": g.best.raw.get("ats", ""), "ats_slug": g.best.raw.get("slug", ""),
             "external_id": g.best.external_id,
             # how the role arrived: blank for the daily run; "manual" or "manual-override:<reasons>" from jobradar/intake.py
             "origin": g.best.raw.get("origin", ""),
             **g.best.raw.get("row_extra", {})} for g in new]
    if not rows:
        return
    log = DATA / "matches.csv"
    fields = list(rows[0].keys())
    if log.exists():
        with open(log, newline="", encoding="utf-8") as fh:
            reader = csv.DictReader(fh)
            old_fields, old_rows = list(reader.fieldnames or []), list(reader)
        if old_fields != fields:  # columns changed between versions: rewrite once with the union
            merged = old_fields + [f for f in fields if f not in old_fields]
            with open(log, "w", newline="", encoding="utf-8") as fh:
                w = csv.DictWriter(fh, fieldnames=merged, restval="")
                w.writeheader()
                w.writerows(old_rows)
            fields = merged
    else:
        with open(log, "w", newline="", encoding="utf-8") as fh:
            csv.DictWriter(fh, fieldnames=fields).writeheader()
    with open(log, "a", newline="", encoding="utf-8") as fh:
        csv.DictWriter(fh, fieldnames=fields, restval="").writerows(rows)


def write_dropped_log(today: str, keep_days: int = 45) -> int:
    """Merge this run's dropped alert listings into state/dropped_alerts.csv (first/last seen; old rows expire). Returns rows kept."""
    path = STATE / "dropped_alerts.csv"
    old: dict[tuple, dict] = {}
    if path.exists():
        with open(path, newline="", encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                old[(r["company"].lower(), r["title"].lower(), r["location"].lower())] = r
    for r in DROPPED_ROWS:
        k = (r["company"].lower(), r["title"].lower(), r["location"].lower())
        if k in old:
            old[k].update(last_seen=today, reasons=r["reasons"], url=r["url"] or old[k]["url"])
        else:
            old[k] = {"first_seen": today, "last_seen": today, **r}
    cutoff = (date.fromisoformat(today) - timedelta(days=keep_days)).isoformat()
    rows = sorted((r for r in old.values() if r["last_seen"] >= cutoff), key=lambda r: (r["last_seen"], r["company"]), reverse=True)
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=DROPPED_FIELDS, restval="", extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    return len(rows)


ALERT_HIT_FIELDS = ["first_seen", "last_seen", "alert", "company", "title", "location"]


def write_alert_hits(results, today: str, keep_days: int = 45) -> int:
    """Log which LinkedIn alert (search name) listed each role, kept or dropped, in state/alert_hits.csv, so a
    search (for example a fintech one) can be judged by the roles only it surfaces. Mails without a search name
    (single-job alerts) are logged as '(single-job mail)'. Returns rows kept."""
    path = STATE / "alert_hits.csv"
    old: dict[tuple, dict] = {}
    if path.exists():
        with open(path, newline="", encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                old[(r["alert"], r["company"].lower(), r["title"].lower(), r["location"].lower())] = r
    for res in results:
        for p in res.postings:
            if p.source != "linkedin_email":
                continue
            alert = (p.raw or {}).get("alert") or "(single-job mail)"
            k = (alert, p.company.lower(), p.title.lower(), p.location.lower())
            if k in old:
                old[k]["last_seen"] = today
            else:
                old[k] = {"first_seen": today, "last_seen": today, "alert": alert, "company": p.company,
                          "title": p.title, "location": p.location}
    cutoff = (date.fromisoformat(today) - timedelta(days=keep_days)).isoformat()
    rows = sorted((r for r in old.values() if r["last_seen"] >= cutoff),
                  key=lambda r: (r["last_seen"], r["alert"]), reverse=True)
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=ALERT_HIT_FIELDS, restval="", extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    return len(rows)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true", help="fetch and print the digest; write nothing")
    ap.add_argument("--source", help="run only this source (even if disabled in sources.yaml)")
    ap.add_argument("--quiet", action="store_true",
                    help="don't print the digest (CI logs are public on public repos); print counts only")
    ap.add_argument("--include-outside", action="store_true",
                    help="also list employers not in targets.tsv (overrides sources.yaml for this run)")
    args = ap.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")  # Windows consoles default to cp1252

    scfg = load_sources_config()
    sources = build_sources(scfg, only=args.source)
    seen: dict = load(STATE / "seen.json", {})
    health: dict = load(STATE / "health.json", {})
    baseline = not seen
    today = date.today().isoformat()

    results = asyncio.run(run_sources(sources))
    default_outside = args.include_outside or bool(scfg.get("include_outside_list", False))
    outside = {name: args.include_outside or bool((c or {}).get("include_outside_list", default_outside))
               for name, c in (scfg.get("sources") or {}).items()}
    dropped: Counter = Counter()
    global LOG_DROPS
    LOG_DROPS = True
    kept, matched = select(results, outside, dropped=dropped)
    LOG_DROPS = False
    groups = group_postings(kept)
    unseen = {g.key for g in groups if g.key not in seen}
    new = diff_seen(groups, seen, today)
    carded = set(load(STATE / "issue_map.json", {})) | {q["ref"] for q in load_queue(STATE / "board_queue.json")}
    fresh = {g.key for g in new}
    new += follow_retitles([g for g in groups if g.key not in fresh], unseen, seen,
                           read_matches_rows(DATA / "matches.csv"), carded, today)
    enrich(new)
    broken = update_health(health, results)
    digest = render_digest(today, baseline, new, broken, results, matched)

    board_groups = select_for_board(new, CONFIG.get("board", {}), baseline)
    queue = enqueue(load_queue(STATE / "board_queue.json"), [payload(g) for g in board_groups])
    held = register_holds(new, CONFIG.get("board", {}), baseline, today)
    status_md = render_status(today, baseline, new, broken, results, matched, len(queue), dropped)
    summary = (f"{len(new)} new roles, {len(board_groups)} for the board, {len(broken)} silent sources, "
               + ", ".join(f"{r.source}={'ok' if r.ok else 'FAILED'}" for r in results))
    if args.dry_run:
        print(summary if args.quiet else digest)
        print(f"[dry-run] {len(new)} new, nothing written; {len(DROPPED_ROWS)} dropped alert listings would be logged.")
        return

    cutoff = (date.today() - timedelta(days=120)).isoformat()
    seen = {k: v for k, v in seen.items() if v >= cutoff}
    DIGESTS.mkdir(exist_ok=True); STATE.mkdir(exist_ok=True)
    (DIGESTS / f"{today}.md").write_text(digest, encoding="utf-8")
    (DIGESTS / "latest.md").write_text(digest, encoding="utf-8")
    (DIGESTS / "status.md").write_text(status_md, encoding="utf-8")
    save_queue(STATE / "board_queue.json", queue)
    # Roles on the board that no source has listed for a while are probably closed. Skipped on
    # runs where a source failed or many units errored, so an outage can't "close" everything.
    issue_map = load(STATE / "issue_map.json", {})
    units = [u for r in results for u in r.units]
    healthy = all(r.ok for r in results) and sum(not u.ok for u in units) <= max(3, len(units) // 10)
    if issue_map and healthy and not args.source:
        stale, alive = stale_refs(issue_map, seen, today, int(CONFIG.get("board", {}).get("stale_days", 5)))
        (STATE / "stale_roles.json").write_text(json.dumps({"stale": stale, "alive": alive}, indent=1))
    (STATE / "seen.json").write_text(json.dumps(seen, indent=0, sort_keys=True))
    (STATE / "health.json").write_text(json.dumps(health, indent=0, sort_keys=True))
    append_matches(new, today)
    write_dropped_log(today)
    write_alert_hits(results, today)
    keep = int((CONFIG.get("board", {}).get("outside_tier1") or {}).get("max_age_days") or 30)
    register_check.add_holds(held, today, keep, STATE / "register_check.csv")

    print(summary if args.quiet else digest)
    if gh := os.environ.get("GITHUB_OUTPUT"):
        with open(gh, "a") as fh:
            fh.write(f"new_count={len(new)}\nbroken_count={len(broken)}\nboard_queued={len(queue)}\n")


if __name__ == "__main__":
    main()
