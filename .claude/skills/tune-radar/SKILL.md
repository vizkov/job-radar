---
name: tune-radar
description: Change what the radar looks for — titles, exclusions, countries, target companies, sources, tier weights — and show the effect before saving. Use when the user says there's too much noise, wants to add/remove companies or countries, or wants different roles.
---

# Tune the radar

All settings live in `profile/` (copy a file from `examples/` first if it isn't there yet):

| Request | File |
|---|---|
| titles to include/exclude, countries, tier weights | `profile/config.json` (`title_include`, `title_exclude`, `priority_countries`, `tiering`) |
| add/remove a target company | `profile/targets.tsv` (+ board discovery, below) |
| a company appears under another name | `profile/aliases.csv` |
| a company has a careers page without an ATS | `profile/careers_pages.yaml` (see its header; check the page source for a hidden ATS first and prefer `profile/overrides.csv`) |
| turn a source on/off, search terms | `profile/sources.yaml` |
| wrong sponsor match | `profile/sponsor_overrides.csv` |

Steps:
1. Make the smallest change that does what they asked. Title keywords are whole-word; `*` matches
   prefixes; exclude wins over include.
2. **Show the effect before committing:** `python radar.py --dry-run --quiet` for counts, or without
   `--quiet` to list what would appear. For title changes, compare roles gained/lost in the digest.
3. New target company: `python tools/build_candidates.py` (needs `atss/` and `agg/` clones — see
   docs/design/Setup.md) then `python verify_boards.py --quiet`; report whether a board was found. If not,
   look for a careers page and offer to add it.
4. Run `pytest -q` if you touched anything beyond these data files.
5. Tell the user what changed and the before/after numbers; commit to `origin` when they agree.
