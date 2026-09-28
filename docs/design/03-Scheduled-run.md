# 3. A scheduled run, step by step

**What this is:** What happens three times a day in GitHub Actions, followed through the code, then one real role's journey from a job board to a card.  
**Read first:** [2. Architecture](02-Architecture.md)  
**Code:** `.github/workflows/radar.yml`, `radar.py`, `jobradar/`, `tools/board_sync.py` (roles/stale/status)

Three times a day (02:47, 08:47, 14:47 UTC) GitHub starts `.github/workflows/radar.yml`.
This page follows one run from start to finish, through the actual code, then follows
one real role all the way to the user's board.

## 3.1 The workflow file: `radar.yml`

A workflow has **jobs**; each job has **steps**; each step runs a command on a fresh
Ubuntu machine GitHub provides.

**Triggers.** `schedule: cron: "47 2,8,14 * * *"` and `workflow_dispatch` (a manual
"Run workflow" button, also what `gh workflow run job-radar` presses).

**`permissions: {}` at the top** grants nothing by default; each job asks for what it
needs. **`concurrency: group: job-radar`** means this workflow and the two others
(verify, registers) never run at the same time, so their commits can't collide.

**Job 1: `guard`** (read-only). Asks the GitHub API whether the repo is private
(`gh api repos/$GITHUB_REPOSITORY --jq .private`). It outputs `allowed=true` only for a
private repo, or when the repo variable `JOB_RADAR_ALLOW_PUBLIC` is `true`. Why: in a
public repo the issues, commits and logs would publish the user's job search. That's
also why the public template never runs anything.

**Job 2: `radar`** runs only if `guard` said allowed. Permissions: `contents: write`
(to commit) and `issues: write` (to create role issues). Steps:

| # | Step | What it does | If it fails |
|---|---|---|---|
| 1 | `actions/checkout@<sha>` | Downloads the repo | run fails |
| 2 | `actions/setup-python@<sha>` | Installs Python 3.13 | run fails |
| 3 | Fetch job-alert emails | `python -I -S tools/fetch_alert_emails.py --out .alert_mail --days 3 --providers linkedin,indeed,glassdoor` with the two mail secrets in its environment | ignored (`continue-on-error`); the failure shows in the Radar status card |
| 4 | `pip install --require-hashes -r requirements.txt` | Installs dependencies; refuses any file whose hash doesn't match the lock file | run fails |
| 5 | `python radar.py --quiet` | The pipeline (3.2 below) | run fails |
| 6 | `board_sync.py roles` | Queued roles → issues | ignored, so the commit still happens |
| 7 | `board_sync.py stale` | Label roles no longer listed | ignored |
| 8 | `board_sync.py status` | Update the pinned "Radar status" issue | ignored |
| 9 | Commit state | `git add state digests data/matches.csv`, commit, then up to 3 tries of `git pull --rebase` + `git push` | run fails |

Three details that matter:

- Actions are referenced by **commit SHA**, not version tag (`@11d5960…  # v4.4.0`). A
  tag can be moved by whoever controls the action; a SHA can't.
- Step 3 runs **before** step 4. At that moment no third-party Python package exists on
  the machine, and `-I -S` makes Python ignore any site-packages and startup hooks. So the
  only code that ever shares a process with the mailbox password is the standard library
  plus two small files in this repo. See [Job-alert emails](12-Job-alert-emails.md).
- Step 9 retries because the user may push from their machine while the run is going
  (GitHub rejects a push that isn't based on the latest commit).

## 3.2 Inside `radar.py: main()`

Read `radar.py` alongside this. `main()` is about 60 lines; here is each block.

### Load

```python
scfg = load_sources_config()                 # sources.yaml (profile/ else examples/)
sources = build_sources(scfg, only=args.source)
seen = load(STATE / "seen.json", {})
health = load(STATE / "health.json", {})
baseline = not seen                          # first run ever?
```

`build_sources()` (in `jobradar/sources/__init__.py`) imports every adapter module. Each
module ends with `register("name")(Class)`, which records the class in a dictionary.
Then, for every source in `sources.yaml` with `enabled: true`, it creates the adapter
with that source's settings. `--source X` builds only X, even if disabled (for testing).

### Fetch: `run_sources()`

```python
results = asyncio.run(run_sources(sources))
```

All sources run **at the same time** (`asyncio.gather`). Each is wrapped by `_run_one()`,
which applies the source's `timeout_seconds` and turns any exception or timeout into a
failed `SourceResult` instead of crashing. **One broken source never stops the others.**

Each adapter returns a `SourceResult`: a list of `Posting`s plus a list of `UnitStatus`es
(one per board, query, page or email provider), which feed health tracking. What each
adapter does is in [Sources](08-Sources.md) and the [code reference](05-Code-reference.md).

### Filter and match: `select()`

For every posting from every source:

1. **Country.** Keep only the posting's countries that are targets (`target_countries()`
   plus `REMOTE-EU`). If none are left, drop it. (Countries were worked out by the adapter,
   usually with `common.py: countries_for()`.)
2. **Title.** `common.py: title_matches()`: drop it if any `title_exclude` keyword appears
   (whole words), otherwise keep it only if a `title_include` keyword appears. Exception:
   a "careers page changed" notice has no job title, so it always passes.
3. **Company.** `matcher.resolve(p.company, p.company_hint)` looks the employer up in
   the target list (exact match after normalizing, or via an alias). ATS postings also
   carry a *hint*: the targets whose board this is, used if the posting's own company
   field doesn't match. The result goes in `p.company_canonical`. If it's `None` and the
   source isn't set to include outsiders, drop it.

It also counts matches per source for the report.

### Deduplicate and diff: `group_postings()` then `diff_seen()`

`group_postings()` (in `dedupe.py`) puts postings with the same **content key**
(company + title + primary country, all normalized) into one `Group`. The same
"Senior Penetration Tester" at Bridewell in the UK, found on its ATS board and on
EURES, becomes one group.

`diff_seen()` decides what's new. A group's keys are its content key plus every posting's
`source:id`. If **none** of those keys is in `seen.json`, the group is new. Either way,
all its keys get today's date in `seen.json`. (Checking IDs too means a role whose title
was slightly edited is still recognised, as long as its ID doesn't include the title: ATS
and API postings have stable IDs, but careers-page postings use `url|title`, so an edited
title there shows up as a new role.)

### Enrich: `enrich()`

Only for **new** groups, so the expensive part stays small:

- `sponsors.tag(company, canonical)` looks the employer up in the UK and NL registers.
  The first call loads ~135,000 register names, which is why it's imported lazily.
- The posting's age in days comes from `posted_at`.
- `tiering.score()` adds up the rule weights; `tiering.tier()` turns the score into 1 or 2.
- The results go in `g.tags`: `sponsor`, `score`, `tier`, `reasons`.

### Health: `update_health()`

`health.py` keeps a streak counter per unit (`"ats|https://…"`, `"eures|canary"`). A
unit is **bad** this run if it errored, or if it returned zero raw results when zero isn't
normal (`track_empty`). After 2 bad runs in a row, a unit is reported if it reported an
error, or (for zero results) if it has worked before. Such a unit is
reported as "stopped returning results". A whole-source crash is tracked as unit `*` and
reported even if the source never worked.

### Reports and the board queue

- `render_digest()` builds the Markdown report: Tier 1, then Tier 2, grouped by company
  (best-scoring company first), then "outside your list", then broken sources, then a
  source table. Every third-party string goes through `md()` (escapes Markdown) and every
  link through `md_url()` (only http/https).
- `select_for_board()` picks new groups for the board: tiers in `config.board.tiers`
  (only `baseline_tiers` on the first run), and only companies on the list.
- `payload()` turns each into `{ref, title, body, labels}`. `enqueue()` appends them to
  `state/board_queue.json`, skipping refs already queued.
- `render_status()` builds the short "Radar status" text: counts and source health, no
  job titles (so it can be shown anywhere).

`--dry-run` stops here and prints; nothing is written.

### Write

```python
seen = {k: v for k, v in seen.items() if v >= cutoff}   # forget keys unseen for 120 days
write digests/<today>.md, digests/latest.md, digests/status.md
save_queue(...)
stale check (below)
write state/seen.json, state/health.json
append_matches(new, today)                              # data/matches.csv
```

**Stale check.** A role on the board that no source has listed for more than `stale_days` (5) days is
probably closed. `stale_refs()` compares each board ref's last-seen date
(`ref_last_seen()` hashes every content key in `seen.json` back to its ref) with the
cutoff. It runs **only on healthy runs**: every source OK, and no more than
`max(3, 10% of units)` units erroring (so up to 3 errors are always tolerated). Otherwise
an outage would make every role look closed. On an unhealthy run `stale_roles.json` is
left as it was, and `board_sync.py stale` simply re-applies the previous report, which
changes nothing.

`append_matches()` adds one CSV row per new group. If the column list changed since the
file was created (a new version added a column), it rewrites the file once with the
combined header.

With `--quiet` (always, in Actions) only a one-line summary is printed, so the Actions
log never contains job titles or target companies.

## 3.3 After `radar.py`: `board_sync.py` in Actions

`gh` in these steps uses GITHUB_TOKEN.

**`roles`: `sync_roles()`.** Takes up to `max_per_run` (40) payloads from the queue.
Makes sure every label exists (`gh label create --force`), then for each payload runs
`gh issue create --title … --body-file <temp file> --label …`. Arguments go as a list,
never through a shell, and the body goes in via a file, so nothing in a job ad can be
interpreted as a command. After **each** issue it rewrites the queue without the ones
done, so a crash halfway never creates duplicates. It records `ref → issue number` in
`state/issue_map.json`, and waits 2 seconds between issues (GitHub throttles bursts).

**`stale`: `sync_stale()`.** Reads `state/stale_roles.json`. Adds `possibly-closed` to
newly stale roles' issues, removes it from roles seen again, and remembers the flagged
set in `state/stale_flagged.json`.

**`status`: `sync_status()`.** Finds the open issue labelled `radar-status` and replaces
its body with `digests/status.md` (with the "waiting" count corrected, since `roles` ran
after the status was written). If there isn't one, it creates it and pins it.

**What happens next, outside our code:** the Project's built-in *Auto-add to project*
workflow sees each new issue labelled `role` and puts it on the board. The card has
labels but **empty fields**. Those are filled at the user's next Claude session
([step 4](04-Claude-session.md)).

## 3.4 One role's journey

Bridewell (a UK security consultancy on the user's target list) posts *Senior
Penetration Tester* in London on its Workable board.

1. **Fetch.** `boards.json` has `{"companies": ["Bridewell"], "ats": "workable", "slug":
   "bridewell", …}`. The `ats` source asks `ats-scrapers` for that board and gets a `Job`
   with title, location "London, England, United Kingdom", `country_iso` "GB", and
   `global_id` "workable:ABC123". `ats.py: job_to_posting()` makes a `Posting` with
   `source="ats"`, `countries={"GB"}`, `external_id="workable:ABC123"`,
   `company_hint=("Bridewell",)`.
2. **The same role on EURES?** No: EURES has no UK. But suppose an alert email also
   carried it: that would be a second `Posting` with `source="linkedin_email"`.
3. **Filter.** GB is a target country. "penetration test*" is in `title_include`; nothing
   in `title_exclude` matches. Kept.
4. **Match.** Suppose the board reports the employer as "Bridewell Consulting Ltd":
   `normalize()` gives `bridewellconsulting`, which isn't a target spelling. The hint
   `Bridewell` gives `bridewell`, which is. `company_canonical =
   "Bridewell"`.
5. **Group.** Content key `c:bridewell|seniorpenetrationtester|GB`. Any LinkedIn copy
   has the same key, so it joins the group; the ATS posting is `best` (source rank 0), the
   LinkedIn one becomes "also on".
6. **New?** Neither `ats:workable:ABC123` nor the content key is in `seen.json`: new.
7. **Enrich.** UK register: `Bridewell` prefix-matches exactly one entry, "Bridewell
   Consulting Limited" → `yes`. Score: title "penetration test*" 4 + "senior" 1 + GB 2 +
   on list 1 + sponsor 1 (+1 if posted in the last 3 days) = 9 or 10 → Tier 1.
8. **Queue.** Tier 1, on list → `payload()`: ref = first 16 hex of
   `sha1("c:bridewell|seniorpenetrationtester|GB")`, title
   `Bridewell — Senior Penetration Tester (GB)`, labels `role, tier-1, country-GB,
   sponsor-yes`, body with the link, score reasons, sponsor match, posted date, Role ID,
   and a hidden `<!-- job-radar:ref=… -->` marker.
9. **Record.** A row goes into `data/matches.csv` with the same ref.
10. **Issue.** `board_sync.py roles` creates the issue; `issue_map.json` gets `ref → #12`.
11. **Card.** Auto-add puts issue #12 on the board.
12. **Fields.** At the next Claude session, `board_sync.py fill` reads the card's labels
    and sets Stage=New, Tier=T1, Sponsor=Yes, and Posted from the body's "Posted:" line.
13. **Later.** When the user asks Claude to score it, `jd_prep` fetches the JD into
    `work/jd/<ref>/`, Claude writes `score.json`, `jd_check score` validates it and sets
    Fit and Recommendation on the card. If Bridewell takes the ad down, after 5 days of
    healthy runs the issue gets `possibly-closed`.

The ref is the thread through all of it: the same 16 characters appear in the issue's
hidden marker, the `matches.csv` row, `work/jd/<ref>/`, `scores.jsonl` and the
application folder.

## 3.5 The two other workflows

**`verify.yml` (1st of each month, or on demand).** Same guard. Runs
`verify_boards.py --quiet`: fetches every candidate board (from `data/candidates.csv`
plus `profile/overrides.csv`), keeps a board only if it lists jobs in the target
countries (this rules out dead boards and same-name companies elsewhere), and writes
`boards.json`, `data/verified_boards.csv` and `data/coverage_report.csv`. Commits them.

**`registers.yml` (Mondays).** Runs `tools/refresh_registers.py`: downloads the UK
register CSV (its URL changes each update, so it's looked up through the gov.uk content
API) and the Dutch IND HTML table, keeps skilled-worker routes, and writes sorted CSVs.
It refuses to overwrite if a download looks truncated. Commits only when a register
actually changed.
