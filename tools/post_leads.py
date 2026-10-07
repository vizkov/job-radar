"""LinkedIn hiring-post discovery: the bookkeeping behind the `post-discovery` skill. Standard library only.

    python tools/post_leads.py queries [--n N] [--urls] # the next searches to run (least recently run first); marks them run;
                                                        # --urls also prints the LinkedIn link (author-company filter when the id is known)
    python tools/post_leads.py company-id "<company>" <digits>   # record a company's LinkedIn id (from the Author company filter)
    python tools/post_leads.py person add --name "…" --url <profile> --company "…" [--headline "…"] [--function "…"]
    python tools/post_leads.py person next [--n N]      # known recruiters/managers whose posts were read longest ago
    python tools/post_leads.py person read <profile url>   # mark one person's posts as read now
    python tools/post_leads.py lead --post-url <url> --author "…" --company "…" --title "…" [--location "…"] \\
        [--posted YYYY-MM-DD] [--kind person|job_board] [--author-url <url>] [--reposter "…"] [--jd-url <url>] \\
        [--open yes|no|unknown] [--note "…"]            # log one post; says if the role is already known or stale
    python tools/post_leads.py add-role <lead id> --countries GB[,NL] [--location "…"] [--override old,company]   # new roles only, through the radar's filters (jobradar/intake.py): row + board card
    python tools/post_leads.py stats [--days N]         # what the posts added compared with the other sources

The searches themselves are run by Claude in the user's own logged-in Chrome, read-only (see the skill and
CLAUDE.md rule 4c). This file never touches LinkedIn: it keeps the rotation, the people list and the lead log,
and turns a confirmed lead into the same matches.csv row and board card as any other role. The role's ref is
the hash of the same company+title+country key `jobradar/dedupe.py` uses, so if the radar later finds the
posting on a careers page or ATS it lands on the same card instead of opening a second one.

Private files: state/post_queries.json (when each search last ran), data/post_people.jsonl (people whose posts
are worth re-reading), data/post_leads.jsonl (every post logged).
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import itertools
import json
import re
import sys
from urllib.parse import quote
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))
from jobradar.matching import normalize, normalize_words  # noqa: E402  (stdlib-only)
from jobradar.paths import profile_path  # noqa: E402

QUERIES = ROOT / "state" / "post_queries.json"
COMPANY_IDS = ROOT / "state" / "linkedin_company_ids.json"   # {normalised company: LinkedIn company id}, read once from the filter
PEOPLE = ROOT / "data" / "post_people.jsonl"
LEADS = ROOT / "data" / "post_leads.jsonl"
MATCHES = ROOT / "data" / "matches.csv"
KINDS = ["person", "job_board"]   # a hiring post by someone at the company, or a job-board / "follow me for every opening" repost
DEFAULTS = {
    "enabled": False, "max_searches": 8, "max_scrolls": 12, "max_people_per_session": 8, "max_post_age_days": 30,
    "company_queries": 6, "company_extra": [], "company_fit": "High", "network_only": False, "careers_site_companies": [], "not_words": ["contract", "contractor", "freelance"],
    # Each title is a LinkedIn query fragment, used as written: quotes keep a phrase together, OR joins spellings.
    "titles": ['("application security" OR appsec)', '"product security"', '("penetration tester" OR pentester OR "pen tester")',
               '("threat modelling" OR "threat modeling")', '("AI security" OR "LLM security")', '"security consultant"',
               '"vulnerability management"', '"security architect"'],
    "places": ["United Kingdom", "London", "Netherlands", "Amsterdam", "Ireland", "Switzerland", "Germany", "Sweden"],
    "phrases": ['"we\'re hiring"', '"visa sponsorship"', '"relocation"', '"join my team"'],
}
SCORES = ROOT / "data" / "scores.jsonl"
TARGETS = profile_path("targets.tsv")   # the user's target companies; an optional Fit column ranks them


def settings() -> dict:
    try:
        cfg = json.loads(profile_path("config.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        cfg = {}
    return {**DEFAULTS, **((cfg.get("discovery") or {}).get("linkedin_posts") or {})}


def _load(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def _jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _append(path: Path, rec: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, ensure_ascii=False) + "\n")


def leads() -> dict[str, dict]:
    """Every logged lead by id; later records (e.g. status "added") overwrite fields of the first."""
    out: dict[str, dict] = {}
    for r in _jsonl(LEADS):
        out[r["id"]] = {**out.get(r["id"], {}), **r}
    return out


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def fit_companies() -> list[str]:
    """Employers whose roles the user scored apply or maybe, best score first: where hiring posts are most worth finding."""
    best: dict[str, tuple[int, str]] = {}
    for r in _jsonl(SCORES):
        if r.get("recommendation") in ("apply", "maybe") and r.get("company"):
            key = normalize(r["company"])
            if r.get("fit_score", 0) >= best.get(key, (-1, ""))[0]:
                best[key] = (r.get("fit_score", 0), r["company"])
    return [name for _, name in sorted(best.values(), key=lambda v: -v[0])]


def fit_targets(fit: str) -> list[str]:
    """Companies in targets.tsv whose Fit column equals `fit` (case-insensitive), in file order. No Fit column or no `fit`: none."""
    if not fit or not TARGETS.exists():
        return []
    with TARGETS.open(encoding="utf-8", newline="") as fh:
        return [r["Company"].strip() for r in csv.DictReader(fh, delimiter="\t")
                if r.get("Company") and (r.get("Fit") or "").strip().lower() == fit.strip().lower()]


def _has_contact(company: str) -> bool:
    """True if `profile/network.csv` lists someone the user knows at `company` (same loose match as `referrals.py contacts`)."""
    from referrals import contacts
    return bool(contacts(company))


def network_companies() -> list[str]:
    """Employers listed in `profile/network.csv`, once each, in the order the user told Claude."""
    from referrals import NETWORK
    if not NETWORK.exists():
        return []
    with open(NETWORK, encoding="utf-8", newline="") as fh:
        names = [r.get("company", "").strip() for r in csv.DictReader(fh)]
    return list(dict.fromkeys(n for n in names if n))


def ranked_companies() -> list[tuple[int, str]]:
    """(tier, company) for every employer the company searches walk, each once. Tier 0: named in chat (`company_extra`).
    Tier 1: the user knows someone there (any employer in `network.csv`: knowing someone makes it a fit; the user's word, 2026-10-04): a hiring post
    there leads to a referral before applying. Tier 2: scored apply/maybe, no contact. Tier 3: `company_fit` targets, no contact."""
    s = settings()
    scored, targets = fit_companies(), fit_targets(s["company_fit"])
    known = network_companies()
    good = {normalize(c) for c in scored + targets + known}
    # `careers_site_companies` (the user, 2026-10-06) are read on their own careers sites in Chrome, not through post searches: start them as seen
    seen, out = {normalize(c) for c in s.get("careers_site_companies") or []}, []
    for tier_of, names in ((lambda c: 0, list(s["company_extra"])),
                           (lambda c: 1 if _has_contact(c) else 9, known + scored + targets),
                           (lambda c: 2, scored), (lambda c: 3, targets)):
        for name in names:
            if normalize(name) in seen or normalize(name) not in good and tier_of(name) != 0:
                continue
            t = tier_of(name)
            if t == 9 or (t in (2, 3) and s.get("network_only")):
                continue   # no contact: left for the tier 2/3 passes, in their own order
            seen.add(normalize(name))
            out.append((t, name))
    return _merge_variants(out)


def _merge_variants(ranked: list[tuple[int, str]]) -> list[tuple[int, str]]:
    """One search per employer (the user, 2026-10-06: 'Amazon', 'Amazon / AWS' and 'Meta AI (FAIR)' spent three of eight searches on the same posts).
    A name whose words start with another listed name's words ('amazon aws' after 'amazon', 'meta ai' after 'meta') is a variant: it folds into the
    shorter name, which keeps the better (lower) tier. Whole words only, so 'Meta' never swallows 'Metaswitch'."""
    words = {name: normalize_words(name).split() for _, name in ranked}
    best = {}
    for tier, name in ranked:
        w = words[name]
        base = next((m for _, m in ranked if m != name and words[m] and len(words[m]) < len(w) and w[:len(words[m])] == words[m]), name)
        best[base] = min(tier, best.get(base, tier))
    return [(best[name], name) for _, name in ranked if name in best]


def search_companies() -> list[str]:
    """The employers the company searches walk, best first: see `ranked_companies`."""
    return [name for _, name in ranked_companies()]


def company_id(company: str, path: Path | None = None) -> str:
    """LinkedIn's numeric id for `company` ('' if not recorded yet), for the post-search `authorCompany` filter."""
    return str(_load(path or COMPANY_IDS, {}).get(normalize(company), ""))


def set_company_id(company: str, cid: str, path: Path | None = None) -> str:
    path = path or COMPANY_IDS
    if not re.fullmatch(r"\d{1,12}", cid):
        raise SystemExit("the company id is the number in the address bar after authorCompany=%5B%22 (digits only)")
    ids = _load(path, {})
    ids[normalize(company)] = cid
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(ids, indent=1, sort_keys=True), encoding="utf-8")
    return f"{company}: LinkedIn company id {cid} recorded"


def search_url(line: str, path: Path | None = None) -> tuple[str, str]:
    """(url, hint) for one line from `next_queries`. A company line whose LinkedIn id is known becomes `hiring security` with the
    `authorCompany` filter: only posts written by people who work there (the user's idea, 2026-10-04; tested on Meta: 3 of 6 posts were
    by Meta staff, 2 real hiring posts, against none from a company-name keyword search). Without an id the hint says how to get one."""
    base = "https://www.linkedin.com/search/results/content/?keywords={}&sortBy=%22date_posted%22"
    m = re.fullmatch(r"""(.+?) "we're hiring" security""", line)
    if m:
        cid = company_id(m.group(1), path)
        if cid:
            return base.format(quote("hiring security")) + f"&authorCompany=%5B%22{cid}%22%5D", ""
        return base.format(quote(line)), (f"no LinkedIn id for {m.group(1)}: open All filters > Author company, pick the company, read the digits "
                                          f"after authorCompany in the address bar, then `post_leads.py company-id \"{m.group(1)}\" <digits>`")
    return base.format(quote(line)), ""


def next_queries(n: int | None = None, now: str | None = None) -> list[str]:
    """The next `n` post searches, least recently run first; marks them run. `company_queries` of them are
    "<company> hiring security", employers with a contact of the user's first (`ranked_companies`); the rest walk the title x place grid
    on a diagonal, so one session does not spend every search on one city. The phrase rotates each time a
    (title, place) pair comes round again. `not_words` are appended as NOT (...) to the grid searches."""
    s = settings()
    n = s["max_searches"] if n is None else n
    log = _load(QUERIES, {})
    stamp = now or _now()
    out = []
    # keyed by the normalised name, so "Amazon" and "Amazon Web Services" are one employer however the best-scored role names it;
    # the list itself is rebuilt from the scores each time, so new employers join (never run: first) and dropped ones leave
    ckey = lambda c: f"company|{normalize(c)}"  # noqa: E731
    firms = [c for _, c in sorted(ranked_companies(), key=lambda tc: (tc[0], (log.get(ckey(tc[1])) or {}).get("last", "")))]
    for c in firms[:min(s["company_queries"], n)]:
        out.append(f'{c} "we\'re hiring" security')
        log[ckey(c)] = {"last": stamp, "runs": (log.get(ckey(c)) or {}).get("runs", 0) + 1}
    titles, places, phrases = s["titles"], s["places"], s["phrases"]
    tail = f" NOT ({' OR '.join(s['not_words'])})" if s["not_words"] else ""
    pairs = list(itertools.product(range(len(titles)), range(len(places))))
    pairs.sort(key=lambda p: ((log.get(f"{titles[p[0]]}|{places[p[1]]}") or {}).get("last", ""), (p[0] + p[1]) % len(titles), p[1]))
    for ti, pi in pairs[:n - len(out)]:
        key = f"{titles[ti]}|{places[pi]}"
        rec = log.get(key) or {"runs": 0}
        out.append(f"{phrases[rec['runs'] % len(phrases)]} {titles[ti]} {places[pi]}{tail}")
        log[key] = {"last": stamp, "runs": rec["runs"] + 1}
    QUERIES.parent.mkdir(parents=True, exist_ok=True)
    QUERIES.write_text(json.dumps(log, indent=1, sort_keys=True), encoding="utf-8")
    return out


def people() -> list[dict]:
    """Latest record per profile URL."""
    latest: dict[str, dict] = {}
    for r in _jsonl(PEOPLE):
        latest[r["url"]] = {**latest.get(r["url"], {}), **r}
    return list(latest.values())


def add_person(name: str, url: str, company: str, headline: str = "", function: str = "") -> str:
    url = _clean_url(url)
    _append(PEOPLE, {"name": name, "url": url, "company": company, "headline": headline, "function": function,
                     "added": _now(), "last_read": ""})
    return f"saved {name} ({company})"


def next_people(n: int | None = None) -> list[dict]:
    n = settings()["max_people_per_session"] if n is None else n
    return sorted(people(), key=lambda p: p.get("last_read") or "")[:n]


def mark_read(url: str) -> str:
    url = _clean_url(url)
    if not any(p["url"] == url for p in people()):
        return f"unknown person: {url}"
    _append(PEOPLE, {"url": url, "last_read": _now()})
    return "marked read"


def _clean_url(url: str) -> str:
    """Drop the query string, fragment and trailing slash: the same post or profile has many tracking variants."""
    return re.sub(r"[?#].*$", "", (url or "").strip()).rstrip("/")


def lead_id(post_url: str) -> str:
    return hashlib.sha1(_clean_url(post_url).lower().encode()).hexdigest()[:10]


def _title_words(title: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", (title or "").lower())) - {"and", "the", "of", "for", "a", "in", "m", "f", "d", "w"}


def known_roles(company: str, title: str, path: Path | None = None) -> list[dict]:
    """Rows of matches.csv for the same employer and a similar title (most of the title's words shared)."""
    path = path or MATCHES
    if not path.exists():
        return []
    key, want = normalize_words(company), _title_words(title)
    hits = []
    for row in csv.DictReader(path.open(encoding="utf-8")):
        other = normalize_words(row.get("company", ""))
        if not (key and other and (other == key or other.startswith(key + " ") or key.startswith(other + " "))):
            continue
        have = _title_words(row.get("title", ""))
        share = len(want & have) / min(len(want), len(have)) if want and have else 0
        if share >= 0.6:
            hits.append((share, len(want & have), row))
    return [r for *_, r in sorted(hits, key=lambda h: h[:2], reverse=True)]   # closest title first


def log_lead(post_url: str, author: str, company: str, title: str, location: str = "", posted: str = "",
             kind: str = "person", author_url: str = "", reposter: str = "", jd_url: str = "", open_: str = "unknown",
             note: str = "", today: date | None = None) -> tuple[str, dict]:
    """Record one post. Returns (message, record); record["status"] is known (the radar already has the role),
    stale (original post older than max_post_age_days and the role not confirmed open), job_board or new."""
    lid = lead_id(post_url)
    if lid in leads():
        return f"lead {lid} is already logged", {}
    today = today or date.today()
    known = known_roles(company, title)
    age = None
    if posted:
        try:
            age = (today - date.fromisoformat(posted[:10])).days
        except ValueError:
            age = None
    if known:
        status = "known"
    elif kind == "job_board":
        status = "job_board"
    elif age is not None and age > settings()["max_post_age_days"] and open_ != "yes":
        status = "stale"
    else:
        status = "new"
    rec = {"id": lid, "post_url": _clean_url(post_url), "author": author, "author_url": _clean_url(author_url),
           "reposter": reposter, "company": company, "title": title, "location": location, "posted": posted,
           "age_days": age, "kind": kind, "jd_url": jd_url, "open": open_, "status": status,
           "ref": (known[0]["ref"] if known else ""), "note": note, "at": _now()}
    _append(LEADS, rec)
    msg = {"known": f"already known: the radar has this role (ref {rec['ref']}); the poster is a warm route",
           "stale": f"stale: the original post is {age} days old and the role is not confirmed open",
           "job_board": "job-board repost: not a contact; counts only as a sign the role is live",
           "new": "NEW: not in matches.csv. Check the JD, then add-role"}[status]
    return f"lead {lid}: {msg}", rec


def add_role(lid: str, countries: str, location: str = "", gh=None, override: str = "") -> str:
    """Turn a `new` lead into a matches.csv row and a queued board card, through the radar's own pipeline
    (jobradar/intake.py: country, title, permanent-only, age and employer filters, dedupe, sponsor tags, tier). A filter that
    would drop the role is reported and the role is not added, unless `override` names the reason (the user's word)."""
    import board_sync
    from jobradar import intake
    from jobradar.model import Posting
    lead = leads().get(lid)
    if not lead:
        return f"unknown lead {lid}"
    if lead["status"] != "new":
        return f"lead {lid} is {lead['status']}: not added"
    cc_list = [c.strip().upper() for c in countries.split(",") if c.strip()]
    if not cc_list:
        return "give --countries (ISO codes, e.g. GB,NL)"
    try:
        posted_at = datetime.fromisoformat(lead["posted"]) if lead.get("posted") else None
    except ValueError:
        posted_at = None
    p = Posting(source="linkedin_post", company=lead["company"], title=lead["title"], location=location or lead["location"],
                countries=frozenset(cc_list), url=lead["jd_url"] or lead["post_url"], external_id=lid, posted_at=posted_at,
                raw={"row_extra": {"poster": lead["author"], "poster_url": lead["author_url"] or lead["post_url"]}})
    r = intake.admit(p, {x.strip() for x in override.split(",") if x.strip()})
    if r["status"] == "dropped":
        return (f"NOT ADDED: the radar's filters would drop this role: {'; '.join(r['why'])} [{', '.join(r['reasons'])}]. "
                f"Only on the user's word: add-role {lid} --countries {countries} --override {','.join(r['reasons'])}")
    if r["status"] == "known":
        return f"already known to the radar (ref {r['ref']}): not added again"
    _append(LEADS, {"id": lid, "status": "added", "ref": r["ref"], "at": _now()})
    board_sync.promote([r["ref"]])          # no-op when intake already queued the card
    return (f"added {lead['company']} — {lead['title']} as ref {r['ref']} (tier {r['tier']})"
            + (f", overriding: {','.join(r['overridden'])}" if r["overridden"] else "")
            + "; card queued. Next: `board_sync.py roles` opens it, then score-roles and sponsorship-check")


def _write_row(row: dict) -> None:
    fields, old = [], []
    if MATCHES.exists():
        with MATCHES.open(newline="", encoding="utf-8") as fh:
            reader = csv.DictReader(fh)
            fields, old = list(reader.fieldnames or []), list(reader)
    new_cols = [c for c in row if c not in fields]
    MATCHES.parent.mkdir(parents=True, exist_ok=True)
    if new_cols or not MATCHES.exists():
        fields += new_cols
        with MATCHES.open("w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=fields, restval="")
            w.writeheader()
            w.writerows(old)
    with MATCHES.open("a", newline="", encoding="utf-8") as fh:
        csv.DictWriter(fh, fieldnames=fields, restval="").writerow(row)


def stats(days: int = 30, now: datetime | None = None) -> dict:
    """What the posts brought, so the user can see whether the source earns its (small) risk."""
    cutoff = ((now or datetime.now(timezone.utc)) - timedelta(days=days)).isoformat()
    rows = [r for r in leads().values() if r.get("at", "") >= cutoff and r.get("post_url")]
    count = {k: sum(1 for r in rows if r["status"] == k) for k in ("new", "added", "known", "stale", "job_board")}
    count["logged"] = len(rows)
    count["people_known"] = len(people())
    return count


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    q = sub.add_parser("queries"); q.add_argument("--n", type=int); q.add_argument("--urls", action="store_true")
    ci = sub.add_parser("company-id"); ci.add_argument("company"); ci.add_argument("id")
    p = sub.add_parser("person"); ps = p.add_subparsers(dest="what", required=True)
    pa = ps.add_parser("add"); pa.add_argument("--name", required=True); pa.add_argument("--url", required=True)
    pa.add_argument("--company", required=True); pa.add_argument("--headline", default=""); pa.add_argument("--function", default="")
    pn = ps.add_parser("next"); pn.add_argument("--n", type=int)
    pr = ps.add_parser("read"); pr.add_argument("url")
    ld = sub.add_parser("lead"); ld.add_argument("--post-url", required=True); ld.add_argument("--author", required=True)
    ld.add_argument("--company", required=True); ld.add_argument("--title", required=True); ld.add_argument("--location", default="")
    ld.add_argument("--posted", default=""); ld.add_argument("--kind", choices=KINDS, default="person")
    ld.add_argument("--author-url", default=""); ld.add_argument("--reposter", default=""); ld.add_argument("--jd-url", default="")
    ld.add_argument("--open", dest="open_", choices=["yes", "no", "unknown"], default="unknown"); ld.add_argument("--note", default="")
    ar = sub.add_parser("add-role"); ar.add_argument("id"); ar.add_argument("--countries", required=True); ar.add_argument("--location", default=""); ar.add_argument("--override", default="")
    st = sub.add_parser("stats"); st.add_argument("--days", type=int, default=30)
    a = ap.parse_args(argv)
    if a.cmd == "queries":
        for line in next_queries(a.n):
            if a.urls:
                url, hint = search_url(line)
                print(f"{line}\n  {url}" + (f"\n  NOTE: {hint}" if hint else ""))
            else:
                print(line)
    elif a.cmd == "company-id":
        print(set_company_id(a.company, a.id))
    elif a.cmd == "person":
        if a.what == "add":
            print(add_person(a.name, a.url, a.company, a.headline, a.function))
        elif a.what == "next":
            for r in next_people(a.n):
                print(f"{r['name']} · {r['company']} · {r.get('headline', '')} · {r['url']} · last read {r.get('last_read') or 'never'}")
        else:
            print(mark_read(a.url))
    elif a.cmd == "lead":
        print(log_lead(a.post_url, a.author, a.company, a.title, a.location, a.posted, a.kind, a.author_url, a.reposter,
                       a.jd_url, a.open_, a.note)[0])
    elif a.cmd == "add-role":
        print(add_role(a.id, a.countries, a.location, override=a.override))
    else:
        print(json.dumps(stats(a.days)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
