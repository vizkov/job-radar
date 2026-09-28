"""Tune the tier rules from the user's Fit scores, automatically but visibly. Standard library only.

    python tools/calibrate.py report            # per title keyword: roles scored, average Fit, skip/apply rates
    python tools/calibrate.py apply [--dry-run] # apply the changes the evidence supports (the session brief runs this weekly)
    python tools/calibrate.py revert <keyword>  # put a keyword's weight back to what it was before the last change

Only config.json -> tiering.title_keywords weights move, by one step at a time, within 0..MAX_WEIGHT,
and only with enough evidence (MIN_TOTAL scored roles overall, MIN_PER with that keyword). Title
include/exclude lists, countries and every other setting stay the user's decision. Every change is
logged to data/calibration_log.jsonl and reported in the session brief with a one-line undo.

Why weights only: the tier is a title-based guess made before anyone reads the ad; the Fit score is
made after. When roles matching a keyword keep scoring Skip, that keyword over-promises.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from jobradar.paths import profile_path  # noqa: E402  (stdlib-only)

SCORES = ROOT / "data" / "scores.jsonl"
MATCHES = ROOT / "data" / "matches.csv"
LOG = ROOT / "data" / "calibration_log.jsonl"
MIN_TOTAL, MIN_PER, MAX_WEIGHT = 30, 5, 5
LOWER_IF = {"avg_fit_below": 45, "skip_rate_at_least": 0.7}
RAISE_IF = {"avg_fit_at_least": 70, "apply_rate_at_least": 0.6}
COOLDOWN = timedelta(days=7)   # at most one change per keyword per week


def _kw_re(word: str) -> re.Pattern:
    """Same rule as jobradar.common.keyword_re (whole word; trailing * = prefix), without its imports."""
    w = word.strip().lower()
    return re.compile(r"\b" + re.escape(w[:-1]) if w.endswith("*") else r"\b" + re.escape(w) + r"\b", re.I)


def config_path() -> Path:
    return profile_path("config.json")


def weights(cfg_text: str | None = None) -> dict[str, int]:
    cfg = json.loads(cfg_text if cfg_text is not None else config_path().read_text(encoding="utf-8"))
    return {k: int(v) for k, v in (cfg.get("tiering", {}).get("title_keywords") or {}).items()}


def best_keyword(title: str, kw: dict[str, int]) -> str | None:
    """The keyword that set this title's weight (highest weight among matches), as tiering.score does."""
    hits = [(w, k) for k, w in kw.items() if _kw_re(k).search(title or "")]
    return max(hits)[1] if hits else None


def stats(kw: dict[str, int] | None = None) -> tuple[int, dict[str, dict]]:
    kw = kw if kw is not None else weights()
    titles = {}
    if MATCHES.exists():
        with open(MATCHES, encoding="utf-8", newline="") as fh:
            titles = {r["ref"]: r["title"] for r in csv.DictReader(fh) if r.get("ref")}
    scored = [json.loads(l) for l in SCORES.read_text(encoding="utf-8").splitlines() if l.strip()] \
        if SCORES.exists() else []
    per: dict[str, dict] = {}
    for s in scored:
        k = best_keyword(titles.get(s["key"], s.get("title", "")), kw)
        if not k:
            continue
        d = per.setdefault(k, {"n": 0, "fit": 0, "skip": 0, "apply": 0})
        d["n"] += 1
        d["fit"] += s.get("fit_score", 0)
        d["skip"] += s.get("recommendation") == "skip"
        d["apply"] += s.get("recommendation") == "apply"
    for d in per.values():
        d["avg_fit"] = round(d["fit"] / d["n"])
        d["skip_rate"], d["apply_rate"] = d["skip"] / d["n"], d["apply"] / d["n"]
    return len(scored), per


def _log_rows() -> list[dict]:
    return [json.loads(l) for l in LOG.read_text(encoding="utf-8").splitlines() if l.strip()] if LOG.exists() else []


def proposals(now: datetime | None = None) -> list[dict]:
    now = now or datetime.now(timezone.utc)
    kw = weights()
    total, per = stats(kw)
    if total < MIN_TOTAL:
        return []
    recent = {r["keyword"] for r in _log_rows() if now - datetime.fromisoformat(r["at"]) < COOLDOWN}
    out = []
    for k, d in per.items():
        if d["n"] < MIN_PER or k in recent:
            continue
        w = kw[k]
        if d["avg_fit"] < LOWER_IF["avg_fit_below"] and d["skip_rate"] >= LOWER_IF["skip_rate_at_least"] and w > 0:
            out.append({"keyword": k, "from": w, "to": w - 1, **_why(d)})
        elif d["avg_fit"] >= RAISE_IF["avg_fit_at_least"] and d["apply_rate"] >= RAISE_IF["apply_rate_at_least"] \
                and w < MAX_WEIGHT:
            out.append({"keyword": k, "from": w, "to": w + 1, **_why(d)})
    return out


def _why(d: dict) -> dict:
    return {"n": d["n"], "avg_fit": d["avg_fit"], "skip_rate": round(d["skip_rate"], 2),
            "apply_rate": round(d["apply_rate"], 2)}


def set_weight(keyword: str, value: int) -> None:
    """Edit one weight in place, keeping the file's layout and comments."""
    path = config_path()
    text = path.read_text(encoding="utf-8")
    rx = re.compile(r'("title_keywords"\s*:\s*\{[^}]*?"' + re.escape(keyword) + r'"\s*:\s*)(-?\d+)', re.S)
    new, n = rx.subn(lambda m: m.group(1) + str(value), text, count=1)
    if n != 1:
        raise SystemExit(f"keyword {keyword!r} not found in tiering.title_keywords")
    json.loads(new)  # still valid JSON
    path.write_text(new, encoding="utf-8")


def apply(dry_run: bool = False, now: datetime | None = None) -> list[dict]:
    now = now or datetime.now(timezone.utc)
    changes = proposals(now)
    if dry_run:
        return changes
    for c in changes:
        set_weight(c["keyword"], c["to"])
        LOG.parent.mkdir(parents=True, exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as fh:
            fh.write(json.dumps({**c, "at": now.isoformat(timespec="seconds")}) + "\n")
    return changes


def revert(keyword: str) -> str:
    last = next((r for r in reversed(_log_rows()) if r["keyword"] == keyword and "reverted" not in r), None)
    if last is None:
        return f"no automatic change to {keyword!r} to revert"
    set_weight(keyword, last["from"])
    with open(LOG, "a", encoding="utf-8") as fh:
        fh.write(json.dumps({"keyword": keyword, "from": last["to"], "to": last["from"], "reverted": True,
                             "at": datetime.now(timezone.utc).isoformat(timespec="seconds")}) + "\n")
    return f"{keyword}: weight back to {last['from']} (the cooldown stops it changing again for a week)"


def describe(c: dict) -> str:
    return (f"'{c['keyword']}' weight {c['from']}→{c['to']} ({c['n']} scored roles: average Fit {c['avg_fit']}, "
            f"{int(c['skip_rate'] * 100)}% skip, {int(c['apply_rate'] * 100)}% apply)")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("report")
    a = sub.add_parser("apply"); a.add_argument("--dry-run", action="store_true")
    r = sub.add_parser("revert"); r.add_argument("keyword")
    args = ap.parse_args(argv)
    if args.cmd == "report":
        kw = weights()
        total, per = stats(kw)
        print(f"{total} scored roles (automatic tuning starts at {MIN_TOTAL}; a keyword needs {MIN_PER})")
        for k, d in sorted(per.items(), key=lambda x: -x[1]["n"]):
            print(f"  {k:24} weight {kw[k]}  n={d['n']:3}  avg Fit {d['avg_fit']:3}  "
                  f"skip {int(d['skip_rate'] * 100):3}%  apply {int(d['apply_rate'] * 100):3}%")
    elif args.cmd == "apply":
        changes = apply(args.dry_run)
        print("\n".join(("would change " if args.dry_run else "changed ") + describe(c) for c in changes)
              or "no changes: not enough evidence yet, or nothing to adjust")
    else:
        print(revert(args.keyword))
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
