# 5.6 Setup and upkeep tools, automation config and constants

**What this is:** The tools used at setup and for upkeep (alert-email fetching, sponsor registers, candidate boards, doc links, fixtures), then the automation config files, the settings pointers, and the module constants not covered elsewhere.  
**Read first:** [14. Setup and publishing](14-Setup-and-publishing.md) and [10. Configuration](10-Configuration.md)  
**Code:** `tools/fetch_alert_emails.py`, `refresh_registers.py`, `build_candidates.py`, `discover_boards.py`, `check_doc_links.py`, `record_fixture.py`; `.github/`, `.claude/`, `.githooks/`  

Part of the [5. Code reference](05-Code-reference.md) (the index of every file and function).

---

## `tools/fetch_alert_emails.py`: IMAP (standard library only)

`all_mail_name(m)`: Gmail's All Mail folder from `LIST` flags. `fetch(host, user, password, mailbox,
since, senders, domains)`: IMAP over TLS; `mailbox="auto"` = All Mail else INBOX; `select(readonly=
True)` (IMAP EXAMINE: nothing is marked read or deleted), `SEARCH SINCE … FROM …` per
sender, `FETCH BODY.PEEK[]`. `main()`: clears old `.eml` files, reads the credentials
from the environment, writes `<uid>.eml` files and `_status.json`, always exits 0, and
never prints credentials (errors are truncated exception messages).

**Watch out**: `sys.path.insert(0, ROOT)` because `python -I` leaves the script's folder
off the import path, and it needs `jobradar/alert_providers.py`.

## `tools/refresh_registers.py`: sponsor registers

`fetch_uk()` (gov.uk content API → the current CSV attachment → skilled-worker routes,
de-duplicated per organisation and town), `fetch_nl()` (the IND page's table; the name is
in the row header `<th>`), `write()` (refuses fewer than 50,000 UK / 5,000 NL rows),
`main()` (also writes `meta.json`). Output is sorted plain CSV so weekly git diffs stay
small.

## `tools/build_candidates.py`: targets → candidate boards (setup)

A script, not functions-with-main: run from the repo root after cloning `atss/`
(ats-scrapers' company lists) and `agg/` (job-board-aggregator's slugs). For each target:
generate name variants (`candidates()`: strip brackets, split on `/`, drop "slice" words
like UK/Security/Group), look them up in both indexes, prefer first-party careers APIs for
giants (`FIRST_PARTY`), skip Asia/LatAm ATS platforms (`OFF_REGION`) and known wrong
matches (`REJECT`), and write `data/candidates.csv` with a status per company.
`verify_boards.py` then checks each candidate live.

## `tools/discover_boards.py`: find boards for uncovered targets

`slug_guesses()` (joined, hyphenated, first word), `uncovered()` (non-VERIFIED companies
in the coverage report), `candidates()` (ats-scrapers' company index + guesses on 12 common
ATSs), `evaluate()` (keep a board only if it lists jobs in target countries), `discover()`,
`main()` (`--apply` appends the proposals to `profile/overrides.csv`).

**Watch out**: a guessed slug can belong to a different company with the same name, and
some ATSs return a default board for any slug. Results are proposals: Claude and the
user review them before `--apply`.

## `tools/check_doc_links.py`: doc link checker (standard library only)

Every relative Markdown link in `docs/`, `README.md`, `CLAUDE.md` and the skills must
resolve (a target containing a space counts as broken), and every `docs/<folder>/<page>.md`
path mentioned in code or config must exist. Exit 1 if not. Used by the `docs-review` skill.

## `tools/record_fixture.py`: capture a test fixture

Fetches one live ATS board and saves up to 60 jobs (title, location, URL, IDs; no
descriptions) as `tests/fixtures/ats/<name>.json`.

## Automation config

| File | Is |
|---|---|
| `.github/workflows/radar.yml` | The scheduled pipeline. [Page 3](03-Scheduled-run.md). |
| `.github/workflows/verify.yml` | Monthly `verify_boards.py`, commits `boards.json` and reports. |
| `.github/workflows/registers.yml` | Weekly `refresh_registers.py`, commits registers only when they changed. |
| `.claude/settings.json` | The SessionStart hook: runs `session_brief.py`, 90 s limit, on startup and resume. |
| `.githooks/post-commit` | Finds a Python (venv first) and runs `public_template.py autopublish`. Active only after `git config core.hooksPath .githooks`; does nothing without `git config jobradar.templateDir`. |
| `.gitignore` | `.venv/`, caches, `.alert_mail/`, `work/`. |
| `.gitattributes` | LF line endings; `.eml` and `.docx` untouched (binary-exact). |
| `pytest.ini` | Tests live in `tests/`. |
| `requirements*.in` / `.txt` | Wanted packages / hash-locked resolution (pip-tools). Four sets: runtime, dev (tests), career (python-docx), browser (playwright). |

All three workflows share the `guard` job and the `job-radar` concurrency group, pin
actions by commit SHA, and retry their final push.

## Settings and career files

Every settings file is described in [Configuration](10-Configuration.md); where each is read
is in [Architecture](02-Architecture.md). `examples/` has a public sample of each, plus
`examples/career/` showing the ID format with a fictional person.

## Claude's instructions

`CLAUDE.md` and `.claude/skills/*/SKILL.md` are prose, not code: see [page 4,
section 4.1](04-Claude-session.md#41-how-claude-knows-what-to-do) for what each skill does and which tools it runs. When a
capability changes, the rule in `CLAUDE.md` is to update `CLAUDE.md`, the skill and these
docs in the same commit.

## Remaining module constants

| Name | File | Is |
|---|---|---|
| `ISO_ALIASES`, `_TITLE_INCLUDE`, `_TITLE_EXCLUDE` | `common.py` | `UK` → `GB`; the compiled title filters |
| `_TITLE`, `_SENIORITY` | `tiering.py` | Compiled (regex, weight) pairs from `config.json` → `tiering` |
| `REG_DIR` | `sponsors.py` | `data/registers/` |
| `_retry_after()` | `sources/_http.py` | Seconds from a `Retry-After` header, capped at 60; 0 for the date form |
| `BundesagenturSource`, `JobTechSource`, `EuresSource`, `PAGE_SIZE` | `sources/*.py` | The search-source classes; results per page (50, 100, 50; `reed.py` also uses 100) |
| `_get()` | `sources/jobtech.py` | One JobTech API call (phrase-quoting multi-word queries) |
| `_PERIODS` | `sources/eures.py` | Allowed look-back windows: 1, 3, 7, 30 days |
| `_ROLLUP` | `sources/ats.py` | Matches Workday's "N Locations" placeholder |
| `META_FIELDS`, `MAX_CHARS` | `tools/jd_prep.py` | Role facts copied into `meta.json`; JD length cap (20,000) |
| `CONTACT_FIELDS` | `tools/render_resume.py` | Front-matter keys shown in the CV header |
| `UK_ROUTES`, `MIN_ROWS` | `tools/refresh_registers.py` | Visa routes kept from the UK register; minimum rows before overwriting |
| `TARGETS`, `SLICE_WORDS`, `agg_board()` | `tools/build_candidates.py` | Targets file path; words stripped when generating name variants; aggregator slug → board URL |
| `GUESS_ATS`, `OUT` | `tools/discover_boards.py` | ATS platforms tried with guessed slugs; `work/discovered_boards.csv` |
