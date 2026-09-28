"""Step 1 of the job-radar pipeline: map target companies -> candidate ATS boards.

Sources (both cloned from GitHub):
  atss/ats-companies/*.csv   kalil0321/ats-scrapers   (name, slug, url)
  agg/data/*_companies.json  Feashliaa/job-board-aggregator (slugs only)

Output: candidates.csv — one row per (company, candidate board), with a review
flag. verify_boards.py then hits each board live to confirm it's the right
entity (i.e. it actually lists jobs in the target European countries).
"""
import csv, glob, json, os, re, sys, unicodedata
from collections import defaultdict, Counter

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from jobradar.paths import profile_path  # noqa: E402

TARGETS = sys.argv[1] if len(sys.argv) > 1 else str(profile_path("targets.tsv"))

def norm(s):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]", "", s.replace("&", "and"))

# Words describing a practice / region slice rather than the hiring entity.
# Applied independently, so "Accenture Security UK" -> "accenture".
SLICE_WORDS = ["uk", "nl", "ch", "ireland", "germany", "cyber", "security", "cyberdefense",
               "x-force", "redteam", "risk", "information", "digital intelligence",
               "group", "plc", "ag", "se", "ltd", "inc", "gmbh", "semiconductors",
               "banking group", "technologies", "labs"]

def candidates(company):
    raw = company.strip()
    parents = [p for p in re.findall(r"\((.*?)\)", raw) if "hq" not in p.lower()]
    base = re.sub(r"\(.*?\)", "", raw).strip()
    parts = [p.strip() for p in re.split(r"\s*/\s*", base) if p.strip()]
    variants = []
    for p in [raw, base] + parts:
        variants.append(p)
        t = p.lower()
        t = re.sub(r"\.(com|io|ai)$", "", t)
        variants.append(t)
        stripped = " ".join(w for w in re.split(r"\s+", t) if w not in SLICE_WORDS)
        for multi in ("digital intelligence", "banking group"):
            stripped = stripped.replace(multi, "")
        if stripped.strip():
            variants.append(stripped)
    keys = []
    for v in variants:
        k = norm(v)
        if len(k) >= 2 and k not in keys:
            keys.append(k)
    return keys, [norm(p) for p in parents if len(norm(p)) >= 2]

# ATSs that are regional to Asia / LatAm / job-board aggregators. A hit there
# for a European target is the wrong regional entity (e.g. EY -> EY China on Moka).
OFF_REGION = {"moka", "beisen", "beisen_legacy", "hrmos", "herp", "gupy", "keka",
              "darwinbox", "seek", "jobbankca", "infojobs_es", "jobs_cz", "mercor",
              "paylocity", "paycom", "ukg", "adp", "jazzhr"}

# Big employers that run their own careers APIs; ats-scrapers has first-party
# scrapers for these, and any third-party "board" under their name is noise.
FIRST_PARTY = {"amazonaws": "amazon", "amazon": "amazon", "apple": "apple",
               "google": "google", "meta": "meta", "uber": "uber"}

# Name collisions / wrong boards found on manual review: (company, board substring)
REJECT = [
    ("Fox-IT / NCC Group", "lever:foxit"),                   # Foxit PDF software
    ("Booking.com", "join_com"),                              # a Spanish hotel
    ("DNB", "dnb"),                                           # Dun & Bradstreet, not DNB bank
    ("Infosys", "workday"),                                   # "BLS", unrelated tenant
    ("eBay", "tcgplayer"),                                    # TCGplayer subsidiary board only
    ("Etsy", "workday:https://depop"),                        # Depop's board, not Etsy's
    ("Philips", "internal-job-postings"),                     # internal-only board
    ("Aviva", "gupy"),
    ("Microsoft", "workable"), ("Microsoft", "smartrecruiters"),
    ("Microsoft", "bamboohr"), ("Microsoft", "icims"),
    ("Siemens", "teamtailor"), ("Atlassian", "teamtailor"),
    ("Netflix", "teamtailor"), ("Netflix", "smartrecruiters"),
    ("Accenture", "bamboohr"), ("Accenture", "breezy"), ("Accenture", "join_com"),
    ("Accenture", "pinpoint"), ("Accenture", "smartrecruiters"), ("Accenture", "workable"),
    ("SAP", "bamboohr"), ("SAP", "smartrecruiters"),
    ("Wiz (Google)", "gupy"),
]

def rejected(company, key):
    base = re.sub(r"\s*\(.*?\)", "", company).strip()
    for c, pat in REJECT:
        if (company == c or base == c or base.startswith(c + " ") or company.startswith(c)) and pat in key:
            return True
    return False

WD = re.compile(r"^([^|]+)\|(wd\d+)\|(.+)$")
def agg_board(ats, s):
    """Aggregator slug -> (ats, scraper_slug, public_url)."""
    if ats == "workday":
        m = WD.match(s)
        if not m:
            return None
        t, wd, site = m.groups()
        url = f"https://{t}.{wd}.myworkdayjobs.com/{site}"
        return ("workday", url, url)
    urls = {"greenhouse": "https://job-boards.greenhouse.io/{}", "lever": "https://jobs.lever.co/{}",
            "ashby": "https://jobs.ashbyhq.com/{}", "bamboohr": "https://{}.bamboohr.com/careers",
            "icims": "https://careers-{}.icims.com"}
    if ats not in urls:
        return None
    return (ats, s, urls[ats].format(s))

# ---------- load indexes
atss = defaultdict(list)
for f in glob.glob("atss/ats-companies/*.csv"):
    ats = os.path.basename(f)[:-4]
    if ats in OFF_REGION:
        continue
    with open(f, newline="", encoding="utf-8", errors="ignore") as fh:
        for row in csv.DictReader(fh):
            name, url = (row.get("name") or "").strip(), (row.get("url") or "").strip()
            slug = (row.get("slug") or "").strip()
            scraper_slug = url if ats in ("workday", "phenom", "oracle") or not slug else slug
            for k in {norm(name), norm(slug.split("/")[0]) if slug and "://" not in slug else ""}:
                if len(k) >= 2:
                    atss[k].append(("ats-scrapers", ats, scraper_slug, url, name))

agg = defaultdict(list)
for f in glob.glob("agg/data/*_companies*.json"):
    ats = os.path.basename(f).split("_")[0]
    if ats in OFF_REGION:
        continue
    for s in json.load(open(f)):
        b = agg_board(ats, str(s))
        if not b:
            continue
        tenant = str(s).split("|")[0]
        for k in {norm(tenant), norm(re.sub(r"-\d+$", "", tenant))}:
            if len(k) >= 2:
                agg[k].append(("aggregator", b[0], b[1], b[2], tenant))

# ---------- match
with open(TARGETS, encoding="utf-8") as fh:
    lines = [l.rstrip("\n") for l in fh if l.strip()]
out, summary, seen = [], [], set()
for l in lines[1:]:
    cols = l.split("\t")
    company, offices = cols[0].strip(), (cols[1].strip() if len(cols) > 1 else "")
    if norm(company) in seen:
        continue
    seen.add(norm(company))
    keys, pkeys = candidates(company)

    fp = next((FIRST_PARTY[k] for k in keys if k in FIRST_PARTY), None)
    boards, via_parent = [], False
    if fp:
        boards = [("ats-scrapers", fp, fp, f"(first-party {fp} careers API)", company)]
    else:
        for idx in (atss, agg):
            for k in keys:
                if k in idx:
                    boards += idx[k]
                    break
        if not boards and pkeys:
            for idx in (atss, agg):
                for k in pkeys:
                    if k in idx:
                        boards += idx[k]; via_parent = True
                        break

    # dedupe by public URL, drop rejects
    uniq, dropped = {}, 0
    for b in boards:
        key = f"{b[1]}:{b[3].lower()}"
        if rejected(company, key) or rejected(company, f"{b[1]}:{b[4].lower()}"):
            dropped += 1; continue
        if b[3].lower() not in uniq:
            uniq[b[3].lower()] = b
        else:
            prev = uniq[b[3].lower()]
            if prev[0] != b[0]:
                uniq[b[3].lower()] = ("both",) + prev[1:]
    boards = list(uniq.values())

    if fp:
        status = "first-party API"
    elif not boards:
        status = "not covered"
    elif via_parent:
        status = "parent company board only"
    elif len(boards) == 1:
        status = "single board"
    else:
        status = "multiple boards - verify"
    summary.append((company, status))
    for b in boards or [(None,) * 5]:
        out.append({"company": company, "offices": offices, "status": status,
                    "source": b[0] or "", "ats": b[1] or "", "scraper_slug": b[2] or "",
                    "board_url": b[3] or "", "board_name": b[4] or ""})

with open("data/candidates.csv", "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(out[0].keys())); w.writeheader(); w.writerows(out)

c = Counter(s for _, s in summary)
print(f"{len(summary)} unique companies, {sum(1 for r in out if r['board_url'])} candidate boards")
for k, v in c.most_common():
    print(f"  {k:30} {v}")
