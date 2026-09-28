---
name: consultant-brief
description: Brief the user on their job search — new roles since last time, best matches, pipeline status on the board, and anything broken. Use when the user asks what's new, how the search is going, or opens a session without a specific task.
---

# Brief the user

1. `git pull` (the daily Action commits new data), then gather:
   - New roles: `data/matches.csv` rows since the last briefing (ask, or default to the last 7 days),
     grouped by tier; note on-list vs outside-list.
   - Scores: `data/scores.jsonl` (fit, recommendation, blockers).
   - Board: `python tools/board_sync.py fill` first (sets Stage/Tier/Sponsor on cards the Action added),
     then `gh project item-list <number> --owner <owner> --format json` (coordinates in
     `profile/board.json`) for how many are New / Shortlisted / Applied / Interview.
   - Health: the "Radar status" issue (`gh issue list --label radar-status`) or `digests/status.md`.
2. **Tell them, in this order, briefly:**
   - The 3-5 roles most worth their time (Tier 1, best fit, sponsor yes), each with one line on why.
   - Unscored Tier 1 roles — offer to score them.
   - Pipeline: applications waiting on a reply for 2+ weeks (suggest a follow-up), interviews coming up.
   - Anything broken, in one line (details via `health` if they want).
3. **Recommend a next step** (score these, tailor that one, drop a noisy keyword). Don't dump tables;
   they can see the board.
