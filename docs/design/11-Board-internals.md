# 11. Board internals

**What this is:** How a role becomes a card, why data travels as labels first and fields later, and how the board's views are kept identical in every copy.  
**Read first:** [3.3](03-Scheduled-run.md#33-after-radarpy-board_syncpy-in-actions) and [4.2](04-Claude-session.md#42-session-start-toolssession_briefpy)  
**Code:** `jobradar/board.py`, `tools/board_sync.py`, `profile/board.json`

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
   seen, from `data/matches.csv`). **Fit** and **Recommendation** are set separately, by
   `jd_check.py score --board` when a role is scored.
5. `board_sync.py stale` labels roles no source has listed for `stale_days` as
   `possibly-closed` (and removes the label if they come back).
6. **Archiving Skipped cards** (`board_sync.py archive`) is not in the Action: the Action's token has no
   access to the user's Project, so the session-start hook (`session_brief.start_archive`) runs it in the
   background at most once a day, capped at 40 cards a run. Archived cards leave `item-list`, so
   `find_item` (and `set`) can't see them until they're restored from the Project's Archived items.

**First run:** the baseline records every open role but only puts `baseline_tiers`
(Tier 1) on the board.

## Setup

`setup` skill: after `gh auth refresh -s project`, `tools/board_sync.py setup-project`
creates the Project and fields, links the repo, then builds the views. The Auto-add
workflow is a manual step (see [Your part](../wiki/Your-part.md)).

## Stage vs GitHub's Status

Projects has a built-in **Status** field (Todo / In Progress / Done) that its "Item closed" workflow
sets to Done. job-radar tracks **Stage** instead. The session brief reconciles the two
(`closed_cards()`), and the *Act now* view filters `is:open`, so a card the user closes leaves it.

## What's on a card

The issue body (`board.py: payload()`): company and location, the posting link, sponsor match,
posted date, where else it was found, the Role ID and the hidden ref marker. The tier is a label
and a field only; how it was computed stays in `data/matches.csv`.

Claude adds to it later:
- **Fit breakdown** (`jd_check.py score --board` → `board_sync.set_fit_section()`): Matches, Partly,
  Doesn't match (blockers first, quoted), between `<!-- job-radar:fit -->` markers, replaced on a
  re-score. `board_sync.py refresh-bodies` updates existing cards (and removed the tier line older
  cards carried).
- **Promoting a recorded role** (`board_sync.py promote <ref> …`, then `roles`): roles that are in
  `matches.csv` but never got a card (the first run cards only `baseline_tiers`) are queued from their
  CSV row by `board.row_payload()`, an equivalent title, body, marker and labels to what a radar run gives them ("Also on" is plain text there, not links).
  Claude does this for Tier 2 roles that score apply or maybe.
- **Visa sponsorship block** (`tools/sponsorship.py record --board`): verdict, summary and up to 4
  evidence lines with links, between `<!-- job-radar:visa -->` markers.
- **Comments** with the user's reasons (`board_sync.py set … --note`) and each referral step
  (`tools/referrals.py`).

All text is read from and written to GitHub as UTF-8 (`Gh`); Windows' default code page once
garbled every card's dashes and umlauts when bodies were rewritten.

## Views as code

The views are defined in `VIEWS` in `tools/board_sync.py`: name, layout, filter, visible
columns, sort and board grouping. `board_sync.py views` creates or updates the board to
match (GraphQL `createProjectV2View` / `updateProjectV2View`), so every copy gets the same
board. The API sets name, layout, filter and columns, but **not sort or grouping**: for those
it prints the exact menu clicks for the user, once per view. Columns are compared as a set: GitHub appends a new
column at the end whatever order the API is given, so order isn't treated as drift.

The session brief runs `design-diff`. If the user changed a view on purpose, Claude updates
`VIEWS` (the commit publishes it to the template, so new copies get it); if not, it offers
`board_sync.py views` to restore it. Extra views the user adds are left alone.
