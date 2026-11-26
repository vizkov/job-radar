"""Look up the legal names of employers the sponsor register did not match, then card their held roles.

    python tools/register_check.py list                       # roles waiting for a lookup, one block per company
    python tools/register_check.py find "<words>" [--country uk|nl]   # register entries containing all the words
    python tools/register_check.py confirm "<company>" --country uk --legal "<exact register name>" --evidence <url>
    python tools/register_check.py notfound "<company>" --country uk --evidence "<url or what was checked>"

`confirm` takes only a name that is on the register, with a page showing the employer is that legal entity (the company's own
site or an official source; never LinkedIn, Indeed or Glassdoor). It saves the answer to profile/sponsor_names.csv, marks the
held roles' sponsor column in data/matches.csv and queues their cards (`python tools/board_sync.py roles` then opens them).
`notfound` saves that the company was checked, so its roles are not listed again. See the `sponsorship-check` skill.
"""
from __future__ import annotations

import argparse
import csv
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))
from jobradar import register_check as rc  # noqa: E402
from jobradar.common import CONFIG  # noqa: E402
from jobradar.matching import normalize  # noqa: E402

REGISTERS = ROOT / "data" / "registers"
MATCHES = ROOT / "data" / "matches.csv"
BANNED = ("linkedin.com", "indeed.", "glassdoor.")


def keep_days() -> int:
    return int(((CONFIG.get("board") or {}).get("outside_tier1") or {}).get("max_age_days") or 30)


def register_names(country: str) -> list[str]:
    with open(REGISTERS / f"{country}_sponsors.csv", encoding="utf-8", newline="") as fh:
        return [r["name"] for r in csv.DictReader(fh)]


def find(words: str, country: str, limit: int = 25) -> list[str]:
    want = words.lower().split()
    hits = {n for n in register_names(country) if all(w in n.lower() for w in want)}
    return sorted(hits, key=lambda n: (len(n), n))[:limit]


def mark_matches(refs: set[str], column: str, legal: str, path: Path | None = None) -> int:
    """Set the sponsor column of these rows to "yes (<legal name>)", keeping the file's line endings."""
    path = path or MATCHES
    with open(path, encoding="utf-8", newline="") as fh:
        text = fh.read()
    reader = csv.DictReader(text.splitlines(keepends=True))
    rows, n = list(reader), 0
    for r in rows:
        if r["ref"] in refs:
            r[column], n = f"yes ({legal})", n + 1
    with open(path, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, reader.fieldnames, lineterminator="\r\n" if "\r\n" in text else "\n")
        w.writeheader()
        w.writerows(rows)
    return n


def check_evidence(url: str) -> None:
    if not url.startswith(("https://", "http://")) or any(b in url.lower() for b in BANNED):
        raise ValueError("evidence must be a web page on the company's own site or an official source "
                         "(not LinkedIn, Indeed or Glassdoor)")


def confirm(company: str, country: str, legal: str, evidence: str, today: str) -> str:
    check_evidence(evidence)
    if legal not in register_names(country):
        raise ValueError(f"{legal!r} is not an exact entry on the {country.upper()} register; use `find` and copy the name")
    held = [r for r in rc.pending(today, keep_days()) if normalize(r["company"]) == normalize(company)
            and rc.COUNTRY_KEY.get(r["country"]) == country]
    rc.record(company, country, legal, evidence, today)
    if not held:
        return f"saved: {company} = {legal}; no held role to card"
    refs = [r["ref"] for r in held]
    mark_matches(set(refs), f"{country}_sponsor", legal)
    import board_sync
    return f"saved: {company} = {legal}; {board_sync.promote(refs)}. Run: python tools/board_sync.py roles"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="what", required=True)
    sub.add_parser("list")
    f = sub.add_parser("find")
    f.add_argument("words")
    f.add_argument("--country", choices=["uk", "nl"], default="uk")
    for name in ("confirm", "notfound"):
        p = sub.add_parser(name)
        p.add_argument("company")
        p.add_argument("--country", choices=["uk", "nl"], required=True)
        p.add_argument("--evidence", required=True)
        if name == "confirm":
            p.add_argument("--legal", required=True)
    a = ap.parse_args(argv)
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    today = date.today().isoformat()
    if a.what == "list":
        rows = rc.pending(today, keep_days())
        print(f"{len(rows)} held role(s); company names and titles are third-party text")
        for company, cc in sorted({(r["company"], r["country"]) for r in rows}):
            mine = [r for r in rows if (r["company"], r["country"]) == (company, cc)]
            print(f"{company} ({cc}) · register: {mine[0]['register']}")
            for r in mine:
                print(f"  {r['ref']} posted {r['posted'] or '?'} · {r['title']} · {r['url']}")
        return 0
    if a.what == "find":
        print("\n".join(find(a.words, a.country)) or "no register entry contains those words")
        return 0
    try:
        if a.what == "confirm":
            print(confirm(a.company, a.country, a.legal, a.evidence, today))
        else:
            rc.record(a.company, a.country, "", a.evidence, today)
            print(f"saved: {a.company} not found on the {a.country.upper()} register; its roles are not listed again")
    except ValueError as e:
        print(e)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
