"""One-time (or monthly) live check of every candidate board.

For each company in data/candidates.csv, fetch every candidate board and keep
the ones that actually list jobs in your target countries. That weeds out
dead boards (company moved ATS), wrong entities (a US company with the same
name), and wrong regional tenants.

Also reads overrides.csv (profile/) (company,careers_url) so you can add boards for
companies the mapping missed — paste their careers page URL and the ATS is
detected automatically (Greenhouse, Lever, Ashby, Workday, SmartRecruiters…).

profile/board_blocklist.csv (ats,slug,board_url,reason) lists boards to never poll, such as a placeholder
board that shows fake jobs in your countries and so passes the check above.

Outputs:
  data/verified_boards.csv   one row per board: jobs total / in target countries
  data/coverage_report.csv   one row per company: final status + kept boards
  boards.json                what radar.py polls daily
"""
from __future__ import annotations

import argparse
import asyncio
import csv
import json
from collections import Counter, defaultdict

from ats_scrapers import resolve_careers_url

from jobradar.common import ROOT, all_europe, fetch_many, job_countries, target_countries, title_matches
from jobradar.paths import profile_path

DATA = ROOT / "data"


def load_blocklist() -> tuple[set, set]:
    """profile/board_blocklist.csv (ats,slug,reason  and/or  board_url,reason): boards to never poll, e.g. a
    placeholder board that lists fake jobs. Returns ({(ats, slug)}, {board_url}), lower-cased."""
    path = profile_path("board_blocklist.csv")
    pairs, urls = set(), set()
    if path.exists():
        for r in csv.DictReader(open(path, encoding="utf-8")):
            ats, slug = (r.get("ats") or "").strip().lower(), (r.get("slug") or "").strip().lower()
            url = (r.get("board_url") or "").strip().lower().rstrip("/")
            if ats and slug:
                pairs.add((ats, slug))
            if url:
                urls.add(url)
    return pairs, urls


def load_candidates():
    rows = list(csv.DictReader(open(DATA / "candidates.csv", encoding="utf-8")))
    ov = profile_path("overrides.csv")
    if ov.exists():
        for r in csv.DictReader(open(ov, encoding="utf-8")):
            url = (r.get("careers_url") or "").strip()
            company = (r.get("company") or "").strip()
            # optional explicit ats/slug columns, for boards the URL detector doesn't recognise
            # (and for boards found by tools/discover_boards.py, which have no careers URL)
            ats, slug = (r.get("ats") or "").strip(), (r.get("slug") or "").strip()
            if not company or not (url or (ats and slug)):
                continue
            url = url or f"{ats}:{slug}"
            if not (ats and slug):
                resolved = resolve_careers_url(url)
                if not resolved:
                    print(f"! override for {company}: can't detect ATS from {url} "
                          "(custom careers site; set the ats and slug columns if you know them)")
                    continue
                ats = resolved.ats.value if hasattr(resolved.ats, "value") else str(resolved.ats)
                slug = url if ats in ("workday", "phenom", "oracle") else resolved.slug
            rows = [x for x in rows if not (x["company"] == company and not x["board_url"])]
            rows.append({"company": company, "offices": "", "status": "override", "source": "override",
                         "ats": ats, "scraper_slug": slug, "board_url": url, "board_name": company})
    pairs, urls = load_blocklist()
    return [r for r in rows if (r["ats"].lower(), r["scraper_slug"].lower()) not in pairs
            and (r["board_url"] or "").lower().rstrip("/") not in urls]


def careers_page_companies() -> set[str]:
    """Lower-cased companies with an enabled entry in careers_pages.yaml (covered without an ATS board)."""
    import yaml
    path = profile_path("careers_pages.yaml")
    pages = yaml.safe_load(path.read_text(encoding="utf-8")) if path.exists() else None
    return {p["company"].lower() for p in pages or [] if p.get("company") and p.get("enabled", True)}


def main(argv=None):
    ap = argparse.ArgumentParser(description="Live check of every candidate ATS board; writes boards.json.")
    ap.add_argument("--quiet", action="store_true", help="no per-board lines (they name your target companies)")
    args = ap.parse_args(argv)
    rows = load_candidates()
    boards = {}
    for r in rows:
        if r["board_url"]:
            boards.setdefault(r["board_url"], (r["ats"], r["scraper_slug"], r["board_url"]))
    print(f"Fetching {len(boards)} boards for {len({r['company'] for r in rows})} companies…")
    results = asyncio.run(fetch_many(list(boards.values()), progress=not args.quiet))

    tgt, eur = target_countries() | {"REMOTE-EU"}, all_europe() | {"REMOTE-EU"}
    board_stats = {}
    for url, res in results.items():
        in_tgt = [j for j in res.jobs if job_countries(j) & tgt]
        cc = Counter(c for j in res.jobs for c in job_countries(j))
        board_stats[url] = {
            "ats": res.ats, "board_url": url, "ok": res.ok, "error": res.error,
            "jobs_total": len(res.jobs),
            "jobs_target_countries": len(in_tgt),
            "jobs_europe": sum(1 for j in res.jobs if job_countries(j) & eur),
            "relevant_now": sum(1 for j in in_tgt if title_matches(j.title or "")),
            "top_countries": ", ".join(f"{c}:{n}" for c, n in cc.most_common(5)),
        }
    with open(DATA / "verified_boards.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(next(iter(board_stats.values())).keys()))
        w.writeheader(); w.writerows(board_stats.values())

    by_company = defaultdict(list)
    for r in rows:
        by_company[r["company"]].append(r)

    report, keep = [], defaultdict(set)
    watched = careers_page_companies()
    for company, rs in by_company.items():
        stats = [board_stats[r["board_url"]] for r in rs if r["board_url"] in board_stats]
        kept = [s for s in stats if s["jobs_target_countries"] > 0]
        if kept:
            status = "VERIFIED"
        elif any(s["ok"] and s["jobs_total"] > 0 for s in stats):
            status = "no jobs in target countries (wrong entity or not hiring in Europe)"
        elif any(s["ok"] for s in stats):
            status = "boards empty (stale / moved ATS)"
        elif stats:
            status = "fetch error"
        else:
            status = "not covered - add careers URL to profile/overrides.csv"
        if status != "VERIFIED" and company.lower() in watched:
            status = "careers page (profile/careers_pages.yaml)"  # the careers_page source covers it
        for s in kept:
            keep[s["board_url"]].add(company)
        report.append({
            "company": company, "offices": rs[0].get("offices", ""), "status": status,
            "kept_boards": " | ".join(f"{s['ats']}: {s['board_url']}" for s in kept),
            "jobs_in_target_countries": sum(s["jobs_target_countries"] for s in kept),
            "relevant_titles_open_now": sum(s["relevant_now"] for s in kept),
            "rejected_boards": " | ".join(
                f"{s['ats']}: {s['board_url']} ({s['error'] or s['top_countries'] or 'empty'})"
                for s in stats if s not in kept),
        })

    order = {"VERIFIED": 0}
    report.sort(key=lambda r: (order.get(r["status"], 1), r["status"], r["company"].lower()))
    with open(DATA / "coverage_report.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(report[0].keys())); w.writeheader(); w.writerows(report)

    out = [{"companies": sorted(cos), "ats": boards[u][0], "slug": boards[u][1], "url": u}
           for u, cos in sorted(keep.items(), key=lambda kv: sorted(kv[1])[0].lower())]
    (ROOT / "boards.json").write_text(json.dumps(out, indent=1))

    c = Counter(r["status"] for r in report)
    print(f"\n{len(report)} companies:")
    for k, v in c.most_common():
        print(f"  {v:4}  {k}")
    print(f"\n{len(out)} boards written to boards.json  (radar.py polls these)")
    print("Details: data/coverage_report.csv, data/verified_boards.csv")


if __name__ == "__main__":
    main()
