"""Download the UK and Dutch sponsor registers into data/registers/ (weekly workflow).

UK: Home Office "Register of worker and temporary worker licensed sponsors" (CSV).
    The asset URL changes with every update, so it's looked up through the gov.uk
    content API. Only routes relevant to skilled hires are kept.
NL: IND "Public register Work" (recognised sponsors for work / highly skilled
    migrants), an HTML table on ind.nl.

Output is sorted plain CSV (not gzip) on purpose: weekly updates change a few
hundred rows, and git stores small text diffs efficiently, whereas a changed
gzip is a whole new blob every week.
"""
from __future__ import annotations

import csv
import io
import json
import sys
from datetime import date
from pathlib import Path

import httpx
from selectolax.parser import HTMLParser

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from jobradar.sources._http import USER_AGENT  # noqa: E402

OUT = Path(__file__).resolve().parent.parent / "data" / "registers"
UK_API = "https://www.gov.uk/api/content/government/publications/register-of-licensed-sponsors-workers"
NL_URL = "https://ind.nl/en/public-register-recognised-sponsors/public-register-work"
UK_ROUTES = {"Skilled Worker", "Global Business Mobility: Senior or Specialist Worker", "Scale-up"}
MIN_ROWS = {"uk": 50_000, "nl": 5_000}  # refuse to overwrite with a truncated download


def fetch_uk(c: httpx.Client) -> tuple[list[list[str]], str]:
    meta = c.get(UK_API).raise_for_status().json()
    url = next(a["url"] for a in meta["details"]["attachments"] if a.get("content_type", "").startswith("text/csv"))
    text = c.get(url).raise_for_status().content.decode("utf-8-sig", errors="replace")
    orgs: dict[tuple[str, str], set[str]] = {}
    for r in csv.DictReader(io.StringIO(text)):
        route = (r.get("Route") or "").strip()
        if route in UK_ROUTES:
            key = (" ".join((r["Organisation Name"] or "").split()), " ".join((r.get("Town/City") or "").split()))
            orgs.setdefault(key, set()).add(route)
    rows = sorted([n, t, "; ".join(sorted(rs))] for (n, t), rs in orgs.items() if n)
    return rows, url


def fetch_nl(c: httpx.Client) -> tuple[list[list[str]], str]:
    tree = HTMLParser(c.get(NL_URL).raise_for_status().text)
    rows = []
    for tr in tree.css("table tbody tr"):
        th, td = tr.css_first("th"), tr.css_first("td")  # organisation is the row header
        name = " ".join(th.text().split()).replace('""', '"') if th else ""
        if name:
            rows.append([name, " ".join(td.text().split()) if td else ""])
    return sorted(rows), NL_URL


def write(name: str, header: list[str], rows: list[list[str]]) -> None:
    if len(rows) < MIN_ROWS[name]:
        raise SystemExit(f"{name}: only {len(rows)} rows — refusing to overwrite (format change?)")
    with open(OUT / f"{name}_sponsors.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(header)
        w.writerows(rows)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    meta = {}
    with httpx.Client(timeout=120, follow_redirects=True, headers={"User-Agent": USER_AGENT}) as c:
        uk, uk_url = fetch_uk(c)
        write("uk", ["name", "town", "routes"], uk)
        nl, nl_url = fetch_nl(c)
        write("nl", ["name", "kvk"], nl)
    meta = {"refreshed": date.today().isoformat(),
            "uk": {"source": uk_url, "rows": len(uk), "routes": sorted(UK_ROUTES)},
            "nl": {"source": nl_url, "rows": len(nl)}}
    (OUT / "meta.json").write_text(json.dumps(meta, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(meta, indent=1))


if __name__ == "__main__":
    main()
