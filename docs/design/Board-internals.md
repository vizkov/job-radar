# Board internals

What the user sees is in [docs/wiki/Board.md](../wiki/Board.md). This page is how it works.

## How roles become cards

1. Each scheduled run records every new matching role in `data/matches.csv` and queues
   the ones for the board in `state/board_queue.json`: Tier 1 and 2 at companies on
   the list (`profile/config.json` → `board`).
2. `tools/board_sync.py roles` opens one **issue** per queued role in the private
   repo, labelled `role`, `tier-1|2`, `country-XX`, `sponsor-yes|unknown|no`.
   Up to 40 per run, 2 seconds apart (GitHub throttles bursts); the rest wait.
3. The Project's built-in **Auto-add to project** workflow (filter `is:issue label:role`)
   puts each issue on the board.
4. The run can't edit Project fields (its built-in token has no access to user-owned
   Projects), so labels are its only way to attach data. At session start Claude runs
   `board_sync.py fill` with the user's local `gh` login (project scope): **Stage = New**,
   **Tier** and **Sponsor** from the labels, **Posted** from the issue body (else the day first
   seen, from `data/matches.csv`), **Fit** / **Recommendation** from scores.
5. `board_sync.py stale` labels roles no source has listed for `stale_days` as
   `possibly-closed` (and removes the label if they come back).

**First run:** the baseline records every open role but only puts `baseline_tiers`
(Tier 1) on the board.

## Setup

`setup` skill: after `gh auth refresh -s project`, `tools/board_sync.py setup-project`
creates the Project and fields, links the repo, then builds the views. The Auto-add
workflow is a manual step (see [Your part](../wiki/Your-part.md)).

## Views as code

The views are defined in `VIEWS` in `tools/board_sync.py`: name, layout, filter, visible
columns, sort and board grouping. `board_sync.py views` creates or updates the board to
match (GraphQL `createProjectV2View` / `updateProjectV2View`), so every copy gets the same
board. The API sets name, layout, filter and columns, but **not sort or grouping**: for those
it prints the exact menu clicks for the user, once per view.

The session brief runs `design-diff`. If the user changed a view on purpose, Claude updates
`VIEWS` (the commit publishes it to the template, so new copies get it); if not, it offers
`board_sync.py views` to restore it. Extra views the user adds are left alone.
