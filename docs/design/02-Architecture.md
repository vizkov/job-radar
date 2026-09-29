# 2. Architecture

**What this is:** The whole system on one page: the three places code runs, what each folder holds, and every data file with who writes and reads it.  
**Read first:** [1. Concepts](01-Concepts.md)  
**Code:** the whole repo, at folder level

## The whole system on one page

job-radar is a set of Python scripts plus instructions for Claude, living in one git
repo. Code runs in **three places**, and they talk to each other only through files
committed to the repo and through GitHub (issues, the board).

```
 ┌──────────────── 1. GitHub Actions (GitHub's servers, no human) ────────────────┐
 │ radar.yml, 3x a day                                                            │
 │   fetch_alert_emails.py ─▶ .alert_mail/*.eml   (only step with the mail secret)│
 │   radar.py ─▶ poll sources ─▶ filter ─▶ match ─▶ dedupe ─▶ new? ─▶ tier/sponsor│
 │           ─▶ data/matches.csv, state/*, digests/status.md, state/board_queue   │
 │   board_sync.py roles|stale|status ─▶ GitHub issues (labels) ─────────┐        │
 │   git commit + push (state, digests, matches)                         │        │
 │ verify.yml, monthly: verify_boards.py ─▶ boards.json                  │        │
 │ registers.yml, weekly: refresh_registers.py ─▶ data/registers/        │        │
 └───────────────────────────────────────────────────────────────────────┼────────┘
                                                                         ▼
                                GitHub Project board ◀── "Auto-add" workflow puts
                                (cards, fields, views)    every `role` issue on it
                                         ▲
 ┌──────────── 2. Claude Code session (user's machine, user's logins) ──┼─────────┐
 │ SessionStart hook: session_brief.py ─▶ git pull, read board, log drags,│        │
 │                                        start `board_sync.py fill` ─────┘        │
 │ Claude + CLAUDE.md + skills ─▶ runs tools: jd_prep, jd_check, render_resume,    │
 │                               board_sync set/views, radar --dry-run, …          │
 │                             ─▶ edits profile/, commits, pushes                  │
 │ Claude in Chrome (apply-assist) ─▶ pre-fills forms; the user clicks Submit      │
 └──────────────────────────────────────────────────────────────────────────────────┘
 ┌──────────── 3. git hook (user's machine, after each commit) ────────────────────┐
 │ .githooks/post-commit ─▶ public_template.py autopublish ─▶ public template repo │
 │                                                          ─▶ its Wiki tab        │
 └──────────────────────────────────────────────────────────────────────────────────┘
```

Why three places:

- **Finding roles must happen without the user**, so it runs in GitHub Actions on a
  schedule. Actions only has GITHUB_TOKEN, which can create issues but can't edit a
  personal Project. So the scheduled run attaches data as **labels**, and fills in
  nothing on the board itself.
- **Judgement needs Claude**, and Claude runs on the user's subscription only inside a
  Claude Code session on their machine, with no API key. So scoring, tailoring and
  setting **board fields** happen there, using the user's own `gh` login.
- **The public template must stay current** with code changes made in the private
  copy, without ever receiving private data. A git hook does that after each commit.

## Folders

| Folder / file | What's in it | Public? |
|---|---|---|
| `README.md` | The front door: what it is, how to start, where to read next | public |
| `radar.py` | The scheduled pipeline's entry point | public |
| `verify_boards.py` | Checks candidate ATS boards live, writes `boards.json` | public |
| `jobradar/` | The Python package (`__init__.py` is empty; it only marks the folder as a package): data model, matching, dedupe, tiering, sponsors, board payloads, career docs | public |
| `jobradar/sources/` | One module per source adapter, plus the registry that runs them | public |
| `tools/` | Command-line tools Claude (or a workflow) runs: board sync, JD prep and checks, rendering, publishing, the session brief | public |
| `.github/workflows/` | The three scheduled workflows | public |
| `.claude/` | `settings.json` (the SessionStart hook) and `skills/` (Claude's procedures) | public |
| `CLAUDE.md` | Claude's operating manual for this repo | public |
| `.githooks/` | The post-commit hook that publishes code to the template | public |
| `docs/wiki/` | User guide: `Home.md`, `Your-part.md`, `Using-it.md`, `Board.md` (also mirrored to the GitHub Wiki tab) | public |
| `docs/reviews.md` | Weekly system-review notes about the user's search | **private** (the one private file under `docs/`) |
| `docs/design/` | These pages | public |
| `examples/` | Generic sample settings and career docs, used when `profile/` doesn't have a file, and by the tests | public |
| `tests/` | Offline tests and recorded fixtures | public |
| `requirements*.in` / `.txt` | Dependencies: `.in` lists what we want, `.txt` is the hash-locked result | public |
| `profile/` | The user's real settings, career docs, applications, board coordinates | **private** |
| `state/` | What the pipeline remembers between runs | **private** |
| `digests/` | Per-run reports | **private** |
| `data/` | Run output and derived data | **private** (see below) |
| `boards.json` | The verified ATS boards for the user's targets | **private** |
| `work/` | Scratch space: fetched JDs, Claude's drafts, logs. Not committed at all (`.gitignore`) | **private, local only** |
| `.alert_mail/` | Alert emails saved during a run. Not committed | **private, local only** |
| `atss/`, `agg/` | Clones of two public company→ATS indexes, used once at setup | local only |

`data/` detail: `data/registers/` is public government data, but each copy refreshes it
weekly, so shipping it in the template would cause merge conflicts. It's treated as
private for publishing purposes. Everything else in `data/` is derived from the user's
targets or activity.

The authoritative private/public rules are the `PRIVATE` and `PUBLIC` lists in
`tools/public_template.py`: a file is published only if it matches `PUBLIC` **and**
doesn't match `PRIVATE`.

## Every data file: who writes it, who reads it

### Settings (`profile/`, falling back to `examples/`)

| File | Holds | Written by | Read by |
|---|---|---|---|
| `config.json` | Countries, title include/exclude, tier weights, sponsor thresholds, board options, timeouts | Claude (`tune-radar`) | almost everything via `common.py: CONFIG` |
| `sources.yaml` | Which sources run and their options | Claude | `sources/__init__.py: load_sources_config()` |
| `targets.tsv` | Target companies (`Company<TAB>Offices`) | Claude (`setup`, `tune-radar`) | `matching.py`, `build_candidates.py` |
| `aliases.csv` | `alias,canonical` spellings | Claude | `matching.py` |
| `overrides.csv` | Extra ATS boards: `company,careers_url,ats,slug` | Claude, `discover_boards.py --apply` | `verify_boards.py` |
| `board_blocklist.csv` | Boards never to poll: `ats,slug,board_url,reason` | Claude | `verify_boards.py` (`load_blocklist`) |
| `careers_pages.yaml` | Careers pages without an ATS, with CSS selectors | Claude | `sources/careers_page.py` |
| `sponsor_overrides.csv` | Pinned sponsor-register matches | Claude | `sponsors.py` |
| `career/master_resume.md`, `stories.md`, `cover_blocks.md` | The user's CV lines, STAR stories and cover paragraphs, each with an ID | Claude (converted from the user's CV, confirmed by them) | `career.py` → `jd_check.py`, `render_resume.py`, skills |
| `applications/<folder>/` | Per-application `tailored.json`, `validated.sha256`, `resume.md`, `cover_letter.md` (plus `resume.docx` only when asked), `submitted.md` | Claude, `jd_check.py`, `render_resume.py` | the user, `apply-assist` |
| `network.csv` | Who can help where: `name,company,added`, one row per person per company. Nothing about how people are related or what they do (the user's choice) | Claude (`referrals` skill), from what the user says | `tools/referrals.py` |
| `board.json` | The Project's owner, number, node ID, URL, field IDs and option IDs | `board_sync.py setup-project` | `board_sync.py`, `session_brief.py` |

### Pipeline memory (`state/`, committed by the scheduled run)

| File | Holds | Written by | Read by |
|---|---|---|---|
| `seen.json` | `{key: last-seen date}` for every posting ID and content key reported; entries older than 120 days are pruned | `radar.py` | `radar.py` (what's new), `board.py: stale_refs()` |
| `health.json` | `{"source|unit": {last_ok_count, bad_streak, label}}` | `radar.py` via `health.py` | `radar.py` |
| `board_queue.json` | Payloads waiting to become issues | `radar.py` (adds), `board_sync.py roles` (removes) | `board_sync.py roles`, `status` |
| `issue_map.json` | `{ref: issue number}` | `board_sync.py roles`, `backfill-map` | `radar.py` (stale check), `board_sync.py stale` |
| `stale_roles.json` | `{stale: [refs], alive: [refs]}` from the latest healthy run | `radar.py` | `board_sync.py stale` |
| `stale_flagged.json` | Refs currently labelled `possibly-closed` | `board_sync.py stale` | `board_sync.py stale` |

### Output (`data/`, `digests/`)

| File | Holds | Written by | Read by |
|---|---|---|---|
| `data/matches.csv` | One row per new role ever found: ref, date, company, title, location, countries, url, source, posted, on_list, tier, score, score_reasons, uk/nl sponsor, also_on, ats, ats_slug, external_id | `radar.py: append_matches()` | `jd_prep.py`, `session_brief.py`, `board_sync.py` (Posted fallback), Claude |
| `data/scores.jsonl` | One JSON line per scored role: fit_score, recommendation, blockers, missing requirements, summary, injection flag | `jd_check.py score` | `session_brief.py`, `jd_prep.py` (skip scored), `cv-review` |
| `data/pipeline_log.jsonl` | Every stage change: `{ref, field, value, by: claude|board, at, from?, note?}` | `board_sync.py set`, `session_brief.py` | `session_brief.py` (follow-ups) |
| `data/referrals.jsonl` | Every referral ask and answer: `{ref, person, relation?, channel?, status: asked|referred|declined|no_reply|finding|none|not_needed, note, at}` | `tools/referrals.py` | `tools/referrals.py`, `session_brief.py` (reminders) |
| `data/sponsorship.jsonl` | One checked sponsorship verdict per role, with evidence and URLs | `tools/sponsorship.py record` | `sponsorship.py company` (reuse), Claude |
| `data/calibration_log.jsonl` | Every automatic tier-weight change: keyword, from, to, evidence, time; reverts too | `tools/calibrate.py` | `calibrate.py` (cooldown, revert) |
| `data/usage_log.jsonl` | Per scoring batch: roles, JD characters, the user's `/usage` before and after (to put a real cost figure in the guide) | Claude (`score-roles`, first 3 batches) | Claude |
| `data/pipeline_snapshot.json` | `{ref: stage}` at the last session start, to detect cards the user dragged | `session_brief.py` | `session_brief.py` |
| `data/registers/uk_sponsors.csv`, `nl_sponsors.csv`, `meta.json` | UK and NL sponsor registers | `refresh_registers.py` (weekly workflow) | `sponsors.py` |
| `data/candidates.csv` | Every candidate ATS board per target (from public indexes) | `build_candidates.py` | `verify_boards.py` |
| `data/verified_boards.csv` | Per board: fetched OK?, jobs total, jobs in target countries | `verify_boards.py` | Claude (diagnosis) |
| `data/coverage_report.csv` | Per target: VERIFIED or why not, kept/rejected boards | `verify_boards.py` | `discover_boards.py`, Claude |
| `boards.json` | `[{companies, ats, slug, url}]`: the boards the `ats` source polls | `verify_boards.py` | `sources/ats.py` |
| `digests/YYYY-MM-DD.md`, `latest.md` | Human-readable run report, grouped by tier and company | `radar.py` | Claude |
| `digests/status.md` | Counts and source health (no job titles) | `radar.py` | `board_sync.py status` (→ the "Radar status" issue), `session_brief.py` |

### Local only (never committed)

These live only on the machine where they were made: a fresh clone or a second computer
starts them from scratch (so both review timers reset).

| File | Holds | Written by |
|---|---|---|
| `work/jd/<ref>/jd.txt`, `meta.json`, `packet.md` | A role's JD text, facts, and the packet Claude reads | `jd_prep.py` (or the user pastes `jd.txt`) |
| `work/jd/<ref>/score.json` | Claude's fit assessment, before validation | Claude |
| `work/jd/<ref>/sponsorship.json` | Claude's sponsorship verdict and evidence, before validation | Claude |
| `work/.last_calibration` | When calibration last ran | `session_brief.py` |
| `work/discovered_boards.csv` | Proposed boards for uncovered targets | `discover_boards.py` |
| `work/.last_session`, `.fill_started`, `board_fill.log` | Timestamps and logs for the session brief | `session_brief.py` |
| `.claude/settings.local.json` | Personal Claude Code settings; never copied to the template (`NEVER_COPY`) | the user / Claude Code |
| `work/.last_docs_review` | When the last docs review happened | `session_brief.py` (first start), Claude (`docs-review` skill) |
| `work/.last_review` | When the last weekly review happened | Claude, at the end of the `system-review` skill (no tool writes it) |
| `.alert_mail/*.eml`, `_status.json` | This run's alert emails and fetch status | `fetch_alert_emails.py` |

## External services

| Service | Used for | Auth |
|---|---|---|
| Company ATS APIs (via `ats-scrapers`) | Job lists and descriptions | none (public) |
| Bundesagentur, JobTech, EURES APIs | Job search | none / published public key |
| Company careers pages | Job lists | none; robots.txt respected |
| Reed Jobs API | UK job search | free API key, GitHub secret `REED_API_KEY`, radar step only |
| Gmail IMAP | Alert emails | app password, GitHub secret, one workflow step only |
| gov.uk content API, ind.nl | Sponsor registers | none |
| GitHub (issues, Projects, Actions, GraphQL) | Board, scheduling | GITHUB_TOKEN in Actions; the user's `gh` login locally |
| LinkedIn, Indeed, Glassdoor | **Never fetched.** Only their emails are read | n/a |

## Dependencies

Runtime (`requirements.in`, hash-locked in `requirements.txt`): `ats-scrapers` (fetches
ATS boards; the biggest piece of third-party code), `beautifulsoup4` (needed by
ats-scrapers but not declared by it), `httpx` (HTTP), `pyyaml`, `selectolax` (fast HTML
parsing, no JavaScript), `defusedxml` (safe XML), `rapidfuzz` (fuzzy name matching).
Optional: `python-docx` (`requirements-career.txt`, CV rendering, local only),
`playwright` (`requirements-browser.txt`, JavaScript pages, local only). Dev: `pytest`,
`respx` (fakes httpx responses).

Several tools are **standard-library only** on purpose: `fetch_alert_emails.py` and
`alert_providers.py` (they run next to the mail secret, before any package is installed),
`session_brief.py`, `board_sync.py`, `public_template.py` and `manual.py` (they run with
whatever `python` is on the machine, outside the virtualenv).
