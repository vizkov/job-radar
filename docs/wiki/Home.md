# job-radar

**This page:** what job-radar is, the words you'll see, and what to read next.

job-radar is a job-search assistant for AppSec, product security, pentest and
security-consulting roles in Europe. It watches the job boards of the companies you want
to work for, three times a day, and puts every new matching role on a board for you. You
use it through **two things only**:

1. **Claude.** You talk to it in Claude Code, in your private copy of this project. It
   acts as your recruitment consultant and does all the operating for you: setup,
   briefings, judging how well a role fits you, tailored CVs and cover letters,
   tracking, tuning the search, fixing what breaks.
2. **Your board.** A GitHub Project where every new role is a card. You (or Claude) move
   each card along: New → Shortlisted → Applied → Interview → Offer.

You never run a script or edit a settings file.

## Read these, in order

| # | Page | What you'll learn |
|---|---|---|
| 1 | [Your part](Your-part.md) | The handful of steps only you can do (a login, a secret, two board clicks) |
| 2 | [Using it](Using-it.md) | What to say to Claude, what happens without you, what it costs, where your data is |
| 3 | [Board](Board.md) | How to read your board: the columns, the views, the status card |

Curious how it works inside? That's [docs/design](../design/README.md), written for
developers and for Claude.

## Words you'll see

| Word | Means |
|---|---|
| **Card** | One job on your board. Behind each card is a GitHub issue with the details and the link to apply. |
| **Stage** | Where you are with a job: New, Shortlisted, Applied, Interview, Offer, Rejected or Skipped. |
| **Tier** | A quick automatic rating from the job title, seniority, country and company. **Tier 1** = strongest match to what you're looking for; Tier 2 = worth a look. |
| **Fit** | Claude's 0–100 judgement of how well your CV matches the job description, set when you ask it to score roles. |
| **Recommendation** | Claude's call after scoring: Apply, Maybe or Skip. |
| **Sponsor** | Whether the employer appears on the UK or Dutch register of companies licensed to sponsor work visas. A match means they *can* sponsor, not that they will for this role. |
| **Posted** | When the employer posted the job. Newer is better: early applications do better. |
| **Role ID** | A 16-character code on each card. Mention it (or just the company and role) and Claude finds everything about that job. |
| **Target companies** | The list of employers you want. Roles elsewhere are ignored unless you ask otherwise. |

## The picture

```
 3x a day, on GitHub's servers (no one involved)
   → check your target companies' job boards, public job portals, your job-alert emails
   → keep matching roles → rate them → one card per new role on your board
                                                        ▲            ◀── you look, drag cards
 You ──talk──▶ CLAUDE (your Claude subscription) ───────┘ fills in Fit, Stage, …
               briefs you, scores fit, tailors CVs, fills forms for you to submit,
               tunes the search, fixes what breaks
```

**Next:** [1. Your part](Your-part.md)
