# 5.1 Entry points

**What this is:** The two scripts that run in GitHub Actions: the daily pipeline and the monthly board verifier.  
**Read first:** pages [2](02-Architecture.md) and [3](03-Scheduled-run.md)  
**Code:** `radar.py`, `verify_boards.py`  

Part of the [5. Code reference](05-Code-reference.md) (the index of every file and function).

---

## `radar.py`: the scheduled pipeline

Runs every source, filters, matches, dedupes, finds what's new, enriches, writes reports,
state and the board queue. Walkthrough: [page 3](03-Scheduled-run.md).
CLI: `--dry-run` (write nothing), `--source NAME` (only that source), `--quiet` (counts
only), `--include-outside` (keep employers not on the list).

| Function | Does |
|---|---|
| `STATE`, `DIGESTS`, `DATA` | The `state/`, `digests/` and `data/` folders. |
| `load(path, default)` | Reads a JSON file, or returns `default` if it doesn't exist. |
| `UNRECOGNISED`, `UNRECOGNISED_N` | Per source, up to 30 distinct sample locations of listings whose **title matched** but where no country was found, and how many such listings there were: possible real losses, listed in the digest so missing places can be added to `_CITY_NAMES`. Module-level and never reset: they add up across `select()` calls in one process (one per run in practice; tests reset them). |
| `DROP_REASONS`, `drop_lines(results, matched, dropped)` | Why a listing was dropped (country, title, employment, company), and one status line per source: found → dropped by reason → kept. |
| `select(results, include_outside, matcher, dropped)` | Country filter, title filter, company matching; returns kept postings and per-source match counts. `include_outside` is a bool or a per-source dict. |
| `diff_seen(groups, seen, today)` | Returns groups none of whose keys are in `seen`; stamps all their keys with today. |
| `enrich(new, sponsors)` | Adds sponsor tags, score, tier and reasons to each new group's `tags`. |
| `_sponsor_note(g)` / `_line(g)` | One digest line for a group: escaped title link, location, posted date, sponsor note, "also on" links. |
| `_by_score(groups)` | Sort by score descending, then title. |
| `render_digest(...)` | The full Markdown digest (tiers → companies → roles, outside list, broken sources, source table). |
| `render_status(...)` | The short "Radar status" text: counts, source table and per-source drop reasons, no job titles. |
| `append_matches(new, today)` | Appends one row per new group to `data/matches.csv`, migrating the header if columns changed. |
| `main(argv)` | The sequence: load → fetch → select → group → diff → enrich → health → render → queue → write. |

**Watch out**
- `baseline = not seen`: an empty `seen.json` means first run, which sends only
  `baseline_tiers` to the board. Deleting `seen.json` re-triggers baseline behaviour.
- The stale check runs only when `healthy` (all sources OK, at most `max(3, len(units)//10)` units erroring) and not
  with `--source`, so an outage or a partial test run can't mark roles closed.
- `seen` pruning (120 days) happens before the stale check, so roles unseen that long
  count as stale.
- `sys.stdout.reconfigure(encoding="utf-8")`: Windows consoles default to cp1252 and would
  crash on non-ASCII job titles.
- `GITHUB_OUTPUT`: when running in Actions, the counts are exposed as step outputs.

## `verify_boards.py`: which ATS boards to poll

Reads `data/candidates.csv` and `profile/overrides.csv`, fetches every board live, keeps
boards that list jobs in the target countries. Writes `data/verified_boards.csv` (per
board), `data/coverage_report.csv` (per company) and `boards.json` (what the `ats`
source polls). Run monthly by `verify.yml`, and after target or override changes.

| Function | Does |
|---|---|
| `load_candidates()` | Candidate rows plus override rows. An override has a careers URL (the ATS is detected with `ats_scrapers.resolve_careers_url()`) or explicit `ats` + `slug` columns. An override replaces the "not covered" row for that company. |
| `careers_page_companies()` | Companies with an enabled `careers_pages.yaml` entry: covered by the careers_page source even without an ATS board. |
| `main(argv)` | Fetch all boards concurrently; compute jobs in target countries per board; mark each company VERIFIED / no jobs in target countries / boards empty / fetch error / not covered, or "careers page" when not VERIFIED but in `careers_pages.yaml`; write the three outputs. |

**Watch out**
- For Workday, Phenom and Oracle the "slug" passed to the scraper is the full URL (those
  scrapers need it); elsewhere it's the short slug.
- A board with jobs but none in target countries is rejected: that's how a same-name US
  company, or the wrong regional tenant, is filtered out.
- An override with only `ats` and `slug` gets the pseudo-URL `ats:slug` as its key.
