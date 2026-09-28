---
name: track
description: Update an application's stage on the GitHub Projects board (shortlisted, applied, interview, offer, rejected, skipped). Use when the user reports progress on an application or says they're not interested in a role.
---

# Track an application

1. Find the role's ref: match the company/title the user mentions against `data/matches.csv`
   (or `gh issue list --label role --search "<company>"` and read "Role ID" in the body). If several
   match, ask which one.
2. Map what they said to a Stage: Shortlisted, Applied, Interview, Offer, Rejected, Skipped.
3. `python tools/board_sync.py set <ref> Stage=<Stage>`. Offer, Rejected and Skipped also close the
   issue (the Project moves it to Done). Add `--close` only if the user wants a different stage closed.
4. If the board isn't set up or the card doesn't exist yet, say so and offer `setup` / wait for the
   next daily run.
5. Confirm in one line. When relevant, suggest the next action (e.g. "want interview prep from your
   STAR stories for this role?").
