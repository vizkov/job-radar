# 6. Tests

**What this is:** How the test suite is organised, the three rules every test follows, and what each test file checks.  
**Read first:** [5. Code reference](05-Code-reference.md)  
**Code:** `tests/`, `tests/conftest.py`, `tests/fixtures/`

```bash
pip install --require-hashes -r requirements-dev.txt   # once
pytest                                                 # ~10 s, fully offline
```

The public template runs the same suite before every publish (`public_template.py
publish`): a failing test blocks the publish.

## Three rules every test follows

1. **Offline.** No test touches the network. Live responses were recorded once into
   `tests/fixtures/`; HTTP clients are faked with `respx` (for httpx) or a fake runner;
   `gh` is replaced by a fake class that returns GitHub's JSON shapes.
2. **Against the sample settings, never the user's.** `tests/conftest.py` sets
   `JOBRADAR_PROFILE=examples` *before* any `jobradar` import, because `common.py` reads
   `config.json` at import time. So results don't depend on whatever is in `profile/`.
3. **Never write real files.** The autouse fixture `_isolate_tool_state` points every
   file path constant in `board_sync.py`, `jd_check.py`, `jd_prep.py`, `render_resume.py`,
   `session_brief.py`, `calibrate.py`, `referrals.py` and `sponsorship.py` at a temporary folder
   (JD packets, applications, scores, matches, logs, state), and gives `calibrate.py` a copy of
   the sample config. (It exists because earlier tests once wrote
   into the real `scores.jsonl` and `issue_map.json`.) When a tool gains a new file path,
   it must be a module constant and must be added here. `_no_politeness_delays` sets the
   HTTP pause and backoff to 0.

## Fixtures (`tests/fixtures/`)

| Folder | Holds | Recorded with |
|---|---|---|
| `ats/` | A Greenhouse board (Monzo), a Workday board and one detail response (Snyk) | `tools/record_fixture.py` |
| `eu/` | One response each from Bundesagentur, JobTech, EURES | saved by hand |
| `careers/` | Five real careers pages (MDSec, Code White, SySS, SEC Consult, NSIDE) | saved by hand |
| `alert_email/` | **Synthetic** alert emails per provider, plus spoofed, wrong-DKIM and unknown-sender cases | `make_fixtures.py` in that folder |

Most alert-email fixtures are modelled on each provider's layout. `alert_email/real/` holds a
sanitised copy of real LinkedIn alerts (2026-09: name, address and tracking tokens removed), which
exposed insight lines being read as job titles. Indeed and Glassdoor still have synthetic fixtures only.

## What each test file covers

| File | Module under test | Checks |
|---|---|---|
| `test_titles.py` | `common.title_matches` | Includes, excludes, student roles, German/Swedish titles |
| `test_countries.py` | `common.countries_for` | Country detection, including past false positives (Cambridge MA, New South Wales) |
| `test_matching.py` | `matching` | Normalization, aliases, **no fuzzy matches**, company field before hints |
| `test_paths.py` | `paths` | `profile/` wins over `examples/`; examples ship every settings file; aliases to non-targets ignored |
| `test_dedupe.py` | `dedupe` | Gender suffixes, cross-source collapse preferring ATS, different country/title stay apart, anonymous employers never merge |
| `test_health.py` | `health` | Flag after two bad runs; never-worked units ignored; whole-source failures |
| `test_enrichment.py` | `sponsors`, `tiering`, digest | Register lookups, whole-word prefix, overrides, canonical-first, tier arithmetic, sponsor bonus only for the role's country, freshness bonus |
| `test_board.py` | `board` | Payload title/labels/marker, hostile text neutralised, title cap, same ref across sources, baseline vs daily selection, queue dedupe, status has no titles, stale refs |
| `test_radar.py` | `radar` | One broken source doesn't stop others, filtering, seen by ID and content key, digest sections, per-source outside flag, Markdown injection, CSV header migration |
| `test_ats_adapter.py` | `sources/ats` | Greenhouse conversion, Workday detail URL and roll-up resolution |
| `test_eu_sources.py` | `bundesagentur`, `jobtech`, `eures`, `reed` | Parsing, JobTech phrase quoting, EURES title search, one failing query keeps the rest |
| `test_careers_page.py` | `sources/careers_page` | Each real page, hash stability, missing anchor is an error, JSON/RSS feeds, XML entity-expansion rejected, robots.txt |
| `test_alert_email.py` | `sources/alert_email` | Text and HTML cards, URLs rebuilt from IDs, tracking redirects, DKIM per provider, spoofed/foreign mail rejected, fetch failure surfaced, adapter never touches IMAP |
| `test_fetch_alert_emails.py` | `tools/fetch_alert_emails` | Read-only + PEEK, missing credentials reported not raised, **password never written or printed**, old mail cleared, runs with standard library only (a real `python -I -S` subprocess) |
| `test_verify_boards.py` | `verify_boards` | Companies with a careers page count as covered |
| `test_board_sync.py` | `board_sync` (issues) | Argument lists and caps, labels created once, crash midway keeps the rest queued, status create/pin/edit, issue map, stale labels, stage logging |
| `test_board_project.py` | `board_sync` (Project) | Setup creates fields and saves IDs, idempotent, adopts an existing Project, saved even if linking fails, set/close, fill, Posted date |
| `test_board_design.py` | `board_sync` (views) | No diff when matching, extra views allowed, changed columns reported, missing views created with clicks listed |
| `test_jd_prep.py` | `tools/jd_prep` | JSON-LD preferred, page text cleanup, Workday API, **LinkedIn never fetched**, pasted JD used, robots/JS shell, selection, scraper first with fallback, Amazon link rewrite |
| `test_jd_check_score.py` | `tools/jd_check score` | Valid passes; each invalid case rejected; quotes compared ignoring case/whitespace; no JD refuses; upsert |
| `test_tailor.py` | `jd_check tailor`, `render_resume` | Valid passes; invented IDs/numbers/names/links rejected; rewording warns; render requires validation of the exact file; outputs |
| `test_career.py` | `career`, `manual` | Parsing, contact tokens, comments ignored, duplicate IDs, missing CV message; manual lists everything; colour only when asked |
| `test_session_brief.py` | `tools/session_brief` | Counts and freshness, health checks, quiet alert emails, drag logging and follow-ups, hostile titles neutralised, gh/git via fakes, system updates, missed-run restart |
| `test_public_template.py` | `tools/public_template` | Code is public; private or unknown paths never published; renames; wiki link rewriting |
| `test_sponsorship.py` | `tools/sponsorship` | Valid verdict passes; non-verbatim quotes, banned sources, unbacked confirmed/no, bad verdicts rejected; card block escaped and replaced in place |
| `test_calibrate.py` | `tools/calibrate` | No change below the evidence threshold; one bounded step down or up; layout kept; cooldown; revert |
| `test_referrals.py` | `tools/referrals` | Contacts found loosely and in the user's order; ask/result logged and put on the card; unanswered asks after the wait |
| `test_docs_cover_code.py` | the overview docs | Every board field is in Concepts and the user guide's Board page; every skill in CLAUDE.md, page 4 and a "Things you can say" row (`USER_PHRASES`); every tool in the code reference; every config key in Configuration |
| `test_check_doc_links.py` | `tools/check_doc_links` | The repo's docs have no broken links; a link with a space or a missing target is caught |

## Faking `gh`

`board_sync.py` calls GitHub only through its `Gh` class. Tests pass a fake with the same
call signature that records every argument list and returns canned JSON: see
`FakeProjectGh` in `test_board_project.py`, `ViewsGh` in `test_board_design.py`. The
assertions then check the exact `gh` commands that would have run. `session_brief.py`
takes a `runner` parameter for the same reason.
