# job-radar

A job-search assistant for AppSec / product security / pentest / security consulting
roles in Europe. It has **two interfaces**:

1. **Claude**: talk to it in Claude Code, in your private copy of this repo. It acts as
   your recruitment consultant and operates the system: setup, briefings, fit scoring
   against your CV, tailored CVs and cover letters, tracking, tuning, fixes.
2. **A GitHub Projects board**: every new role appears as a card that moves from New →
   Shortlisted → Applied → Interview → Offer.

Underneath, a GitHub Action (three times a day) scans company job boards, careers pages, EU public job
portals and (optionally) LinkedIn/Indeed/Glassdoor alert emails, keeps new roles at your
target companies, tiers them, tags UK/NL visa-sponsor status and puts them on the board.
Scoring and tailoring run in Claude Code on your Claude subscription; **no API key**.

Also, without being asked: each Claude Code session starts with a brief (new roles,
stage changes you made on the board, follow-ups due, broken sources, weekly review due).
Claude can fill application forms in Chrome for you to check and submit
(`apply-assist`), proposes job boards for targets with none (`tools/discover_boards.py`),
and lists everything it can do on request (`/manual`).

Start here: [docs/wiki/Home.md](docs/wiki/Home.md) · what to say to Claude:
[docs/wiki/Using-it.md](docs/wiki/Using-it.md). How it works inside, file by file:
[docs/design/README.md](docs/design/README.md).

Built on [ats-scrapers](https://github.com/kalil0321/ats-scrapers) (ATS fetching) plus
company→board mappings from ats-scrapers and
[job-board-aggregator](https://github.com/Feashliaa/job-board-aggregator).

## How it works

```
sources.yaml ──▶ every enabled source runs under its own timeout; one failing never stops the rest
                 ats · bundesagentur · jobtech · eures · careers_page · alert_email
                        ▼
config.json  ──▶ target country AND title include AND NOT title exclude
                        ▼
targets.tsv + profile/aliases.csv ──▶ match employer to your list (exact, after normalizing)
                        ▼
dedupe (company + title + country) ──▶ one entry per role, linked to the company's own ATS if seen there
                        ▼
state/seen.json ──▶ only postings not reported before
                        ▼
sponsor registers + tier rules ──▶ data/matches.csv + one issue per role ──auto-add──▶ Projects board
                                  + pinned "Radar status" issue (counts, broken sources)
```

And on demand, in Claude Code:

```
jd_prep.py (fetch JD) ─▶ Claude scores it against profile/career/ ─▶ jd_check.py score (validates) ─▶ board Fit
Claude tailors CV from your own lines ─▶ jd_check.py tailor (no invented content) ─▶ render_resume.py (.docx/.md)
```

## Sources

| Source | Default | Run time* | Needs | What can break |
|---|---|---|---|---|
| `ats`: your verified company ATS boards (`boards.json`) | on | ~4 min | nothing | Company moves ATS → board flagged after 2 empty runs; monthly `verify.yml` re-maps |
| `bundesagentur`: German public job service | on | ~15 s | nothing (public API key) | API change → canary query flagged |
| `jobtech`: Swedish public job service | on | ~15 s | nothing | API change → canary query flagged |
| `eures`: EU portal (NL, IE, CH, SE) | on | ~1 min | nothing | Undocumented endpoint, most likely to change shape |
| `careers_page`: sites without an ATS (5 security consultancies in the examples) | on | ~15 s | nothing | Site redesign → "page layout changed" or empty page flagged |
| `alert_email`: LinkedIn / Indeed / Glassdoor alert emails | on (needs secrets) | not measured | Gmail app password (GitHub secret); a dedicated mailbox is safer | Provider changes its email layout → flagged |

\*Measured 2026-09-28. Sources run concurrently, so a full run takes about as
long as `ats`, ~4–5 minutes.

Enable/disable and tune each in `profile/sources.yaml`. Test one live without touching state:

```bash
python radar.py --dry-run --source <name> [--include-outside]
```

Per-source setup and failure modes: [docs/design/Sources.md](docs/design/Sources.md).
Alert-email setup: [docs/design/Job-alert-emails.md](docs/design/Job-alert-emails.md).

**Not built, on purpose:** anything that logs in to LinkedIn or another portal,
auto-apply, and scraping LinkedIn/Indeed/Glassdoor (e.g. python-jobspy). The
alert emails cover the same postings without breaking those sites' terms. See the
wiki for why jobspy was dropped.

## Coverage

`verify_boards.py` writes `data/coverage_report.csv`: one row per target company,
saying whether a live ATS board was found. In practice most large employers are
covered by their ATS; the gaps are banks/insurers with custom portals and small
consultancies. For those, watch the careers page (`careers_page`) or set up
LinkedIn/Indeed alerts (`alert_email`).

## Public template, private copy

This repo is a **public template**: code, docs, tests and generic sample settings
in `examples/`. **Run it from a private copy**, because the digests, the daily
issues, `data/matches.csv` and the Actions logs describe your job search, and in
a public repo all of those are public. GitHub Actions secrets are never copied
to forks or clones, but nothing else is protected.

- Your settings go in `profile/` (same file names as `examples/`). Each file is
  read from `profile/` if present, else from `examples/`, so `git pull template main`
  never conflicts with your settings.
- Every workflow starts with a **privacy guard** that skips the run in a public
  repo (override: repository variable `JOB_RADAR_ALLOW_PUBLIC=true`).
- Workflows run with `--quiet`, so the digest never appears in Actions logs.
- `python tools/public_template.py check` fails if a repo tracks private files;
  `export <dir>` builds a clean template tree.

Don't fork (a fork of a public repo can't be private): clone and push to a new
private repo. Steps: [docs/design/Setup.md](docs/design/Setup.md).

## Setup

```bash
git clone <this template> my-job-radar && cd my-job-radar
git remote rename origin template && git remote add origin <your EMPTY private repo>
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install --require-hashes -r requirements.txt
mkdir -p profile && cp examples/targets.tsv examples/config.json profile/   # then edit them
python tools/refresh_registers.py   # sponsor registers, ~1 min
python verify_boards.py             # 15–40 min, live; writes boards.json
python radar.py --dry-run           # full run, nothing written
```

Or just open Claude Code in your private copy and say **"set this up for me"**: it
does all of the above with you (docs/design/Setup.md).

| Workflow | When | What |
|---|---|---|
| `radar.yml` | 3x daily: 08:17, 14:17, 20:17 IST | fetch alert mail, poll sources, add role cards, update status, commit |
| `verify.yml` | 1st of month | re-verify ATS boards |
| `registers.yml` | Mondays | refresh UK/NL sponsor registers |

All three share one concurrency group, so their commits never race.

## Tuning

- `profile/config.json`: the single source of filter truth: countries, title
  include/exclude (whole-word; `*` for prefixes), tier weights, sponsor-match
  thresholds. See [Configuration](docs/design/Configuration.md) and
  [Tiers and sponsorship](docs/design/Tiers-and-sponsorship.md).
- `profile/aliases.csv`: employer spellings that should count as a target.
- `profile/overrides.csv`: extra ATS careers URLs (re-run `verify_boards.py`).
- `profile/careers_pages.yaml`: careers pages without an ATS.
- `profile/sponsor_overrides.csv`: pin a company's sponsor-register entry.

## Tests

```bash
pip install --require-hashes -r requirements-dev.txt
pytest          # offline, ~10 s; always runs against examples/
```

Adapters are tested against responses recorded under `tests/fixtures/`. The
alert-email fixtures are **synthetic** until real exported alerts are added.

## Dependencies

All pinned with hashes (`requirements.txt`, generated from `requirements.in`) and
installed with `--require-hashes`; GitHub Actions are pinned to commit SHAs.

| Package | Why |
|---|---|
| ats-scrapers 0.3.0 | Fetches all ATS boards (existing) |
| beautifulsoup4 | Imported by ats-scrapers 0.3.0 but not declared by it; without it the scrapers fail to import |
| pyyaml | `sources.yaml` and `careers_pages.yaml` (comments next to risky flags; `safe_load` only) |
| selectolax | Parses careers pages and alert-email HTML; fast, no JS execution |
| defusedxml | Careers-page RSS/Atom feeds; the stdlib XML parsers aren't safe on untrusted input |
| rapidfuzz | Fuzzy company-name matching against the sponsor registers |
| pytest, respx | Dev only: offline tests; respx mocks httpx |
| python-docx | Optional, local only (`requirements-career.txt`): renders the ATS-safe `resume.docx` |
| playwright | Optional, local only (`requirements-browser.txt`): JS-rendered careers pages |

## Security notes

- The daily workflow uses only the built-in `GITHUB_TOKEN` (contents + issues write on
  this repo). The optional alert-email source adds one secret: a Gmail app password
  (ideally for a mailbox that only holds job alerts). It reaches only a standard-library-only fetch
  step that runs before any third-party package is installed.
- Claude's output is checked too: fit-score blockers must quote the job ad verbatim,
  and a tailored CV may only use your own lines (by ID) with no new numbers, links or
  contact details.
- Job ads and emails are untrusted input. They're markdown-escaped in the digest,
  alert emails need a provider DKIM pass, and links are rebuilt from job IDs. Any
  future LLM step must follow `jobradar/untrusted.py`.
- Review the upstream diff before bumping `ats-scrapers`.

More: [docs/design/Security-model.md](docs/design/Security-model.md).
