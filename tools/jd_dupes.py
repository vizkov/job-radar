"""Is this ad the same ad as another card's? Read-only: compares the full saved job-description texts, never the titles alone.

    python tools/jd_dupes.py                 # every pair of saved ads from the same company
    python tools/jd_dupes.py <ref> [<ref>…]  # only pairs that include these refs

One job is often posted once per country or under a slightly different title (n8n's Berlin, NL, GB and IE listings; Meta's two
Security Engineer postings). The radar's ref is a hash of company + title + country, so each listing gets its own card. The radar
cannot compare ads (it never reads them), so this runs in a session, after `jd_prep.py` has saved `work/jd/<ref>/jd.txt`.

A pair is SAME only when at least 90% of the shorter ad's 8-word runs appear in the longer one and the shorter ad is not tiny.
The tool also prints the shorter ad's sentences that the other ad lacks, so the verdict is checked against the differing text and not
skimmed from the title. It writes nothing and moves no card: the user decides what to skip.
"""
from __future__ import annotations

import argparse
import csv
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WORK = ROOT / "work" / "jd"
MATCHES = ROOT / "data" / "matches.csv"
RUN = 8             # words per shingle
SAME = 0.90         # share of the shorter ad's runs found in the other ad
SIMILAR = 0.60
MIN_RUNS = 100      # a shorter ad than this (about 110 words) is a snippet, not an ad: never "same"


def runs(text: str) -> set[str]:
    w = re.findall(r"\w+", text.lower())
    return {" ".join(w[i:i + RUN]) for i in range(len(w) - RUN + 1)}


def compare(a: str, b: str) -> dict:
    """Containment of the shorter ad in the longer one, plus the shorter ad's sentences the longer one lacks."""
    ra, rb = runs(a), runs(b)
    small, big, st, bt = (ra, rb, a, b) if len(ra) <= len(rb) else (rb, ra, b, a)
    if not small:
        return {"share": 0.0, "verdict": "different", "small_runs": 0, "missing": [], "only_in_longer": []}
    share = len(small & big) / len(small)
    verdict = "same" if share >= SAME and len(small) >= MIN_RUNS else "similar" if share >= SIMILAR else "different"
    return {"share": share, "verdict": verdict, "small_runs": len(small),
            "missing": _lacking(st, big), "only_in_longer": _lacking(bt, small)}


def _lacking(text: str, other_runs: set[str]) -> list[str]:
    """Sentences of `text` whose 8-word runs are mostly absent from the other ad."""
    out = []
    for s in re.split(r"(?<=[.!?])\s+|\n+", text):
        r = runs(s)
        if r and len(r - other_runs) / len(r) > 0.5 and s.strip() not in out:
            out.append(s.strip())
    return out


def _label(ref: str, rows: dict) -> str:
    r = rows.get(ref, {})
    return f"{ref} {r.get('company', '?')} — {r.get('title', '?')} ({r.get('countries') or r.get('country', '?')})"


def find(refs: list[str] | None = None) -> list[tuple[str, str, dict]]:
    rows: dict[str, dict] = {}
    if MATCHES.exists():
        for r in csv.DictReader(MATCHES.open(encoding="utf-8")):
            rows[r["ref"]] = r
    texts = {}
    for p in WORK.glob("*/jd.txt"):
        t = p.read_text(encoding="utf-8", errors="replace")
        if len(t) > 500 and p.parent.name in rows:
            texts[p.parent.name] = t
    by_company: dict[str, list[str]] = {}
    for ref in texts:
        by_company.setdefault(rows[ref]["company"].strip().lower(), []).append(ref)
    out = []
    for group in by_company.values():
        for i, x in enumerate(sorted(group)):
            for y in sorted(group)[i + 1:]:
                if refs and x not in refs and y not in refs:
                    continue
                out.append((x, y, compare(texts[x], texts[y])))
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("refs", nargs="*")
    args = ap.parse_args(argv)
    sys.stdout.reconfigure(errors="replace")   # ads carry emoji; a Windows console cannot print them
    rows = {r["ref"]: r for r in csv.DictReader(MATCHES.open(encoding="utf-8"))} if MATCHES.exists() else {}
    pairs = find(args.refs or None)
    shown = 0
    for x, y, c in pairs:
        if c["verdict"] == "different":
            continue
        shown += 1
        print(f"{c['verdict'].upper()} {c['share']:.0%} of the shorter ad ({c['small_runs']} runs) is in the longer one:")
        print(f"  {_label(x, rows)}\n  {_label(y, rows)}")
        for key, who in (("missing", "only in the shorter ad"), ("only_in_longer", "only in the longer ad")):
            if c[key]:
                print(f"  {len(c[key])} sentence(s) {who}; read them before calling it the same:")
                for s in c[key][:6]:
                    print(f"    - {s[:200]}")
        if not c["missing"] and not c["only_in_longer"]:
            print("  no sentence differs")
    if not shown:
        print("no saved ads from the same company look alike")
    return 0


if __name__ == "__main__":
    sys.exit(main())
