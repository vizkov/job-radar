# 5.4 Tools: the board, the session and publishing

**What this is:** The tools Claude and the session hook run: GitHub issues, the Project board and its views, the cadence ledger, the session brief, publishing to the public template, referrals, LinkedIn post leads, sponsorship verdicts and tier tuning.  
**Read first:** pages [4](04-Claude-session.md) and [11](11-Board-internals.md)  
**Code:** `tools/board_sync.py`, `cadence.py`, `session_brief.py`, `public_template.py`, `manual.py`, `referrals.py`, `post_leads.py`, `sponsorship.py`, `calibrate.py`  

Part of the [5. Code reference](05-Code-reference.md) (the index of every file and function).

---

## `tools/board_sync.py`: GitHub issues and the Project (standard library only)

Sub-commands: `roles`, `status`, `stale`, `backfill-map` (Actions or local);
`setup-project`, `fill`, `set`, `views`, `design-diff`, `describe`, `refresh-bodies`, `archive` (local, need the `project` scope;
`archive_skipped(gh, max_n=ARCHIVE_MAX)` archives up to 40 cards per run with Stage = Skipped, or Stage = Rejected for more than `REJECTED_ARCHIVE_DAYS` (30) days (read from the stage log by `_rejected_on`), via `gh project
item-archive`, idempotent because `item-list` omits archived items; `session_brief.start_archive` runs it once a day);
`promote <ref> …` (local, queues cards for recorded roles; then `roles`).

| Name | Is |
|---|---|
| Path constants | `QUEUE`, `ISSUE_MAP`, `STALE`, `FLAGGED`, `PIPELINE_LOG`, `STATUS_MD`, `MATCHES`, `BOARD_FILE`: every file it touches (tests redirect them all). |
| `FIELDS`, `DATE` | The board's custom fields and their types/options (`DATE` marks a date field). |
| `STATUS_LABEL`, `SPACING_SECONDS` | `radar-status` (the status issue's label); 2 s between issue creations. |
| `LABEL_COLORS` | Colours for the labels job-radar creates: `role`, `radar-status`, `possibly-closed` (anything else is blue). |
| `REGISTER_TO_SPONSOR` | Register label → provisional Sponsor value: yes → Licensed, unknown → Unclear, no → Unlikely. |
| `FINAL_STAGES` | Offer, Rejected, Skipped: setting one closes the issue. |
| `_match_rows()`, `_row_sponsor(row)` | `ref → matches.csv row`; the Sponsor option from a row's register match for its first country (GB → `uk_sponsor`, NL → `nl_sponsor`). |
| `Gh` | Runs `gh` with an argument list (no shell), reading its output as UTF-8 (Windows' default code page would garble text written back to GitHub); `dry_run` prints instead. Tests replace it. |
| `_body_file(text)` | Writes issue text to a temp file for `--body-file`. |
| `ensure_labels(gh, labels)` | `gh label create --force` for each. |
| `sync_roles(gh, max, sleep)` | Queue → issues, saving the queue after each (crash-safe). |
| `_load`, `_remember_issue` | JSON read helper; record `ref → issue number`. |
| `backfill_map(gh)` | Rebuild `issue_map.json` from every role issue's hidden marker. |
| `sync_stale(gh)` | Add/remove `possibly-closed`. It also labels issues already closed (the issue map holds every ref); harmless, since closed cards are out of the working views. |
| `log_stage(ref, field, value, by, note="")` | Append to `data/pipeline_log.jsonl`. |
| `sync_status(gh)` | Update or create-and-pin the "Radar status" issue. |
| `gh_json`, `load_board`, `_read_fields`, `_save_board` | JSON output of gh; read `profile/board.json`; field and option IDs; save board.json. |
| `setup_project(gh, repo)` | Create or adopt the "Job search" Project, create missing fields, link the repo, save IDs. |
| `_items(gh, board, refresh=False)`, `find_item(gh, board, ref)` | All cards, read **once per `gh` object** (cached as `gh._items_cache`; `_edit` updates the cached cards after each write; `refresh=True` re-reads; dry runs never cache); the card whose body has this ref's marker. `jd_check.py score` and `sponsorship.py record` take several refs and share one `Gh`, so a batch costs one board read. |
| `_edit(gh, board, item, field, value)` | Set one field (single-select by option ID, date, or number). |
| `FIT_START`, `FIT_END`, `fit_section(score, scored_on)`, `with_fit(body, section)`, `set_fit_section(gh, ref, score, scored_on)` | The card's fit breakdown from a validated `score.json` (third-party-derived text escaped with `md()`), inserted before the Role ID line or replacing the previous block between the markers. |
| `promote(refs)` | CLI `promote`: queue cards for recorded roles not on the board (skips ones already carded or queued); `roles` opens them. |
| `TIER_LINE`, `refresh_bodies(gh)` | CLI `refresh-bodies`: remove the tier-arithmetic line older cards carried, and add or refresh fit breakdowns for every scored role from `work/jd/<ref>/score.json`. |
| `set_role_fields(gh, ref, values, close, note)` | Set fields on a role's card, log stage changes (with the note), comment the note on the issue, close on final stages. Setting `Recommendation=Skip` on a card whose Stage is New or blank also sets `Stage=Skipped` (note "recommendation was Skip"), which closes the issue and gets the card archived by the daily run; Shortlisted/Applied/other stages are the user's and are never moved. |
| `VIEWS`, `API_KEYS`, `CLICK_KEYS` | The board's views as data; what the API can set; what needs a click. |
| `DESIGN_QUERY`, `views(gh, owner, number)` | GraphQL for the board's views, returned in `VIEWS` shape plus IDs. |
| `_click_steps(spec, have)` | Menu instructions for sort/grouping differences. |
| `design_diff(gh)` | How the board's views differ from `VIEWS` (extra user views are fine). |
| `apply_views(gh)` | Create/update views; return what's left to click. |
| `POSTED_RE`, `REF_RE`, `posted_date(body, first_seen)` | The Posted date from the issue body, else first seen. |
| `_first_seen()` | `ref → posted or first-seen date` from `matches.csv`. |
| `fill_gaps(item, board, rows, seen)`, `needs_fill(items)` | What `fill` would set on one card (`{"stage": True, "country": "NL", "posted": "2026-09-21"}`), computed from data already in hand: no board read. A value it cannot supply (a country outside `FIELDS["Country"]`, an undatable role) is left out, so it is not a gap. `needs_fill` is true when any card has a gap; the session brief uses it to decide whether to start a fill. |
| `fill_new(gh)` | Writes what `fill_gaps` reports: Country and Posted on any card that lacks them, Stage/Tier/Sponsor on cards with no Stage. Tier, Sponsor and Country come from the card's `matches.csv` row (`_match_rows()`, `_row_sponsor()`), falling back to old `tier-N`/`sponsor-…` labels. See [page 11](11-Board-internals.md#where-each-card-value-comes-from). |
| `describe(gh)`, `LABEL_DESCRIPTIONS`, `FIELD_DOCS`, `PROJECT_DESCRIPTION`, `PROJECT_README` | CLI `describe`: write label descriptions, every dropdown option's description (options are re-sent with their ids, so cards keep their values), the project description and the field-guide README to GitHub. Safe to re-run. |
| `main(argv)` | The CLI. |

**Watch out**: `setup_project()` resolves `@me` to the real login, because `gh project
link` compares owner names literally and fails on `@me`. It saves `board.json` as soon as
the Project exists, so a failure later (e.g. linking) doesn't create a duplicate Project on
retry. It refuses a repo whose owner isn't the Project's owner. It does **not** build views
itself: the `setup-project` command runs `setup_project()` then `apply_views()`.

**CLI flags**: `--repo OWNER/REPO` (setup-project), `--close` (set: also close the issue),
`--note "…"` (set: the reason, stored in `pipeline_log.jsonl` as `note` and posted as an issue comment),
`--dry-run` (print the `gh` commands; nothing changes and no stage changes are logged; `promote` reports
what it would queue),
`--max N` (roles: issues per run). `sync_roles()` takes the queue oldest first.

## `tools/jd_cleanup.py`: trim the JD packets of roles you are done with

`candidates(root, now)` lists `work/jd/<ref>/` folders whose `jd.txt` and `packet.md` are past their retention: Stage Skipped 14 days after it was skipped, Rejected 30 days after, scored skip with no stage change 14 days after the score (days overridable in `profile/config.json` `cleanup`). `run(root, now, dry)` removes those two files (never `score.json`, `meta.json` or `sponsorship.json`) and stamps the `jd_cleanup` cadence job; the SessionStart hook calls it daily (the cadence marks it due after 48 hours) and the CADENCE block has a line for it. Roles in New, Shortlisted, Applied, Interview or Offer are never touched.

## `tools/cadence.py`: the cadence ledger (standard library only)

The session brief's CADENCE block lists every recurring job and whether it is due, so none runs silently. Jobs Claude runs (they need Gmail or Chrome, which a hook cannot drive) stamp themselves in `work/.cadence.json` when finished.

| Name | Is |
|---|---|
| `JOBS` | Job name to hours before it is due again: `inbox_check` 20, `post_discovery` 20, `auto_score` 4, `views_check` 24, `health` 24, `cv_review` 168, `jd_cleanup` 48 (seven jobs). |
| `done(name, root, now)`, `last(name, root)`, `load(root)` | Stamp a job as just finished; read a stamp; read the ledger. CLI: `python tools/cadence.py done <name>` and `show`. |
| `is_due(name, now, root)`, `when(name, now, root, fallback)` | True when never run or older than its interval; the "last ran … (Nh ago)" text. |
| `block(now, root, …)` | Returns the brief's CADENCE lines (radar search, new roles to the board, scoring, inbox check, LinkedIn post sweep, board views vs code, health, CV review, JD packet cleanup (due after 48 hours without a stamp; the SessionStart hook runs `tools/jd_cleanup.py` daily, and the line makes a silent failure visible), the application-mail scan (the `mail_scan` argument: due when the Action's mail ledger is more than 36 hours old), docs review) and the names of the due jobs. These arguments make a line DUE: `views_drift` (the brief's design-diff note: update `VIEWS` to the user's live layout, then `cadence.py done views_check`) and `docs_review` (the reason from `docs_review_note()`: run `docs-review`, which stamps `work/.last_docs_review` itself), `source_problems` (a count from `status_info()`; DUE when above 0 and the `health` job is older than a day: run `health`, then `cadence.py done health`) and `cv_gaps` (the "CV gaps" note from `health_checks()`; DUE when set and `cv_review` is older than a week: offer `cv-review`, then `cadence.py done cv_review`). `session_brief.cadence_block()` gathers its inputs from `matches.csv`, the issue map, the queue and the board, and passes both through. |

## `tools/session_brief.py`: the SessionStart hook (standard library only)

Walkthrough: [page 4, 4.2](04-Claude-session.md).

| Name | Is |
|---|---|
| `FOLLOW_UP_DAYS`, `REVIEW_EVERY_DAYS`, `GRACE` | 14, 7, 1 hour. |
| (maintainer-only, `docs-review` skill) `DOCS_REVIEW_AFTER_FILES`, `CODE_PATHS`, `LAST_DOCS_REVIEW`, `docs_review_note(now, runner)` | Returns the reason when `docs-review` is due, once 10 distinct files changed under `CODE_PATHS` (`radar.py`, `verify_boards.py`, `jobradar/`, `tools/`, `.claude/skills/`, `.github/workflows/`; docs and settings don't count) since `work/.last_docs_review`, per `git log --since` (the stamp is UTC and passed with `+00:00`). On a fresh copy the first call only writes the stamp. Called from `main()`. |
| `calibration_notes(now)`, `LAST_CALIBRATION` | Run `calibrate.apply` at most weekly; report each change with its undo command and a reminder to commit the config. |
| `referral_route_pick(root, scores, items, by_ref, n)` | The brief's REFERRAL-ROUTE line: live (New/Shortlisted, not Done) cards scored apply/maybe at an employer with a contact in `profile/network.csv` (`referrals.contacts`) and no record in `data/referrals.jsonl`, at most 8. Any error returns no lines (a missing network file must not stop the brief). |
| `sponsor_check_pick(scores, checked, items, n)`, `read_sponsor_keys(root)` | The brief's SPONSOR-CHECK line: live (New/Shortlisted, not Done) board cards scored apply/maybe with no record in `data/sponsorship.jsonl`, at most 10; Claude runs `sponsorship-check` on them (standing rule: every role on the board gets a verdict). |
| `auto_score_count(root)`, `auto_score_pick(rows, scored, items, n)`, `start_prep(refs)` | How many roles to score automatically; which (freshest unscored Tier 1, not closed/skipped); fetch their JDs in the background. |
| `referral_notes(now)` | Asks unanswered after `referrals.wait_days`, as health notes (at most 5). |
| `stale_days(root)` | `board.stale_days` from the config, for the brief's "looks closed" line. |
| `skipped_refs(root)` | Refs whose latest logged Stage is Skipped/Rejected, so an archived skip (gone from the board read) is not auto-scored or counted unscored again. |
| `start_archive(now)`, `LAST_ARCHIVE` | Once a day (stamp `work/.last_archive`), start `board_sync.py archive` detached (log `work/board_archive.log`) when any card is in Stage = Skipped or Rejected. |
| `LAST`, `LAST_REVIEW`, `FILL_LOCK`, `SNAPSHOT`, `PIPELINE_LOG` | The files it reads and writes (`work/…`, `data/…`). |
| `_CONTROL`, `_REF` | Characters stripped by `safe()`; the ref marker in issue bodies. |
| Other thresholds (in code) | Top 6 new Tier 1 roles listed; "unscored" = Tier 1 from the last 14 days; "fresh" = posted in the last 3 days; "no run completed for 2+ days" warning; a CV gap needs 3+ scored roles missing it. Follow-ups only apply to cards with a logged stage change. |
| `safe(text, limit)` | Sanitise third-party text for the brief. |
| `run(cmd, timeout)` | Run a command; `(ok, output)`; never raises. |
| `_read_json`, `_read_stamp` | Tolerant file readers. `_read_stamp` returns naive UTC even when the file holds a `+00:00` time (Claude writes `.last_review` that way); an aware stamp used to crash the brief with `TypeError`. |
| `pull()` | `git pull --ff-only`. |
| `read_matches`, `read_scores`, `status_info` | Read `matches.csv`, `scores.jsonl`, `status.md` (last run, problems, alert row). |
| `board_items()` | Role cards via `gh project item-list`. |
| `closed_cards(items, now, gh)` | Sync cards closed on the board: Stage → Skipped when not yet acted on; list in-progress ones for Claude to ask about. |
| `track_stage_changes(items, now)` | Log drags since the last snapshot; save a new snapshot. |
| `stale_applications(items, now)` | Applied cards with no movement for 14+ days. |
| `_needs_fill(items)`, `start_fill(now)` | `_needs_fill` asks `board_sync.needs_fill(items)` (falling back to "any card has no Stage" if that import fails); `start_fill` starts `board_sync.py fill` detached, at most once per 10 minutes. |
| `template_status(since)` | Template commits since last session; unpublished private code. |
| `board_design_note()` | Views drift note. |
| `last_due_slot(now, workflow)` | Latest cron slot (from `radar.yml`) that should have run, minus grace. |
| `last_run_health(runner, now, workflow)` | Report a failed run; restart a skipped one. |
| `health_checks(...)` | Career docs, run age, alert emails, review due, recurring CV gaps. |
| `_age`, `brief(...)` | Format the brief. |
| `main()` | The sequence; always exits 0. |

## `tools/public_template.py`: keep the public template current and clean

| Name | Is |
|---|---|
| `PRIVATE`, `NEVER_COPY`, `PUBLIC` | What may never be published; what's never copied (venv, caches, clones); what may be published (allowlist). |
| `is_private(rel)`, `is_public(rel)` | Path tests. Public = on `PUBLIC`, not on `PRIVATE`, not `NEVER_COPY`. |
| `export(dest)` | Build a clean template tree in an empty folder. |
| `drift(fetch)` | Public files changed in **commits** here since the last template merge. Uncommitted edits are not included. |
| `dirty_public()`, `committed_bytes(rel)` | Public files with uncommitted changes (reported, not published); a file as committed in `HEAD` (what `publish` copies, never the working-tree version) |
| `status_paths(lines)` | Paths from `git status --porcelain`, both sides of a rename. |
| `publish(template_dir, message)` | Copy (from `HEAD`)/delete drifted files in the template clone, run tests, `check`, commit, push. |
| `autopublish()` | The post-commit hook's entry: publish, merge back, mirror the wiki; never raises. |
| `wiki_text(text, blob_base)` | Rewrite links for the GitHub Wiki. |
| `mirror_wiki(template_dir)` | Copy `docs/wiki/` into the template's wiki repo. |
| `check()` | Fail if this repo tracks any private file (run inside the template clone). |

CLI: `export <dir>`, `check`, `drift` (print unpublished public files), `publish <dir> -m "msg"`, `autopublish`.

## `tools/manual.py`: the `man` page

`skills()` reads each skill's `name`/`description`, `tools()` reads each tool's docstring
first line (via `ast`, without importing), `wrap()`, `paint(color)` (ANSI colours only on a
real terminal and without `NO_COLOR`), `main()`. Generated from the code, so it can't go
out of date.

## `tools/referrals.py`: referral routes and asks (standard library only)

| Name | Is |
|---|---|
| `NETWORK`, `LOG` | `profile/network.csv`, `data/referrals.jsonl` |
| `RELATIONS`, `RELATION_NAMES` | `known` (default: someone the user knows; no draft) or a stranger, `recruiter` / `hiring_manager` (drafts) |
| `RESULTS`, `ROUTES` | Answer → board value (only *referred* sets one); route status → board value |
| `wait_days()` | `config.json` → `referrals.wait_days` (default 4) |
| `contacts(company)` | People at a company, loosely matched (whole-word prefix either way), in ask order |
| `records()`, `_append()` | Read / append the log |
| `pending(days, now)` | Latest record per (role, person) still *asked* after `days` |
| `_board(ref, value, note)` | Set the card's Referral field (via `board_sync.set_role_fields`) and comment the note; without a value, comment only |
| `ask`, `result`, `route`, `main` | The CLI: log each step, update the card |

**Watch out**: a second ask after someone already referred leaves the field at *Referred* (the ask is still logged and commented).

## `tools/add_role.py` and `jobradar/intake.py`: roles added by hand go through the daily run's pipeline

`add_role.py <job url>` (Greenhouse, Lever, Ashby links) fetches the company's board through ats-scrapers, finds the posting and hands it to
`intake.admit()`, which runs the same functions as `radar.py`: `select()` (countries, titles, permanent-only, `max_age_days`, employer list),
`group_postings` + `diff_seen` (dedupe against everything seen), `enrich()` (sponsor tags, tier, score), `append_matches()` and the board
queue. `select()` stops at the first filter that drops a role, so `admit()` re-runs it with each triggered filter bypassed (`skip=`) to name
**every** reason. A role the filters would drop is reported and not added; `--override country,old,…` (only on the user's word) adds it anyway
and `data/matches.csv` `origin` records it (`manual-override:country,old`; blank for the daily run, `manual` for a role that passed).
`post_leads.py add-role` uses the same door (`--override` there too). Why: two Anthropic roles added by hand on 2026-10-07 (posted 89 and
623 days before, `max_age_days` 30) skipped the age filter that the daily run applies. For a link the fetch cannot read (LinkedIn, a company site, a pasted ad) `--company --title --location --posted [--countries]` build the posting by hand (`intake.manual_posting`, source `manual`) and it goes through the same filters. `--dry-run` writes nothing. It writes the same files
the Action writes (`data/matches.csv`, `state/seen.json`, `state/board_queue.json`), so commit and pull as for any session change.

## `tools/post_leads.py`: LinkedIn hiring-post discovery (standard library only)

| Name | Is |
|---|---|
| `QUERIES`, `COMPANY_IDS`, `PEOPLE`, `LEADS`, `MATCHES` | `state/post_queries.json`, `state/linkedin_company_ids.json` (LinkedIn's numeric id per company), `data/post_people.jsonl`, `data/post_leads.jsonl`, `data/matches.csv` |
| `KINDS`, `DEFAULTS`, `settings()` | Lead kinds (`person`, `job_board`); the defaults for `config.json` → `discovery.linkedin_posts`; the merged settings |
| `fit_companies()`, `fit_targets(fit)`, `search_companies()` | Employers scored apply/maybe, best first; `targets.tsv` companies with a given Fit; the company-search list: `company_extra`, then the scored employers, then the High-fit targets, each employer once |
| `network_companies()`, `ranked_companies()`, `_has_contact` | Employers in `profile/network.csv`; `(tier, company)` for the company searches: 0 named in chat, 1 a contact there, 2 scored apply/maybe, 3 `company_fit` targets; `search_companies()` is the names only |
| `company_id`, `set_company_id`, `search_url(line)` | LinkedIn's id per company; the post-search link for a query line, with the `authorCompany` filter (posts written by employees) when the id is known, else a note on how to read the id |
| `next_queries(n, now)` | The next post searches, least recently run first, spread over a title x place diagonal; the phrase rotates when a pair comes round again; marks them run |
| `people()`, `add_person`, `next_people`, `mark_read` | The recruiters and managers worth re-reading: latest record per profile URL, longest unread first |
| `leads()`, `lead_id(url)`, `_clean_url` | Every lead by id (later records overwrite fields); id = hash of the post URL without tracking parameters |
| `known_roles(company, title)` | Rows of `matches.csv` for the same employer (loose name match) with a similar title (60% of the shorter title's words shared) |
| `log_lead(...)` | Log one post; status `known`, `job_board`, `stale` (older than `max_post_age_days` and not confirmed open) or `new`; one record per post |
| `add_role(id, countries)` | A `new` lead becomes a `matches.csv` row (new columns `poster`, `poster_url`) and a queued card via `board_sync.promote`; the ref is the hash of the radar's own `c:company|title|country` key, so a later radar hit lands on the same card |
| `stats(days)` | Counts of new, added, known, stale and job-board leads, and known people |
| `main` | The CLI (`queries [--urls]`, `company-id`, `person add/next/read`, `lead`, `add-role`, `stats`) |

**Watch out**: this file never touches LinkedIn; Claude does the reading (CLAUDE.md rule 4c). `jobradar/board.py` `row_payload` adds a "Posted by" line when a row has a `poster`.

## `tools/sponsorship.py`: checked sponsorship verdicts (standard library only)

| Name | Is |
|---|---|
| `WORK`, `LOG` | `work/jd/`, `data/sponsorship.jsonl` |
| `VERDICTS`, `KINDS`, `WEB_KINDS`, `BANNED` | Verdict → Sponsor option; evidence kinds; kinds that need a URL; domains never accepted |
| `check(data, ref, jd_text)` | Validate a record: fields, verdict, country code, summary length, 1–6 evidence items, verbatim ad quotes, http(s) non-banned URLs, `confirmed` and `no` each backed by the ad or the company's own page |
| `visa_section(data)`, `with_visa(body, section)`, `VISA_START`, `VISA_END` | The card's escaped sponsorship block, inserted or replaced in place |
| `upsert`, `company_records(company)` | Log one verdict per role; earlier verdicts for the same employer (loose name match) |
| `record(ref, board, gh=None)`, `main` | CLI `record <ref> [<ref> …] [--board]` (refs share one `Gh`, so one board read) and `company "<name>"` |

## `tools/calibrate.py`: automatic tier tuning (standard library only)

| Name | Is |
|---|---|
| `MIN_TOTAL`, `MIN_PER`, `MAX_WEIGHT`, `LOWER_IF`, `RAISE_IF`, `COOLDOWN` | 30 scored roles overall, 5 per keyword, weights 0..5, lower when average Fit < 45 and ≥70% skip, raise when ≥ 70 and ≥60% apply, one change per keyword per 7 days |
| `_kw_re`, `best_keyword(title, kw)` | Which title keyword set a role's weight (same rule as `tiering.score`) |
| `weights()`, `stats()`, `proposals(now)`, `config_path()` | Current weights; per-keyword n / average Fit / skip and apply rates; changes the evidence supports; the config file edited |
| `set_weight(keyword, value)` | Edit one weight in `config.json` in place, keeping layout and comments |
| `apply(dry_run, now)`, `revert(keyword)`, `describe(c)` | Apply and log; undo the last automatic change; one-line description for the brief |

**Watch out**: only `tiering.title_keywords` weights ever change automatically; include/exclude lists,
countries and everything else remain the user's decision.
