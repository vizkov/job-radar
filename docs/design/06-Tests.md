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
   `session_brief.py`, `calibrate.py`, `referrals.py`, `post_leads.py` and `sponsorship.py` at a temporary folder
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
| `test_hn_hiring.py` | `hn_hiring` | Top-level comments only, header parsing (company, role, location), prose and non-security posts dropped, no thread is a failed source |
| `test_eu_sources.py` | `bundesagentur`, `jobtech`, `eures`, `reed` | Parsing, JobTech phrase quoting, EURES title search, one failing query keeps the rest |
| `test_careers_page.py` | `sources/careers_page` | Each real page, hash stability, missing anchor is an error, JSON/RSS feeds, XML entity-expansion rejected, robots.txt |
| `test_cv_lint.py` | `tools/cv_lint` | Form and section rules from `writing-rules.md` |
| `test_app_mail.py` | `jobradar/application_mail`, `tools/app_mail`, `tools/fetch_application_mail` | Header filter (codes, alerts, bulk mail skipped), role matching (exact / company / ambiguous), receipts that mention interviews stay receipts, only exact-title rejections move automatically, ledger holds no message text, ack, scan-health line, fetch step read-only with PEEK and missing credentials reported not raised |
| `test_inbox_outcomes.py` | `tools/inbox_outcomes` | Pending applications, phrase classifier, seen ids |
| `test_master_clearance.py` | `tools/master_drift`, `jd_check tailor` | Submitted applications listed as `SUBMITTED`, not STALE (`--all` checks them); applications refused until the masters are cleared |
| `test_render_pdf.py` | `tools/render_pdf` | CV and cover-letter PDF layout |
| `test_alert_email.py` | `sources/alert_email` | Text and HTML cards, URLs rebuilt from IDs, tracking redirects, DKIM per provider, spoofed/foreign mail rejected, fetch failure surfaced, adapter never touches IMAP |
| `test_fetch_alert_emails.py` | `tools/fetch_alert_emails` | Read-only + PEEK, missing credentials reported not raised, **password never written or printed**, old mail cleared, runs with standard library only (a real `python -I -S` subprocess) |
| `test_verify_boards.py` | `verify_boards` | Companies with a careers page count as covered |
| `test_board_sync.py` | `board_sync` (issues) | Argument lists and caps, labels created once, crash midway keeps the rest queued, status create/pin/edit, issue map, stale labels, stage logging |
| `test_board_project.py` | `board_sync` (Project) | Setup creates fields and saves IDs, idempotent, adopts an existing Project, saved even if linking fails, set/close, fill, Posted date |
| `test_board_design.py` | `board_sync` (views) | No diff when matching, extra views allowed, changed columns reported, missing views created with clicks listed |
| `test_jd_prep.py` | `tools/jd_prep` | JSON-LD preferred, page text cleanup, Workday API, **LinkedIn never fetched**, pasted JD used, robots/JS shell, selection, scraper first with fallback, Amazon link rewrite |
| `test_jd_check_score.py` | `tools/jd_check score` | Valid passes; each invalid case rejected; quotes compared ignoring case/whitespace; no JD refuses; upsert |
| `test_consistency_check.py` | `tools/consistency_check` | Spelled-out and digit numbers match; a figure, year or name in only one document is flagged; CV-only figures; placeholders; the STAR picker table is ignored; exit codes |
| `test_tailor.py` | `jd_check tailor`, `render_resume` | Valid passes; invented IDs/numbers/names/links rejected; rewording warns; render requires validation of the exact file; outputs |
| `test_career.py` | `career`, `manual` | Parsing, contact tokens, comments ignored, duplicate IDs, missing CV message; manual lists everything; colour only when asked |
| `test_session_brief.py` | `tools/session_brief` | Counts and freshness, health checks, quiet alert emails, drag logging and follow-ups, hostile titles neutralised, gh/git via fakes, system updates, missed-run restart |
| `test_public_template.py` | `tools/public_template` | Code is public; private or unknown paths never published; renames; wiki link rewriting; only committed content is published (uncommitted edits are reported, not copied) |
| `test_sponsorship.py` | `tools/sponsorship` | Valid verdict passes; non-verbatim quotes, banned sources, unbacked confirmed/no, bad verdicts rejected; card block escaped and replaced in place |
| `test_calibrate.py` | `tools/calibrate` | No change below the evidence threshold; one bounded step down or up; layout kept; cooldown; revert |
| `test_post_leads.py` | `tools/post_leads` | Query rotation spreads over titles and rotates the phrase; people read longest ago first; lead status known / stale / job-board / new; add-role writes the row with the poster, queues the card and cannot add twice |
| `test_referrals.py` | `tools/referrals` | Contacts found loosely and in the user's order; ask/result logged and put on the card; unanswered asks after the wait |
| `test_docs_cover_code.py` | the overview docs | Every board field is in Concepts and the user guide's Board page; every skill in CLAUDE.md, page 4 and a "Things you can say" row (`USER_PHRASES`); every tool in the code reference; every config key in Configuration |
| `test_check_doc_links.py` | `tools/check_doc_links` | The repo's docs have no broken links; a link with a space or a missing target is caught |
| `test_workday_cache.py` | `jobradar/workday_cache` | The PC's Workday copy round-trips to Jobs, its age is computed, a missing or broken file reads as empty |
| `test_workday_paced.py` | `jobradar/workday_paced` | A 429 is retried and the search term sent; the retry limit gives a clear error; 404 is not retried; a refusal doubles the shared spacing and successes ease it; pages past the cap are not requested; the run budget defers instead of failing |
| `test_sweep_yield.py` | `tools/sweep_yield` | Reads are logged and reported per lane and company; old rows fall out of the window; the marks write the ledger next to their own state file and never the real one |
| `test_bamboohr_json.py` | `jobradar/bamboohr_json` | The JSON widget is parsed (departments, positions, duplicates dropped, missing URL built from the id) and the patched scraper still accepts the old HTML form |
| `test_dropped_alerts.py` | `radar.py` | Alert drops are logged with every failing filter, other sources and the default-off switch log nothing, and the file merges, keeps first-seen and expires old rows. |
| `test_cadence_reminders.py` | `tools/cadence` | One-off reminders: due on a date, listed until `reminder done`, then gone; adding the same id replaces it, bad input is rejected; the Scoring line is the last cadence line |
| `test_careers_queue.py` | `tools/careers_queue` | Only companies the radar cannot read are queued, in tier order; a read counts only once recorded and moves the company to the back of its tier; the search URL is remembered |
| `test_common.py` | `common.countries_for` | Places once dropped as unrecognised (Prague, Brno, Dutch and British towns) now resolve to their country; Poland still resolves to none |
| `test_cover_sync.py` | `jobradar/career`, `tools/cover_sync` | A cover block goes stale when a story or CV line it cites changes and is clean after `record_cover_sync`; blocks without metadata are ignored |
| `test_domain_profile.py` | `tools/domain_profile` | A valid `domains.json` has no problems; unknown IDs, a `strong` domain with under two pieces of evidence, leads that are not evidence, a missing `not_claimed` and bad quiz answers are rejected; lead IDs by sector come strongest first with no repeats |
| `test_draft_experiment.py` | `tools/draft_experiment` | The default compares two drafts and the ad-only draft is optional; briefs never say which draft is the tailored one and name every report file; `prep` refuses an unvalidated application |
| `test_intake.py` | `jobradar/intake` | Every filter that would drop a hand-added role is named and nothing is written; an override adds it, records why in `origin`, and a second add is `known`; `--dry-run` writes nothing; Greenhouse, Lever and Ashby links parse; manual fields build a posting the same filters judge |
| `test_jd_check.py` | `jd_check.recommendation_cap` | The recommendation band: apply at 70+, maybe at 50-69, skip below 50 or with a blocker; sponsorship `unlikely` caps at maybe and `no` at skip |
| `test_jd_cleanup.py` | `tools/jd_cleanup` | Skipped and rejected roles are trimmed after their retention while `score.json`, `meta.json` and `sponsorship.json` stay; a scored-skip role with no stage is trimmed but any stage protects it; `--dry-run` changes nothing |
| `test_jd_dupes.py` | `tools/jd_dupes` | The same ad under a different title is `SAME`; a different role sharing boilerplate is not; a short snippet is never `SAME`; the sentences only one ad has are reported |
| `test_sector_tier.py` | `matching.load_sectors`, `tiering.score` | The optional Sector column is read (empty without it); the sector bonus applies once, only to listed employers, never as a sum; no configured bonus changes nothing |
| `test_sweep_plan.py` | `tools/sweep_plan` | The pass is split 3/3/2/2 with each company once; a company the radar reads gets the post search only and an unreadable one alternates lanes; spare slots flow down from the short category and the total never exceeds the cap; a company with two lanes does not outrank single-lane ones |

## Faking `gh`

`board_sync.py` calls GitHub only through its `Gh` class. Tests pass a fake with the same
call signature that records every argument list and returns canned JSON: see
`FakeProjectGh` in `test_board_project.py`, `ViewsGh` in `test_board_design.py`. The
assertions then check the exact `gh` commands that would have run. `session_brief.py`
takes a `runner` parameter for the same reason.
