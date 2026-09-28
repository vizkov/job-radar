# Troubleshooting

## "Sources that stopped returning results"

| Unit | Likely cause | Fix |
|---|---|---|
| ATS board (URL) | Company moved ATS or renamed its board | Re-run `verify_boards.py`; if still missing, find the new careers URL and add it to `profile/overrides.csv` |
| `canary query` | The public API changed or is down | `python radar.py --dry-run --source <name>`; if it errors consistently, disable the source in `sources.yaml` until fixed |
| `<source> (whole source)` | Crash or timeout | Error text is in the digest; a timeout may just need a higher `timeout_seconds` |

## A role I expected isn't in the digest

Check in this order:

1. **Title**: does it pass `config.json`? Exclude wins over include.
2. **Country**: is the location recognizable? Unknown towns without a country
   name are dropped. Add the city to `_CITY_NAMES` in `jobradar/common.py`.
3. **Company**: run with `--include-outside`. If it appears there under another
   name, add an alias.
4. **Seen before**: it may have been reported in an earlier digest (see
   `data/matches.csv`).

## Too much noise

- Tighten `title_include` ("security engineer" is broad at banks and MSPs) or
  add excludes.
- Turn off `include_outside_list`.

## The GitHub issue is cut off

Issues are capped at 65,536 characters. The issue is truncated and links to the
full digest in `digests/`. This mainly happens on the first (baseline) run.
