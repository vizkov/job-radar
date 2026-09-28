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

from jobradar.board import enqueue, load_queue, payload, role_ref, save_queue, select_for_board, stale_refs
from jobradar.common import CONFIG, ROOT, target_countries, title_matches
from jobradar.dedupe import Group, group_postings
from jobradar.health import BROKEN_AFTER_RUNS, update_health
from jobradar.matching import default_matcher
from jobradar.mdsafe import md, md_url  # noqa: F401 (tests use radar.md)
from jobradar.model import Posting, SourceResult
from jobradar.sources import build_sources, load_sources_config, run_sources
from jobradar.tiering import score as fit_score, tier as fit_tier

STATE, DIGESTS, DATA = ROOT / "state", ROOT / "digests", ROOT / "data"


def load(p: Path, default):
    return json.loads(p.read_text()) if p.exists() else default


def select(results: list[SourceResult], include_outside, matcher=None) -> tuple[list[Posting], Counter]:
    """Country + title filter, then company matching. Returns kept postings and per-source match counts.
    include_outside: bool for all sources, or {source: bool}."""
    matcher = matcher or default_matcher()
    tgt = target_countries() | {"REMOTE-EU"}
    kept, matched = [], Counter()
    for res in results:
        outside_ok = include_outside.get(res.source, False) if isinstance(include_outside, dict) else include_outside
        for p in res.postings:
            countries = p.countries & tgt
            # a hash-watched careers page has no job titles to filter; its change notice always passes
            if not countries or not (p.raw.get("page_changed") or title_matches(p.title)):
                continue
            p.countries = frozenset(countries)
            p.company_canonical = matcher.resolve(p.company, p.company_hint)
            if p.company_canonical is None and not outside_ok:
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
        total, reasons = fit_score(p.title, p.countries, bool(p.company_canonical), sp, age_days=age)
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

    lines += ["## Sources", "", "| Source | Status | Units erroring | Raw results | Matches | Time |",
              "|---|---|---|---|---|---|"]
    for r in results:
        bad = sum(1 for u in r.units if not u.ok)
        raw = sum(u.raw_count for u in r.units)
        status = "ok" if r.ok else f"FAILED: {r.error[:80]}"
        lines.append(f"| {r.source} | {status} | {bad}/{len(r.units)} | {raw} | {matched[r.source]} | {r.seconds:.0f}s |")
    return "\n".join(lines) + "\n"


def render_status(today, baseline, new: list[Group], broken, results: list[SourceResult],
                  matched: Counter, queued: int) -> str:
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
             "external_id": g.best.external_id} for g in new]
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
    kept, matched = select(results, outside)
    new = diff_seen(group_postings(kept), seen, today)
    enrich(new)
    broken = update_health(health, results)
    digest = render_digest(today, baseline, new, broken, results, matched)

    board_groups = select_for_board(new, CONFIG.get("board", {}), baseline)
    queue = enqueue(load_queue(STATE / "board_queue.json"), [payload(g) for g in board_groups])
    status_md = render_status(today, baseline, new, broken, results, matched, len(queue))
    summary = (f"{len(new)} new roles, {len(board_groups)} for the board, {len(broken)} silent sources, "
               + ", ".join(f"{r.source}={'ok' if r.ok else 'FAILED'}" for r in results))
    if args.dry_run:
        print(summary if args.quiet else digest)
        print(f"[dry-run] {len(new)} new, nothing written.")
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

    print(summary if args.quiet else digest)
    if gh := os.environ.get("GITHUB_OUTPUT"):
        with open(gh, "a") as fh:
            fh.write(f"new_count={len(new)}\nbroken_count={len(broken)}\nboard_queued={len(queue)}\n")


if __name__ == "__main__":
    main()
