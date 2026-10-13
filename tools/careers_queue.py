"""The Chrome careers-site log and queue (the pass itself is planned by `tools/sweep_plan.py`, which shares the cap with the LinkedIn searches): companies whose jobs the radar cannot read itself, so Claude reads their careers pages in Chrome.

    python tools/careers_queue.py done "<company>" [--roles N] [--note "…"]   # a read finished: only this moves it to the back
    python tools/careers_queue.py url "<company>" <careers search url>        # remember the page that worked
    python tools/careers_queue.py status                # every queued company with its tier, last read and url

The pass itself (which companies, how many, which means) is planned by `tools/sweep_plan.py`, which shares ONE cap with the LinkedIn post searches (the user, 2026-10-13: a separate cap would double it). This module keeps the log of finished reads, the remembered search urls and the test for which companies the radar cannot read.

Tiers: 0 the user's dream companies (product list and the parallel consulting list, `discovery.linkedin_posts.dream_companies` and
`dream_consulting`); 1 companies the user knows someone at, and `chrome_always` (no readable feed whatever the coverage report says);
2 the other `company_fit` targets. A company is queued only when the radar cannot read it: not VERIFIED in `data/coverage_report.csv`, or
VERIFIED but zero jobs in the user's countries. Standard library only.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))
from jobradar.matching import normalize, normalize_words  # noqa: E402  (stdlib-only)

STATE = ROOT / "state" / "chrome_careers.json"
COVERAGE = ROOT / "data" / "coverage_report.csv"
TIER_NAMES = {0: "dream", 1: "network", 2: "target"}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _load(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def settings() -> dict:
    import post_leads
    s = post_leads.settings()
    return {"dream": list(s.get("dream_companies") or [])[:10] + list(s.get("dream_consulting") or [])[:5],
            "always": list(s.get("chrome_always") or []),
            "fit": s.get("company_fit", "High"), "skip": {normalize(c) for c in s.get("careers_site_companies") or []}}


def _coverage_rows(path: Path | None = None) -> list[dict]:
    try:
        with open(path or COVERAGE, encoding="utf-8", newline="") as fh:
            return list(csv.DictReader(fh))
    except OSError:
        return []


def _row_for(company: str, rows: list[dict]) -> dict | None:
    """The coverage row for a company: same words, or one name's words start the other's ("Amazon" and "Amazon / AWS")."""
    w = normalize_words(company).split()
    for r in rows:
        rw = normalize_words(r.get("company", "")).split()
        if rw and w and (rw[:len(w)] == w or w[:len(rw)] == rw):
            return r
    return None


def needs_chrome(company: str, rows: list[dict], always: set[str]) -> bool:
    if normalize(company) in always:
        return True
    r = _row_for(company, rows)
    if r is None:
        return True
    if (r.get("status") or "").strip() != "VERIFIED":
        return True
    try:
        return int(r.get("jobs_in_target_countries") or 0) == 0
    except ValueError:
        return True


def queue(rows: list[dict] | None = None, log: dict | None = None) -> list[tuple[int, str]]:
    """(tier, company) for every company Claude must read in Chrome, each once, in the order they should be read."""
    import post_leads
    s = settings()
    rows = _coverage_rows() if rows is None else rows
    log = _load(STATE) if log is None else log
    always = {normalize(c) for c in s["always"]}
    pools = ((0, s["dream"]), (1, s["always"] + post_leads.network_companies()), (2, post_leads.fit_targets(s["fit"])))
    seen, out = set(), []
    for tier, names in pools:
        for name in names:
            k = normalize(name)
            if k in seen or (k in s["skip"] and tier != 0 and k not in always):
                continue
            if not needs_chrome(name, rows, always):
                continue
            seen.add(k)
            out.append((tier, name))
    return sorted(out, key=lambda tn: (tn[0], (log.get(normalize(tn[1])) or {}).get("last", "")))


def done(company: str, roles: int | None = None, note: str = "", now: str | None = None) -> str:
    log = _load(STATE) or {}
    k = normalize(company)
    rec = log.get(k) or {}
    rec.update({"last": now or _now(), "runs": rec.get("runs", 0) + 1, "company": company})
    if roles is not None:
        rec["roles"] = roles
    if note:
        rec["note"] = note
    log[k] = rec
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(log, indent=1, sort_keys=True), encoding="utf-8")
    return f"{company}: read recorded (run {rec['runs']})"


def set_url(company: str, url: str) -> str:
    log = _load(STATE) or {}
    rec = log.get(normalize(company)) or {"company": company}
    rec["url"] = url
    log[normalize(company)] = rec
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(log, indent=1, sort_keys=True), encoding="utf-8")
    return f"{company}: url remembered"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    d = sub.add_parser("done"); d.add_argument("company"); d.add_argument("--roles", type=int); d.add_argument("--note", default="")
    u = sub.add_parser("url"); u.add_argument("company"); u.add_argument("url")
    sub.add_parser("status")
    a = ap.parse_args(argv)
    log = _load(STATE) or {}
    if a.cmd == "done":
        print(done(a.company, a.roles, a.note))
    elif a.cmd == "url":
        print(set_url(a.company, a.url))
    else:
        for tier, name in queue(log=log):
            rec = log.get(normalize(name)) or {}
            print(f"{TIER_NAMES[tier]:8} {name:34} last={rec.get('last', 'never')[:10]:10} runs={rec.get('runs', 0)} {rec.get('url', '')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
