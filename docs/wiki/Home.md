# job-radar

job-radar is a job-search assistant for AppSec / product security / pentest /
security-consulting roles in Europe. You use it through **two interfaces**:

1. **Claude**: you talk to it in Claude Code, in your private copy of this repo. It
   acts as your recruitment consultant and runs everything for you: setup,
   briefings, fit scoring, tailored CVs and cover letters, tracking, tuning, fixes.
2. **Your GitHub Projects board**: every new role appears as a card, and you (or
   Claude) move it through New → Shortlisted → Applied → Interview → Offer.

You never run a script or edit a config file. This wiki covers only what **you**
see and do; how the system works inside is in [docs/design](../design/README.md),
which is Claude's reference (and a maintainer's).

## Pages

| Page | What it covers |
|---|---|
| [Using it](Using-it.md) | What to say to Claude, what happens without you, costs, where your data lives |
| [Board](Board.md) | Reading the board: fields, cards, the Radar status card, extra views |
| [Your part](Your-part.md) | The few steps only you can do (logins, secrets, two board clicks) |

## The picture

```
 GitHub Actions, 3x a day: 08:17, 14:17, 20:17 IST (no one involved)
   → scan company job boards, EU job portals, careers pages, your alert emails
   → keep roles at your target companies → tier + visa-sponsor tag
   → one card per new role on your board                 ◀── you look, drag cards
                                                              ▲
 You ──talk──▶ CLAUDE (Claude Code, your Pro subscription) ───┘ sets Stage / Fit / …
               briefs you, scores fit, tailors CVs, fills forms for you to submit,
               tunes the search, fixes what breaks
```

Every role has a short **Role ID** (16 characters, shown on its card). Mention a
company and role, or the ID, and Claude finds everything about it.
