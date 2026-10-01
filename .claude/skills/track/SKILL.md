---
name: track
description: Update an application's stage on the GitHub Projects board (shortlisted, applied, interview, offer, rejected, skipped). Use when the user reports progress on an application or says they're not interested in a role.
---

# Track an application

1. Find the role's ref: match the company/title the user mentions against `data/matches.csv`
   (or `gh issue list --label role --search "<company>"` and read "Role ID" in the body). If several
   match, ask which one.
2. Map what they said to a Stage: Shortlisted, Applied, Interview, Offer, Rejected, Skipped.
3. `python tools/board_sync.py set <ref> Stage=<Stage>` (logs the change with a date in
   `data/pipeline_log.jsonl`, which drives follow-up reminders in the session brief). Offer, Rejected and Skipped also close the
   issue. Add `--close` only if the user wants a different stage closed.
   **Always pass the user's reason** when they gave one (why they skipped it, who rejected them and
   how, what the recruiter said): `--note "<one or two plain sentences>"`. It's logged with the stage
   change and posted as a comment on the issue, so the card shows why. Feedback reaches the system
   through the conversation: nothing reads issue comments the user writes themselves.
4. If the board isn't set up or the card doesn't exist yet, say so and offer `setup` / wait for the
   next daily run. Skipped cards are **archived daily** (session start, `board_sync.py archive`), and an
   archived card is invisible to `set`: to change one, tell the user to restore it from the Project's
   Archived items first.
5. Moving to **Applied** → offer the stranger outreach from `referrals` (the user's rule, 2026-10-01: recruiters and other strangers are contacted
   *after* applying, with that role's tailored CV attached; the user writes to people they know before applying). Moving to **Interview** → offer `interview-prep`. Cards labelled `possibly-closed` that the user
   hasn't applied to → suggest Skipped.
6. Confirm in one line. When relevant, suggest the next action (e.g. "want interview prep from your
   STAR stories for this role?").
