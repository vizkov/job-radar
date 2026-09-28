---
name: system-review
description: Weekly health and design-gap review of job-radar — failing or silent sources, coverage gaps, parser drift, noisy filters, stale workflows, unused features — producing a ranked list of fixes for the user to approve. Use when the session brief says a weekly review is due, or the user asks what could be improved.
---

# Weekly system review

Goal: find what is broken, degrading or missing, and propose small, specific patches. **Propose, don't
apply**: code or config changes happen only after the user says yes.

1. **Gather facts (read-only).** Spawn one review subagent (Explore) with this brief, so the raw logs stay out
   of the main conversation:
   - last 7 days of `state/health.json` streaks, `digests/*.md` source tables, `gh run list --limit 21`
     (failures, durations creeping toward the 60-minute timeout);
   - coverage: `data/coverage_report.csv` rows not VERIFIED for targets the user cares about (security
     consultancies first), and `profile/careers_pages.yaml` pages erroring;
   - noise vs signal: share of `data/matches.csv` rows later scored "skip" in `data/scores.jsonl`, grouped
     by title keyword and source (which include keywords produce mostly skips?);
   - freshness: median days between `posted` and `date` per source (which sources report late?);
   - tier calibration: Tier 1 roles scored "skip" vs Tier 2 roles scored "apply";
   - alert emails: per-provider counts from the Sources table; any "yielded no jobs" / DKIM rejections;
   - pipeline: `data/pipeline_log.jsonl` (applications with no movement, cards stuck in New for 2+ weeks,
     `possibly-closed` cards not yet moved);
   - career docs: missing files, and `cv-review` findings if there are 5+ scores;
   - new boards: run `python tools/discover_boards.py --limit 40` and list what it found in
     `work/discovered_boards.csv` (a slug guess can hit a same-name company: check the titles look right);
   - board design: `python tools/board_sync.py design-diff`.
   Ask it to return a table: finding, evidence (numbers), impact on the user's search, proposed fix, effort.
2. **Check the proposals yourself** against the code before presenting them: a fix must name the file and
   the change. Drop anything speculative.
3. **Present** the top 3-7 findings ranked by impact on getting interviews, each with the concrete patch
   (config change, alias, careers page, parser fix, workflow change). Separate "config/data only" from
   "code change".
4. **Apply only what the user approves.** Commit to the private repo; the post-commit hook publishes
   code changes to the public template. Approved boards: `discover_boards.py --apply`, then
   `gh workflow run verify-boards`. Approved board-design changes: `board_sync.py publish-board`. Run `pytest`.
5. **Record the review:** write the current UTC time to `work/.last_review` and append a one-paragraph
   summary to `docs/reviews.md` in the private repo (date, findings, what was applied), then commit.
