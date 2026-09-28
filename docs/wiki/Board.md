# Board

Your GitHub Project is the dashboard: one card per role, plus a "Radar status" card.

## How roles become cards

1. The daily run records every new matching role in `data/matches.csv` and queues
   the ones for the board in `state/board_queue.json`: Tier 1 and 2 at companies on
   your list (`profile/config.json` → `board`).
2. `tools/board_sync.py roles` opens one **issue** per queued role in your private
   repo, labelled `role`, `tier-1|2`, `country-XX` and `sponsor-yes|unknown|no`.
   It creates up to 40 per run, 2 seconds apart (GitHub throttles bursts); the rest
   wait for the next run.
3. The Project's built-in **Auto-add to project** workflow (filter
   `is:issue label:role`) puts each issue on the board.
4. The daily run can't edit Project fields (its built-in token has no access to
   user-owned Projects). When you next talk to Claude, it fills **Stage = New**,
   **Tier** and **Sponsor** from the labels, and **Fit** / **Recommendation** once a
   role is scored.

**First run:** the baseline records every open role (about 130 for the author's
targets) but only puts **Tier 1** on the board, so you don't start with a wall of cards.

## Fields

| Field | Values | Set by |
|---|---|---|
| Stage | New, Shortlisted, Applied, Interview, Offer, Rejected, Skipped | Claude (from what you tell it), or you by dragging |
| Tier | T1, T2 | Claude, from the card's label |
| Fit | 0-100 | Claude, after scoring |
| Recommendation | Apply, Maybe, Skip | Claude, after scoring |
| Sponsor | Yes, Unknown, No | Claude, from the label (UK/NL register match) |

Moving a role to Offer, Rejected or Skipped closes its issue; the Project's
"Item closed → Done" workflow, if you turn it on, moves it out of the way.

## Each card

Title `[T1] Company — Role (GB)`. The issue body has the link to the posting, the
location, the tier score and why, the sponsor match, when it was posted, where
else it was found, and its **Role ID**. Job titles and company names are escaped,
so a malicious job ad can't inject links or formatting.

## The Radar status card

One pinned issue, edited every run: roles found today, how many are waiting for
the board, and a table of sources with any that stopped returning results. It
contains counts only, no job titles.

## Notifications

Set the repo's watch level to **Participating and @mentions**. Role issues then
don't email you; the board and Claude replace the old daily email.

## Setup

Claude does it (`setup`): after you run `gh auth refresh -s project` once, it runs
`tools/board_sync.py setup-project`, which creates the Project and fields and
links the repo. One step has no command-line equivalent: in the Project, open
**⋯ → Workflows → Auto-add to project**, set the filter `is:issue label:role`
and turn it on. The GitHub free plan may limit how many auto-add workflows a
Project can have; this setup needs one.
