---
name: tune-radar
description: Change what the radar looks for — titles, exclusions, countries, target companies, sources, tier weights — and show the effect before saving. Use when the user says there's too much noise, wants to add/remove companies or countries, or wants different roles.
---

# Tune the radar

All settings live in `profile/` (copy a file from `examples/` first if it isn't there yet):

| Request | File |
|---|---|
| titles to include/exclude, countries, tier weights | `profile/config.json` (`title_include`, `title_exclude`, `priority_countries`, `tiering`) |
| ignore old roles ("skip anything posted over a month ago") | `profile/config.json` `max_age_days` (0 = no limit; undated roles are kept). It only stops new finds: move existing old cards to Skipped with `track` |
| add/remove a target company | `profile/targets.tsv` (+ board discovery, below) |
| a company appears under another name | `profile/aliases.csv` |
| a company has a careers page without an ATS | `profile/careers_pages.yaml` (see its header; check the page source for a hidden ATS first and prefer `profile/overrides.csv`) |
| turn a source on/off, search terms | `profile/sources.yaml` |
| wrong sponsor match | `profile/sponsor_overrides.csv` |
| a board lists fake or wrong jobs (placeholder or same-name company) | `profile/board_blocklist.csv` (`ats,slug,board_url,reason`), and remove its entry from `boards.json` now: the blocklist stops `verify_boards.py` re-adding it on its monthly run |

Steps:
1. Make the smallest change that does what they asked. Title keywords are whole-word; `*` matches
   prefixes; exclude wins over include.
2. **Show the effect before committing:** `python radar.py --dry-run --quiet` for counts, or without
   `--quiet` to list what would appear. For title changes, compare roles gained/lost in the digest.
3. New target company: `python tools/build_candidates.py` (needs `atss/` and `agg/` clones — see
   docs/design/14-Setup-and-publishing.md) then `python verify_boards.py --quiet`; report whether a board was found. If not,
   look for a careers page and offer to add it.
4. Run `pytest -q` if you touched anything beyond these data files.
   **Expanding a domain's company list (the user, 2026-10-20: "find a company's competitors to expand the list for a domain"; Adyen and Mollie were only the example).**
Works for any domain the user targets (fintech, aviation, healthcare…), not one hardcoded list.
   1. Seeds: the companies in `targets.tsv` whose `Sector` tag is the domain (or the ones the user names).
   2. For each seed, find its direct competitors and close peers with WebSearch / WebFetch on public pages (analyst lists, the seed's own "alternatives" pages, trade press);
      never LinkedIn, Indeed or Glassdoor. Group them by what they compete on (for example enterprise acquiring vs SMB checkout), and note the source for each.
   3. Drop what cannot fit: no site or hiring in `priority_countries` / `extra_countries`, no sign of a security team, or already in `targets.tsv`.
   4. Show the user a table (company, HQ and offices, competes with, source, sponsor register hit, **verified or unverified**) and add only on their yes: `Sector` set to the domain tag,
      `Fit` Medium unless they rate it (Fit is theirs), offices only where the source says so. Names recalled from memory without a source stay marked unverified.
   5. `python tools/discover_boards.py --company "<name>"` for each addition (it overwrites `work/discovered_boards.csv` on every run: read each result before the next), reject a slug that
      hits a same-name company elsewhere, `--apply` only the good ones, then `python verify_boards.py --quiet`. No public board: `profile/careers_pages.yaml`, or the Chrome careers queue (`tools/careers_queue.py`) for companies the user cares about.
   6. Cap a pass at about 15 additions so the radar does not fill with noise, and compare matches before and after with `radar.py --dry-run`.

**Pause / resume:** `gh workflow disable job-radar` / `gh workflow enable job-radar` (the scheduled
   search only; the board and data stay). Confirm with `gh workflow list`, and tell the user no new roles
   arrive while paused.
5. Tell the user what changed and the before/after numbers; commit to `origin` when they agree.
