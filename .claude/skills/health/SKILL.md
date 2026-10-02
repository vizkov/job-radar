---
name: health
description: Diagnose and fix job-radar problems — silent or failing sources, workflow failures, no new roles, board cards not appearing. Use when the user asks if anything is broken or the status issue shows failures.
---

# Check and fix health

1. Read the latest status: `git pull`, then `digests/status.md` (or the "Radar status" issue) and
   `state/health.json` (per-source `bad_streak`). Check workflow runs: `gh run list --limit 5`, and
   `gh run view <id> --log-failed` for failures.
2. Diagnose by source:
   - **ATS board silent** → company probably moved ATS. `python verify_boards.py --quiet`, then look at
     `data/coverage_report.csv` for that company; find the new careers URL and add it to
     `profile/overrides.csv`.
   - **careers_page "layout changed" / empty** → open the page, update selectors in
     `profile/careers_pages.yaml`, test with `python radar.py --dry-run --include-outside --source careers_page`.
   - **EU source canary failing** → `python radar.py --dry-run --source <name>`; if the API changed, disable
     it in `profile/sources.yaml` and tell the user.
   - **alert_email "mail fetch failed"** → the message says why: secrets not set (walk the user through
     GitHub → Settings → Secrets → Actions), login failed (app password revoked — they create a new one),
     DKIM rejections (check a mail's headers with them).
   - **No board cards** → `state/board_queue.json` still full means the issue step failed (see the run log);
     cards exist but not on the board means the Project's Auto-add workflow is off (`setup` step).
   - **Workflow skipped with a "Public repository" warning** → the repo is public; it must be private.
3. Fix what you can, verify with a dry run, commit, and tell the user what was wrong in one or two lines.
4. Stamp the cadence job: `python tools/cadence.py done health` (the session brief's CADENCE block marks Health DUE once a day
   while the status page lists source problems, so it is run or offered instead of read past).
