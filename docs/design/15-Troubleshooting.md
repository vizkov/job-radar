# 15. Troubleshooting

**What this is:** Symptom → where to look → fix. Claude's `health` skill follows this page.  
**Read first:** [3](03-Scheduled-run.md) and [4](04-Claude-session.md)  
**Code:** `jobradar/health.py`, `digests/status.md`, `.claude/skills/health/`

## No new cards on the board

| Check | How | Fix |
|---|---|---|
| Did the run happen? | `gh run list --workflow job-radar --limit 5` | GitHub sometimes skips scheduled runs; the session brief restarts a skipped one. If runs fail, `gh run view <id> --log-failed` |
| Did it find anything? | `digests/status.md` ("New today"), `data/matches.csv` | Nothing new is normal on quiet days |
| Is it queued? | `state/board_queue.json` | More than 40 new roles wait for the next run (`max_per_run`) |
| Did issues get created but not appear? | Issues labelled `role` exist, cards don't | The Project's **Auto-add to project** workflow is off or has the wrong filter (`is:issue label:role`) |
| Is the tier/company excluded? | `config.json` → `board.tiers`, `include_outside` | Only Tier 1–2 roles at target companies go to the board |

## Cards have empty fields

Fields are set by `board_sync.py fill`, started in the background at session start
(log: `work/board_fill.log`). The scheduled run can't set fields. Run it by hand if needed:
`python tools/board_sync.py fill`. If it errors with a permissions message, the user's `gh`
login lacks the `project` scope: `gh auth refresh -s project`.

## "Sources that stopped returning results"

| Unit | Likely cause | Fix |
|---|---|---|
| ATS board (URL) | Company moved ATS or renamed its board | `verify_boards.py`; if still missing, find the new careers URL (or run `discover_boards.py`) and add it to `profile/overrides.csv` |
| `canary query` | The public API changed or is down | `python radar.py --dry-run --source <name>`; if it keeps failing, disable the source in `sources.yaml` until fixed |
| `<source> (whole source)` | Crash or timeout | The error text is in `digests/status.md`; a timeout may just need a higher `timeout_seconds` |
| `alert emails in the mailbox: no emails at all from …` | No alerts reached the mailbox: alerts not created, paused, sent to another address, or the secret points at a different mailbox | Check the alerts exist and go to the address in `JOBALERT_IMAP_USER`; the run log lists what the mailbox held |
| `<provider> alert sender: … the alert sender may have changed` | The provider now sends alerts from an address not in `alert_providers.py` | Add the address shown to that provider's `senders` |
| `<provider> alert emails with no jobs` | The provider changed its email layout (the status line names the subjects of the emails that yielded nothing) | Save a real alert as a fixture and update the parser in `sources/alert_email.py` |
| `<provider> emails failing DKIM` | Forwarding broke signatures, or spoofing | Check one message's headers (Gmail → Show original) before turning `require_dkim` off |
| careers page: "page layout changed" | Site redesign | Update the selectors in `profile/careers_pages.yaml` |

A unit is flagged after 2 bad runs in a row: always if it reports an error; for zero results only if it has worked before
(`jobradar/health.py`).

## A role I expected isn't there

Check in this order:

1. **Title**: does it pass `config.json`? Exclude wins over include.
2. **Country**: is the location recognisable? Unknown towns without a country name are
   dropped. Add the city to `_CITY_NAMES` in `jobradar/common.py`.
3. **Company**: `python radar.py --dry-run --include-outside --source <name>`. If it
   appears under another spelling, add a row to `profile/aliases.csv`.
4. **Board coverage**: is the company VERIFIED in `data/coverage_report.csv`? If not, it
   has no polled board: add one via `overrides.csv` or a careers page.
5. **Seen before**: search `data/matches.csv`; it may have been reported earlier.

## Too much noise

- Tighten `title_include` ("security engineer" is broad at banks and MSPs) or add
  `title_exclude` words.
- Turn off `include_outside_list` in `sources.yaml` (and `board.include_outside` in `config.json`); see [10](10-Configuration.md#two-different-include-outside-switches).
- Raise `tier1_min_score` or lower title weights in `config.json` → `tiering`.

## Scoring or tailoring is rejected

`jd_check.py` prints each problem. The usual ones: a blocker quote that isn't copied
exactly from the JD, an evidence ID that doesn't exist, a tailored line with a number or
name that isn't in the user's original. Fix the content; never loosen the checker. If the
user's CV genuinely lacks something, tell them.

## A JD can't be fetched

`work/jd/<ref>/packet.md` says `unavailable: …`. LinkedIn, Indeed and Glassdoor are never
fetched; JavaScript-only pages and robots.txt refusals can't be. Ask the user to paste the
JD, save it as `work/jd/<ref>/jd.txt`, and re-run `jd_prep.py --ref <ref>`.

## Publishing to the template didn't happen

The session brief lists unpublished files. Causes: `git config jobradar.templateDir`
unset, the template clone missing, or tests failing in the template (the hook printed why
after the commit). Fix, then `python tools/public_template.py publish <template clone> -m "…"`.
