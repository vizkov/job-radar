"""Add a role you found yourself (a job link) through the same pipeline as the daily run. Standard library + the radar's own modules.

    python tools/add_role.py <job url>                       # fetch it, run every filter, add it if it passes
    python tools/add_role.py <job url> --dry-run             # show what would happen, write nothing
    python tools/add_role.py <job url> --override old,country   # only on the user's word, per reason, when a filter would drop it
    python tools/add_role.py <url> --company "Acme" --title "Security Engineer" --location "London, UK" --posted 2026-10-01 [--countries GB]
                                                             # a link that cannot be fetched (LinkedIn, a company site, a pasted ad): fields given by hand

Runs: the company's board through ats-scrapers (Greenhouse, Lever, Ashby links), then select() (countries, titles, permanent-only,
max_age_days, employer list), dedupe against everything seen, sponsor-register tags, tier and score, data/matches.csv, and the
board queue: exactly what radar.py does for a role it finds. A filter that would drop the role is reported with its reason and the
role is NOT added; --override names the reasons the user agreed to bypass, and matches.csv `origin` records them.
Then: `python tools/board_sync.py roles` opens the card; score-roles and sponsorship-check follow as for any role.
"""
from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

from jobradar import intake  # noqa: E402


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("url")
    ap.add_argument("--override", default="", help="comma list of filters to bypass: country, title, employment, old, company")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--company", default=""); ap.add_argument("--title", default=""); ap.add_argument("--location", default="")
    ap.add_argument("--posted", default="", help="YYYY-MM-DD; leave out only if the ad shows no date (a role with no date passes the age filter)")
    ap.add_argument("--countries", default="", help="ISO codes, e.g. GB,NL; default: read from --location")
    a = ap.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    p = None if (a.company and a.title) else asyncio.run(intake.fetch_posting(a.url))
    if p is None and a.company and a.title:
        p = intake.manual_posting(a.url, a.company, a.title, a.location, a.posted, a.countries)
    if p is None:
        print("could not fetch that posting: only Greenhouse, Lever and Ashby job links are supported here, or the job is closed. "
              "For anything else give --company, --title, --location and --posted by hand.")
        return 1
    age = f"{(__import__('datetime').date.today() - p.posted_at.date()).days} days ago" if p.posted_at else "no posted date"
    print(f"{p.company} — {p.title} | {p.location} | countries {','.join(sorted(p.countries)) or '?'} | posted {age}")
    r = intake.admit(p, {x.strip() for x in a.override.split(",") if x.strip()}, dry_run=a.dry_run)
    if r["status"] == "dropped":
        print("NOT ADDED: the radar's filters would drop this role: " + "; ".join(r["why"]) + f"  [{', '.join(r['reasons'])}]")
        print("To add it anyway, the user must say so: --override " + ",".join(r["reasons"]))
        return 2
    if r["status"] == "known":
        print(f"already known (ref {r['ref']}): nothing added")
        return 0
    verb = "would add" if r.get("dry_run") else "added"
    print(f"{verb} ref {r['ref']}, tier {r['tier']}, score {r['score']}" + (f", override: {','.join(r['overridden'])}" if r["overridden"] else "")
          + ("; card queued" if r["carded"] and not r.get("dry_run") else "; board card: " + ("yes" if r["carded"] else "no (tier not carded; promote on request)")))
    return 0


if __name__ == "__main__":
    sys.exit(main())
