# job-radar wiki

job-radar is a job-search assistant for AppSec / product security / pentest /
security-consulting roles in Europe. You use it through **two interfaces**:

1. **Claude**: you talk to it in Claude Code, in your private copy of this repo. It
   acts as your recruitment consultant and runs everything for you: setup,
   briefings, fit scoring, tailored CVs and cover letters, tracking, tuning, fixes.
2. **Your GitHub Projects board**: every new role appears as a card, and you (or
   Claude) move it through New → Shortlisted → Applied → Interview → Offer.

You never need to run a script or edit a config file yourself. These pages
explain what happens underneath, for when you're curious or something breaks.

## Pages

| Page | What it covers |
|---|---|
| [Using it](Using-it.md) | What to say to Claude, and what you'll see on the board |
| [Board](Board.md) | How roles become cards, the fields, the Radar status card |
| [Setup](Setup.md) | Public template vs your private copy; first-time setup (Claude does it) |
| [Sources](Sources.md) | Where roles come from, what each costs, what can break |
| [Job-alert emails](Job-alert-emails.md) | LinkedIn / Indeed / Glassdoor alerts by email (no scraping) |
| [Tiers and sponsorship](Tiers-and-sponsorship.md) | Tier 1/2 rules and the UK/NL visa-sponsor tag |
| [Configuration](Configuration.md) | The files in `profile/` that Claude edits for you |
| [Troubleshooting](Troubleshooting.md) | What Claude checks when something looks wrong |
| [Security model](Security-model.md) | Secrets, untrusted job ads, what it will never do |

## How it fits together

```
 GitHub Actions, 3x a day: 08:17, 14:17, 20:17 IST (no one involved)
   fetch alert mail (stdlib-only step: the only place the Gmail password exists)
   → scan ATS boards, EU job portals, careers pages, alert mail
   → filter (country, title) → match your target companies → dedupe → tier + sponsor tag
   → data/matches.csv  +  one issue per new role  ──auto-add──▶  PROJECTS BOARD  ◀── you look
   → "Radar status" card (counts, broken sources)                      ▲
                                                                       │ sets Stage / Fit / …
 You ──talk──▶ CLAUDE (Claude Code, your Pro subscription, no API key) ─┘
               reads matches, scores and your CV; fetches JDs; scores fit; tailors CVs;
               edits your settings; checks health — using the tools in this repo
```

Every role has a short **Role ID** (16 characters, shown on its card). It links the
card, the role's row in `data/matches.csv`, its fit score and its tailored CV.
