# 3. Board

**This page:** how to read your board: its columns, views and the status card.

Your GitHub Project is the dashboard: one card per role, plus a "Radar status" card.
New cards arrive three times a day. (How they get there, for the curious:
[Board internals](../design/11-Board-internals.md).)

**If a view looks empty:** cards that arrived since your last Claude session may have blank Stage, Tier, Country or
Posted fields until Claude next opens (it fills them at the start of every session), and views filter on those.
The **All Roles** view shows every card except the ones you've already applied to, so it still shows the blank ones.

## Fields

| Field | Values | Set by |
|---|---|---|
| Stage | New, Shortlisted, Applied, Interview, Offer, Rejected, Skipped | Claude (from what you tell it), or you by dragging |
| Country | CH, DE, GB, IE, NL, SE, REMOTE-EU | The first country the ad lists; Claude copies it onto the card |
| Tier | T1, T2 | A rule-based guess when the role is found, copied onto the card by Claude. Once a role is scored, **Apply** makes it T1 and **Skip** makes it T2 |
| Fit | 0-100 | Claude, after scoring |
| Recommendation | Apply, Maybe, Skip | Claude, after scoring |
| Sponsor | Confirmed, Likely, Licensed, Unclear, Unlikely, No | Starts as a **register match only** (Licensed, Unclear or Unlikely): the employer holds a UK/NL sponsor licence, which says it *can* sponsor, not that it will. When Claude checks a role (the ad, the country's rules, the company's own pages), it sets **Confirmed**, **Likely**, **Unlikely** or **No** and adds the evidence, with links, to the card |
| Referral | Finding contact, Asked, Referred, No route, Not needed | Claude, as you tell it about referral asks (each step is also a comment on the card) |
| Posted | date | When the employer posted it; if the source doesn't say, the day job-radar first found it. Sort by it to apply early |

Cards that arrived since your last Claude session may have empty fields: GitHub doesn't
let the automatic runs write to your board's columns, so Claude fills them when you next
open a session (it takes a minute or two, in the background). Until then, "Act now" and
other views that filter on those columns won't show those cards yet; the "All Roles" view
does. Nothing is lost in the meantime. If a column you add later is empty on older cards, Claude
notices at the start of the next session and fills it in by itself, wherever it can work the value out.

Moving a role to Offer, Rejected or Skipped closes its issue. It works the other way too: if you
**close a card** (or mark it Done) that you hadn't acted on, Claude sets its Stage to Skipped at your
next session. If it was Applied or at Interview, Claude asks what happened instead of guessing.
**A role scored Skip goes straight to Skipped.** When Claude rates a role Skip and you haven't acted
on its card, the card moves to Skipped (its issue closes with a note). Cards you've shortlisted or
applied to are never moved: those are your decisions.

**Skipped or Rejected roles lose their tailored application.** If a role you skip or get rejected from has a folder in
`profile/applications/` (the CV and cover letter Claude built), Claude deletes that folder and tells you. The job description
and the score are kept. Roles you applied to, or that are at Interview or Offer, keep theirs.

**Skipped cards are archived once a day.** The first time you open a session each day, cards in the
Skipped stage are archived (up to 40 a day; a bigger backlog clears over the next days). Archiving
hides a card from every view without deleting it: open the Project's menu, choose **Archived items**,
and restore one if you change your mind. Because an archived card is off the board, tell Claude to
restore it before changing its stage.
GitHub also shows its own **Status** column (Todo / In Progress / Done); job-radar doesn't use it,
so Stage is the one to watch.

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
the rest were dropped (wrong country, title, not permanent, posted too long ago, or employer not on your list). It holds counts only, no job titles, so it's
safe to screenshot or share when asking for help. Like everything in your repo, only you
can see it.

## Views

| View | What it's for |
|---|---|
| **Act now** | Open roles you haven't applied to or skipped that are either brand new or posted 14 or more days ago (the ones about to expire: apply before they close), best fit first |
| **All Roles** | Every role you haven't applied to yet, best fit first |
| **Pipeline** | A board with one column per Stage; drag cards as things happen |

**Your layout is yours.** You can change a view's filter, columns or column order in GitHub whenever you like. Claude never
reorders your columns. When you change a filter or add or remove a column, Claude notices at the start of the next session and
copies your layout into the system's saved design, so it survives a rebuild of the board. Claude won't undo a change unless you say it was
a mistake.

Want another view, say "Tier 2 only" or "jobs whose ad may have been taken down"? Ask
Claude. It adds the view to your board and saves it with your copy of job-radar, so it comes back if
the board is ever rebuilt. (It changes only your board, nobody else's.)

A card whose job ad seems to have disappeared (no source has listed it for more than 5 days) gets a
`possibly-closed` label, drops out of "Act now", and Claude suggests moving it to Skipped.

That's the guide. Back to [Home](Home.md).
