"""One plan for the whole post-discovery pass: which companies to cover this session, by what means, within ONE cap.

    python tools/sweep_plan.py [--urls]     # the companies for this pass (marks nothing)

The user's rule (2026-10-13): the cap was there for a reason, so LinkedIn post searches and Chrome careers reads share it (`max_searches`, 10),
split by kind of company: 4 product dream companies, 3 consulting dream companies, 2 other companies the user knows someone at, 1 other company
whose jobs only a Chrome read can reach (`sweep_quotas`). Slots a category cannot fill (a short list, a company the radar already reads) flow
to the next category in that order.

Each company gets ONE action per pass, never two. A company the radar cannot read has two means, the LinkedIn post search (author-company
filter) and the Chrome careers read; the pass uses whichever it did longer ago, so they alternate across passes. A company the radar already
reads gets the post search only (the poster is the referral route); the "other" category is careers reads only.

Marking is separate and happens when an action finishes: `post_leads.py searched <key>` for a post search, `careers_queue.py done "<company>"`
for a careers read, so a cut-off pass keeps its place. Standard library only.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))
from jobradar.matching import normalize  # noqa: E402  (stdlib-only)

CATEGORIES = ["dream_product", "dream_consulting", "network", "other"]
CATEGORY_LABEL = {"dream_product": "dream (product)", "dream_consulting": "dream (consulting)", "network": "network", "other": "chrome-only"}


def categories(s: dict, rows: list[dict]) -> dict[str, list[str]]:
    """Companies per category, each employer once, in the order the lists give them."""
    import careers_queue as cq
    import post_leads as pl
    always = {normalize(c) for c in s.get("chrome_always") or []}
    seen: set[str] = set()
    out: dict[str, list[str]] = {c: [] for c in CATEGORIES}

    def add(cat: str, names) -> None:
        for name in names:
            k = normalize(name)
            if k not in seen:
                seen.add(k)
                out[cat].append(name)

    add("dream_product", list(s.get("dream_companies") or [])[:10])
    add("dream_consulting", list(s.get("dream_consulting") or [])[:5])
    add("network", list(s.get("chrome_always") or []) + pl.network_companies())
    add("other", [n for n in pl.fit_targets(s.get("company_fit", "High")) if cq.needs_chrome(n, rows, always)])
    return out


def lanes(company: str, cat: str, s: dict, rows: list[dict]) -> list[str]:
    import careers_queue as cq
    skip_posts = {normalize(c) for c in s.get("careers_site_companies") or []}
    always = {normalize(c) for c in s.get("chrome_always") or []}
    found = []
    if cat != "other" and normalize(company) not in skip_posts:
        found.append("post")
    if cq.needs_chrome(company, rows, always) or cat == "other":
        found.append("careers")
    return found


def _last(company: str, lane: str, post_log: dict, careers_log: dict) -> str:
    k = normalize(company)
    rec = (post_log.get(f"company|{k}") if lane == "post" else careers_log.get(k)) or {}
    return rec.get("last", "")


def plan(s: dict | None = None, rows: list[dict] | None = None, post_log: dict | None = None, careers_log: dict | None = None,
         total: int | None = None) -> list[tuple[str, str, str]]:
    """[(company, category, lane)] for this pass: quotas per category, one lane per company, spare slots flowing down the categories."""
    import careers_queue as cq
    import post_leads as pl
    s = pl.settings() if s is None else s
    rows = cq._coverage_rows() if rows is None else rows
    post_log = pl._load(pl.QUERIES, {}) if post_log is None else post_log
    careers_log = cq._load(cq.STATE) if careers_log is None else careers_log
    total = int(s.get("max_searches", 10)) if total is None else total
    quotas = {**{"dream_product": 4, "dream_consulting": 3, "network": 2, "other": 1}, **(s.get("sweep_quotas") or {})}
    cats = categories(s, rows)
    ranked: dict[str, list[tuple[str, str]]] = {}
    for cat in CATEGORIES:
        items = []
        for name in cats[cat]:
            ln = lanes(name, cat, s, rows)
            if not ln:
                continue
            lane = min(ln, key=lambda x: (_last(name, x, post_log, careers_log), x != "post"))   # the lane done longer ago; ties: the post search
            items.append((_last(name, lane, post_log, careers_log), name, lane))
        ranked[cat] = [(n, ln) for _, n, ln in sorted(items)]
    chosen = {cat: ranked[cat][:quotas[cat]] for cat in CATEGORIES}
    spare = total - sum(len(v) for v in chosen.values())
    for cat in CATEGORIES:                                   # spare slots flow down the categories, in order
        if spare <= 0:
            break
        more = ranked[cat][len(chosen[cat]):len(chosen[cat]) + spare]
        chosen[cat] += more
        spare -= len(more)
    return [(n, cat, ln) for cat in CATEGORIES for n, ln in chosen[cat]][:total]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--urls", action="store_true", help="also print the link to open")
    a = ap.parse_args(argv)
    import careers_queue as cq
    import post_leads as pl
    log = cq._load(cq.STATE)
    for name, cat, lane in plan():
        if lane == "post":
            line = f'{name} "we\'re hiring" security'
            url, hint = pl.search_url(line)
            extra = f"key: company|{normalize(name)}" + (f"\n  {url}" if a.urls else "") + (f"\n  NOTE: {hint}" if hint and a.urls else "")
        else:
            extra = f"mark: careers_queue.py done \"{name}\"" + (f"\n  {(log.get(normalize(name)) or {}).get('url') or 'no url yet: find the careers search page'}" if a.urls else "")
        print(f"{name} [{CATEGORY_LABEL[cat]}] {lane}\n  {extra}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
