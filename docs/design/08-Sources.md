# 8. Sources

**What this is:** Where roles come from: the six adapters, what each costs to run, what breaks, and how to add a company or a careers page.  
**Read first:** [3. A scheduled run](03-Scheduled-run.md)  
**Code:** `jobradar/sources/`, `verify_boards.py`, `boards.json`, `profile/sources.yaml`, `profile/careers_pages.yaml`, `profile/overrides.csv`

How the adapters are built is in the [code reference](05-Code-reference.md#53-jobradarsources-the-adapters); this page is about
running them. All sources are configured in `sources.yaml`. Each has `enabled`, a
`timeout_seconds` cap for the whole source, and source-specific settings. A
source that crashes or times out is reported on the Radar status card; the others still run.

Test any source live without writing state:

```bash
python radar.py --dry-run --source <name> [--include-outside]
```

| Source | Default | Run time | Credentials | Covers |
|---|---|---|---|---|
| `ats` | on | ~4 min | none | Every verified company board in `boards.json` (Greenhouse, Workday, Lever, Ashby, …) |
| `bundesagentur` | on | ~10 s | none (public key) | Germany's public employment service |
| `jobtech` | on | ~10 s | none | Sweden's public employment service |
| `eures` | on | ~1–2 min | none | EU portal: NL, IE, CH, SE (no UK; DE via bundesagentur) |
| `careers_page` | on | ~10 s for 5 pages | none | Company careers pages without an ATS (`profile/careers_pages.yaml`) |
| `alert_email` | off in `examples/`; on once the secrets exist | not measured yet | Gmail app password (dedicated mailbox safer) | LinkedIn / Indeed / Glassdoor alert emails; see [Job-alert emails](12-Job-alert-emails.md) |

Run times measured 2026-09-27 on a home connection.

## ats — company job boards

Polls every board in `boards.json` via the pinned `ats-scrapers` package.
`verify_boards.py` builds `boards.json` from `data/candidates.csv` +
`profile/overrides.csv`, keeping only boards that currently list jobs in the user's
target countries.

**Coverage.** `data/coverage_report.csv` says, per target, whether a live board was
found. Most large employers are covered by their ATS; the gaps are usually banks and
insurers with custom portals, and small consultancies. For those: a careers page
(`careers_page`), job-alert emails (`alert_email`), or `tools/discover_boards.py`, which
proposes boards to add.

- **Add a company's board:** put `company,careers_url` in `profile/overrides.csv`
  (Greenhouse/Lever/Ashby/Workday/SmartRecruiters/Personio/Recruitee/Teamtailor/
  Workable/… URLs are auto-detected), then re-run `verify_boards.py`.
- **Workday "2 Locations" postings:** Workday hides multi-office locations in its
  list API. For postings whose title matches, the adapter fetches the job's detail
  page to get the real offices (a handful of extra requests per run).
- **What breaks:** a company moves ATS → its board goes empty → flagged in the
  status card after 2 runs; the monthly `verify.yml` re-maps boards. Upstream scraper
  changes are contained by pinning `ats-scrapers`; bump deliberately.

## bundesagentur / jobtech / eures — EU public job APIs

Keyword searches against public APIs (own small clients; the `ats-scrapers`
versions download the entire site, ~1M jobs for Bundesagentur).

- `queries` only narrow what's downloaded; `config.json`'s title filter decides
  what's reported. `days` is the look-back window; `max_pages` caps downloads.
- `health_query` is a broad "canary" search that should never be empty; if it
  returns nothing for 2 runs the source is flagged. Narrow queries returning 0
  is normal and not flagged.
- **Expect little on-list value.** When tested, results were dominated by staffing
  agencies (FERCHAU, Randstad, Akkodis) and non-target employers, with 1 on-list
  match per source. Their value is DE/SE/NL coverage in "Outside your list".
- **EURES Netherlands hides employer names**, so those listings can never match
  the user's list. `eures.include_outside_list: true` shows them (~50–80 in-scope NL
  roles a week when tested) without turning on outside-list for every source.
- **What breaks:** these are unauthenticated public endpoints; the EURES one is
  the portal's own undocumented API and the most likely to change shape. A change
  shows up as query errors plus a flagged canary.

## careers_page — companies without an ATS

For companies like MDSec, SySS or Code White that list jobs on their own
website. Each page is an entry in `profile/careers_pages.yaml`; the file's header
documents every field.

**First, check for a hidden ATS.** View the page source and search for
greenhouse, lever, ashby, workable, personio, recruitee, teamtailor or
smartrecruiters. If one is there, add the ATS URL to `profile/overrides.csv`
instead (that's how usd AG and Bridewell were added). ATS boards don't break
when the website is redesigned.

Three modes:

| Mode | Use when | Result |
|---|---|---|
| `selector` | The page lists jobs as repeated HTML blocks | Real postings (title, link, location), filtered like any other source |
| `feed` | The site offers an RSS/Atom or JSON job feed | Same, more robust than selectors |
| `hash` | Jobs can't be parsed, or the page says "no openings" | One "Careers page changed: X" entry whenever the listing section changes |

### Adding a selector page

1. Open the page, right-click a job title → Inspect. Find the element that wraps
   one whole job (`item`), the title inside it (`title`), the link (`link`),
   and optionally the location (`location`).
2. Pick an `anchor`: something that stays on the page even when there are no
   jobs (e.g. the "Current positions" section). If it disappears, the status card
   reports "page layout changed" instead of silently showing nothing.
3. Test it: `python radar.py --dry-run --include-outside --source careers_page`.
4. Set `tested:` to today's date.

### Seeded pages (tested 2026-09-27)

| Company | Mode | Notes |
|---|---|---|
| MDSec | selector | 2 roles listed; apply links go to MDSec's Indeed page |
| SySS | selector | Job ads are PDFs; `expect_jobs: true` because it always lists something |
| Code White | selector | One-page listing; links are `careers/#<section-id>` |
| SEC Consult | selector | Mostly Vienna (Austria is an extra country, off by default) |
| NSIDE Attack Logic | hash | Page says all positions are filled; any change is worth a look |

Looked at but not seeded: Pen Test Partners (careers page times out for
non-browser clients), Synacktiv (job list loaded by JavaScript, France only),
Secura (now Bureau Veritas Cybersecurity), Computest (now Defion), Cure53 (no
jobs section). For these, LinkedIn job alerts are the better route.

### JavaScript-rendered pages

Mark a page `render: js` to load it in headless Chromium. That needs the
optional browser extra, which is **local only** (keeps the scheduled Actions run
light):

```bash
pip install --require-hashes -r requirements-browser.txt
playwright install chromium
```

In GitHub Actions these pages show up as errors ("needs Playwright") rather
than being silently skipped.

**What breaks:** site redesigns (anchor missing → "page layout changed"; or an
`expect_jobs` page going empty → flagged after 2 runs), bot protection
(timeouts/403 in the error column), and robots.txt changes (reported as
"disallowed by robots.txt").
