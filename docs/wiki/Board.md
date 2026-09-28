# Board

Your GitHub Project is the dashboard: one card per role, plus a "Radar status" card.
New cards arrive three times a day. How they get there:
[Board internals](../design/Board-internals.md).

## Fields

| Field | Values | Set by |
|---|---|---|
| Stage | New, Shortlisted, Applied, Interview, Offer, Rejected, Skipped | Claude (from what you tell it), or you by dragging |
| Tier | T1, T2 | Claude, from the role's tier |
| Fit | 0-100 | Claude, after scoring |
| Recommendation | Apply, Maybe, Skip | Claude, after scoring |
| Sponsor | Yes, Unknown, No | Claude (UK/NL register match; a name match, not a promise) |
| Posted | date | Claude: when the employer posted it, or when the radar first saw it. Sort by it to apply early |

Cards that arrived since your last Claude session may have empty fields: the scheduled
run can't write Project fields, so Claude fills them when you next open a session.

Moving a role to Offer, Rejected or Skipped closes its issue.

## Each card

The issue behind each card has the link to the posting, the location, the tier score and
why, the sponsor match, when it was posted, where else it was found, and its **Role ID**.

## Radar status card

One pinned issue, edited every run: roles found, how many are waiting for the board,
and which sources stopped returning results. Counts only, no job titles.

## Views

| View | What it's for |
|---|---|
| **Act now** | Tier 1 roles you haven't acted on, newest first. Start here: applying early matters |
| **All Roles** | Everything, best fit first |
| **Pipeline** | A board with one column per Stage; drag cards as things happen |

Want another view, say Tier 2 only (`tier:T2 -stage:Rejected,Skipped`) or cards whose listing may
have closed (`label:possibly-closed`)? Ask Claude: it adds it to the board's design so every copy
gets it. Filters can use labels even though the Labels column is hidden.
