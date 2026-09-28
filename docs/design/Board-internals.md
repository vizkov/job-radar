# Board internals

What the user sees is in [docs/wiki/Board.md](../wiki/Board.md). This page is how it works.

## How roles become cards

1. Each scheduled run records every new matching role in `data/matches.csv` and queues
   the ones for the board in `state/board_queue.json`: Tier 1 and 2 at companies on
   the list (`profile/config.json` → `board`).
2. `tools/board_sync.py roles` opens one **issue** per queued role in the private
   repo, labelled `role`, `tier-1|2`, `country-XX`, `sponsor-yes|unknown|no` (and `fresh`).
   Up to 40 per run, 2 seconds apart (GitHub throttles bursts); the rest wait.
3. The Project's built-in **Auto-add to project** workflow (filter `is:issue label:role`)
   puts each issue on the board.
4. The run can't edit Project fields (its built-in token has no access to user-owned
   Projects), so labels are its only way to attach data. At session start Claude runs
   `board_sync.py fill` with the user's local `gh` login (project scope): **Stage = New**,
   **Tier** and **Sponsor** from the labels, **Fit** / **Recommendation** from scores.
5. `board_sync.py stale` labels roles no source has listed for `stale_days` as
   `possibly-closed` (and removes the label if they come back).

**First run:** the baseline records every open role but only puts `baseline_tiers`
(Tier 1) on the board.

## Setup

`setup` skill: after `gh auth refresh -s project`, `tools/board_sync.py setup-project`
creates the Project (copying the board template), fields, and links the repo. The
Auto-add workflow is the manual step (see [Your part](../wiki/Your-part.md)).

## Board template (for new copies)

The design lives in a public, empty Project (`board.template` in `config.json`, currently
https://github.com/users/vizkov/projects/3). `setup-project` copies it, so a new user gets
the same fields and views. GitHub doesn't copy the repo-specific Auto-add workflow.

When the board's design changes, the session brief notices (`board_sync.py design-diff`)
and Claude offers `board_sync.py publish-board`: it copies the board's design (never its
cards) to a new public Project, closes the old one and updates `board.template` in
`profile/config.json` and `examples/config.json`; the next commit publishes the latter.
GitHub has no API to edit a view's columns, and Claude in Chrome view saves did not persist
when tried (2026-09-28), so view edits are the user's.
