# 3. Board

**This page:** how to read your board: its columns, views and the status card.

Your GitHub Project is the dashboard: one card per role, plus a "Radar status" card.
New cards arrive three times a day. (How they get there, for the curious:
[Board internals](../design/11-Board-internals.md).)

## Fields

| Field | Values | Set by |
|---|---|---|
| Stage | New, Shortlisted, Applied, Interview, Offer, Rejected, Skipped | Claude (from what you tell it), or you by dragging |
| Tier | T1, T2 | Worked out automatically when the role is found; Claude copies it onto the card |
| Fit | 0-100 | Claude, after scoring |
| Recommendation | Apply, Maybe, Skip | Claude, after scoring |
| Sponsor | Yes, Unknown, No | Claude (UK/NL register match; a name match, not a promise) |
| Posted | date | When the employer posted it; if the source doesn't say, the day job-radar first found it. Sort by it to apply early |

Cards that arrived since your last Claude session may have empty fields: GitHub doesn't
let the automatic runs write to your board's columns, so Claude fills them when you next
open a session (it takes a minute or two, in the background). Until then, "Act now" and
other views that filter on those columns won't show those cards yet; the "All Roles" view
does. Nothing is lost in the meantime.

Moving a role to Offer, Rejected or Skipped closes its issue.

## Each card

The issue behind each card has the link to the posting, the location, the tier score and
why, the sponsor match, when it was posted, where else it was found, and its **Role ID**.

## Radar status card

One pinned issue, edited every run: roles found, how many are waiting for the board,
and which sources stopped returning results. It holds counts only, no job titles, so it's
safe to screenshot or share when asking for help. Like everything in your repo, only you
can see it.

## Views

| View | What it's for |
|---|---|
| **Act now** | Tier 1 roles posted in the last 14 days that you haven't acted on or ruled out, newest first. Start here: applying early matters |
| **All Roles** | Everything, best fit first |
| **Pipeline** | A board with one column per Stage; drag cards as things happen |

Want another view, say "Tier 2 only" or "jobs whose ad may have been taken down"? Ask
Claude. It adds the view to your board and saves it with your copy of job-radar, so it comes back if
the board is ever rebuilt. (It changes only your board, nobody else's.)

A card whose job ad seems to have disappeared (no source has listed it for 5 days) gets a
`possibly-closed` label, drops out of "Act now", and Claude suggests moving it to Skipped.

That's the guide. Back to [Home](Home.md).
