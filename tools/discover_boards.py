"""Find job boards for target companies that don't have one yet. Proposes, never applies silently.

    python tools/discover_boards.py [--limit 40] [--company "Pen Test Partners"] [--apply]

For each target without a VERIFIED board (data/coverage_report.csv) it collects candidate
boards from ats-scrapers' company index (find_company) plus slug guesses on common ATS
platforms, fetches them, and keeps a candidate only if its board lists jobs in your target
countries (which rules out a same-name company elsewhere). Results go to
work/discovered_boards.csv with evidence (jobs in target countries, matching titles).
--apply appends the proposals to profile/overrides.csv; run verify_boards.py afterwards.
The weekly system-review runs this and asks the user before --apply.
"""
from __future__ import annotations

import argparse
import asyncio
import csv
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from jobradar.common import fetch_many, job_countries, target_countries, title_matches  # noqa: E402
from jobradar.matching import normalize_words  # noqa: E402
from jobradar.paths import profile_path  # noqa: E402

GUESS_ATS = ["greenhouse", "lever", "ashby", "workable", "personio", "recruitee", "teamtailor",
             "smartrecruiters", "pinpoint", "join_com", "bamboohr", "breezy"]
OUT = ROOT / "work" / "discovered_boards.csv"


def slug_guesses(company: str) -> list[str]:
    words = normalize_words(company.split(" / ")[0]).split()
    if not words:
        return []
    return list(dict.fromkeys(["".join(words), "-".join(words), words[0]]))


def uncovered(report: Path) -> list[str]:
    with open(report, encoding="utf-8") as fh:
        return [r["company"] for r in csv.DictReader(fh) if r["status"] != "VERIFIED"]


def candidates(company: str, use_index: bool = True) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    if use_index:
        try:
            from ats_scrapers import find_company
            df = find_company(company.split(" (")[0], limit=5)
            for _, row in df.iterrows():
                ats, slug = str(row.get("ats", "")), str(row.get("slug", ""))
                if ats and slug:
                    out.append((ats, slug))
        except Exception:
            pass  # index unavailable: guesses only
    out += [(ats, s) for s in slug_guesses(company) for ats in GUESS_ATS]
    return list(dict.fromkeys(out))


def evaluate(company: str, results) -> list[dict]:
    tgt = target_countries() | {"REMOTE-EU"}
    found = []
    for key, res in results.items():
        if not res.ok or not res.jobs:
            continue
        in_tgt = [j for j in res.jobs if job_countries(j) & tgt]
        if not in_tgt:
            continue
        ats, slug = key.split("|", 1)
        found.append({"company": company, "ats": ats, "slug": slug, "jobs_total": len(res.jobs),
                      "jobs_target_countries": len(in_tgt),
                      "relevant_titles": " | ".join(j.title for j in in_tgt if title_matches(j.title or ""))[:300],
                      "sample_company_field": (getattr(res.jobs[0], "company", "") or "")[:60]})
    return found


async def discover(companies: list[str], use_index: bool = True) -> list[dict]:
    found = []
    for company in companies:
        cands = candidates(company, use_index)
        boards = [(ats, slug, f"{ats}|{slug}") for ats, slug in cands]
        results = await fetch_many(boards, progress=False)
        hits = evaluate(company, results)
        found += hits
        print(f"{company[:35]:35} {len(cands):3} candidates -> "
              + (", ".join(f"{h['ats']}:{h['slug']} ({h['jobs_target_countries']} in target countries)" for h in hits)
                 or "none"), flush=True)
    return found


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--company", action="append", default=[])
    ap.add_argument("--limit", type=int, default=40)
    ap.add_argument("--no-index", action="store_true", help="skip the ats-scrapers company index")
    ap.add_argument("--apply", action="store_true", help=f"append {OUT.name} proposals to profile/overrides.csv")
    args = ap.parse_args(argv)
    if args.apply:
        rows = list(csv.DictReader(open(OUT, encoding="utf-8")))
        ov = profile_path("overrides.csv")
        existing = ov.read_text(encoding="utf-8") if ov.exists() else "company,careers_url,ats,slug\n"
        new = [f"{r['company']},,{r['ats']},{r['slug']}" for r in rows if f",{r['slug']}" not in existing]
        target = ROOT / "profile" / "overrides.csv"
        target.write_text(existing.rstrip("\n") + "\n" + "\n".join(new) + "\n", encoding="utf-8")
        print(f"added {len(new)} overrides; now run: python verify_boards.py --quiet")
        return 0
    companies = args.company or uncovered(ROOT / "data" / "coverage_report.csv")[: args.limit]
    found = asyncio.run(discover(companies, not args.no_index))
    OUT.parent.mkdir(exist_ok=True)
    with open(OUT, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["company", "ats", "slug", "jobs_total", "jobs_target_countries",
                                           "relevant_titles", "sample_company_field"])
        w.writeheader()
        w.writerows(found)
    print(f"\n{len(found)} candidate boards for {len(companies)} companies -> {OUT.relative_to(ROOT)}"
          "\nReview them (a slug guess can hit a different company with the same name), then --apply.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
