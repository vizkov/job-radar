# 7. Changing it

**What this is:** Step-by-step recipes for the common changes: a source, a setting, a board field or view, a skill, a tool, a dependency.  
**Read first:** pages [1](01-Concepts.md) to [6](06-Tests.md)  
**Code:** whichever the recipe touches

Recipes for the common changes. After any code change: run `pytest` (`test_docs_cover_code.py`
fails if a new board field, skill, tool or config key is missing from the overview docs), update `CLAUDE.md`,
the matching skill and these docs in the same commit (the rule in `CLAUDE.md`), then
commit. In the maintainer's copy the post-commit hook publishes to the template.

## Add a source

1. Create `jobradar/sources/<name>.py` with a class that has `name`, `timeout` and
   `async fetch() -> SourceResult`. For a keyword-search API, subclass
   `search.SearchSource` and implement `search()` (and optionally `count()`).
2. Return one `UnitStatus` per thing you poll. Set `track_empty=False` where zero results
   is normal, so health doesn't flag it.
3. Work out `countries` with `common.countries_for()`; set `company_hint` if the source
   knows which target it's polling.
4. End the module with `register("<name>")(YourClass)` and add `<name>` to `_MODULES` in
   `jobradar/sources/__init__.py`.
5. Add it to `examples/sources.yaml` (and the user's `profile/sources.yaml`) with
   `enabled`, `timeout_seconds` and its settings.
6. Give it a rank in `dedupe.SOURCE_RANK` (lower = its link is preferred).
7. Record a response into `tests/fixtures/`, write a test with `respx`, and try it live:
   `python radar.py --dry-run --source <name> --include-outside`.
8. If it needs a credential: **ask the user first**, put the secret only in GitHub Actions
   secrets, and follow the alert-email pattern (fetch in a separate standard-library step
   before `pip install`). Never scrape LinkedIn, Indeed or Glassdoor.

## Add or change a setting

1. Read it with `CONFIG.get("key", default)` (or from the source's own config dict), so
   existing profiles without it keep working.
2. Add it with a comment to `examples/config.json` (or `sources.yaml`).
3. Document it in [Configuration](10-Configuration.md).

## Add a board field

1. Add it to `FIELDS` in `tools/board_sync.py` (options list, `None` for a number, `DATE`
   for a date).
2. Create it on the live board: `setup-project` creates missing fields, or run
   `gh project field-create` and refresh `profile/board.json` with `_read_fields()`.
3. Decide who sets it: `fill_new()` (from labels or the issue body) or
   `set_role_fields()` (from a skill). The scheduled run can't set fields; if the data
   comes from `radar.py`, pass it as a label or in the issue body.
4. Add it to the relevant views' `fields` in `VIEWS`.

## Add or change a board view

1. Edit `VIEWS` in `tools/board_sync.py`: name, layout (`TABLE_LAYOUT`/`BOARD_LAYOUT`),
   filter (GitHub's filter syntax, e.g. `tier:T1 posted:>=@today-14d`), fields, sort,
   group.
2. `python tools/board_sync.py views` creates or updates it and prints the sort/grouping
   clicks for the user.
3. Check the filter by opening the view: GitHub accepts any filter string, even one it
   can't evaluate.

## Add a skill

1. Create `.claude/skills/<name>/SKILL.md` with front matter `name:` and a `description:`
   that says when to use it (Claude matches requests against it).
2. Write the steps: which tools to run, what to check, what to report, what never to do.
3. Add a row to the skill table in `CLAUDE.md` and to [page 4](04-Claude-session.md).
   `tools/manual.py` picks it up automatically.

## Add a tool

1. `tools/<name>.py` with a module docstring whose first line says what it does (the
   manual shows it) and `--help`.
2. Keep file paths as module-level constants, and add them to `_isolate_tool_state` in
   `tests/conftest.py`.
3. If it may run outside the virtualenv (hooks, session start), use only the standard
   library.

## Change a dependency

```bash
pip install pip-tools
pip-compile --generate-hashes --strip-extras --allow-unsafe -o requirements.txt requirements.in
pip-compile --generate-hashes --strip-extras --allow-unsafe -o requirements-dev.txt requirements-dev.in
```

Review the upstream changes before bumping `ats-scrapers`: it's the largest third-party
code running against live sites in the workflow. The lock must be generated with Python
3.13, the version the workflows use.

## Change what's public or private

Edit `PUBLIC` / `PRIVATE` in `tools/public_template.py` and add a case to
`tests/test_public_template.py`. New kinds of file are private until added to `PUBLIC`.
