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
| Sponsor | Confirmed, Likely, Licensed, Unclear, Unlikely, No | Starts as a **register match only** (Licensed, Unclear or Unlikely): the employer holds a UK/NL sponsor licence, which says it *can* sponsor, not that it will. When Claude checks a role (the ad, the country's rules, the company's own pages), it sets **Confirmed**, **Likely**, **Unlikely** or **No** and adds the evidence, with links, to the card |
| Referral | Finding contact, Asked, Referred, No route, Not needed | Claude, as you tell it about referral asks (each step is also a comment on the card) |
| Posted | date | When the employer posted it; if the source doesn't say, the day job-radar first found it. Sort by it to apply early |

Cards that arrived since your last Claude session may have empty fields: GitHub doesn't
let the automatic runs write to your board's columns, so Claude fills them when you next
open a session (it takes a minute or two, in the background). Until then, "Act now" and
other views that filter on those columns won't show those cards yet; the "All Roles" view
does. Nothing is lost in the meantime.

Moving a role to Offer, Rejected or Skipped closes its issue.

## Each card

The issue behind each card has the link to the posting, the location, the sponsor match,
when it was posted, where else it was found, and its **Role ID**.

Once Claude has checked sponsorship, the card shows a short **Visa sponsorship** note with the
evidence and links.

Once Claude has scored the role, the card also lists what **matches** your CV, what
**partly** matches and what **doesn't match** (blockers first, quoted from the ad). Fit is a
judgement weighted by how much each requirement matters, not a percentage of requirements
met. If a role is re-scored, the list is replaced, not added to.

Only **permanent** roles reach the board: contract, fixed-term, temporary, interim, freelance
and internship roles are filtered out (by job title, and by the employment type where the
job board reports it).

## Radar status card

One pinned issue, edited every run: roles found, how many are waiting for the board,
which sources stopped returning results, and for each source how many listings it found and why
the rest were dropped (wrong country, title, not permanent, or employer not on your list). It holds counts only, no job titles, so it's
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

A card whose job ad seems to have disappeared (no source has listed it for more than 5 days) gets a
`possibly-closed` label, drops out of "Act now", and Claude suggests moving it to Skipped.

That's the guide. Back to [Home](Home.md).
