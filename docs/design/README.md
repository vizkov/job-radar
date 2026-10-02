# job-radar design reference: start here

These pages explain how job-radar works inside, for someone who has never seen it.
Read them in order. By the end you should be able to open any file in the repo and know
what it is for, what each function in it does, what it reads and writes, and why it was
built that way.

If you only want to *use* job-radar, you're in the wrong place: read the user guide in
[docs/wiki](../wiki/Home.md). Claude, which operates the system, uses these pages as its
reference.

## Reading order

| # | Page | You'll learn |
|---|---|---|
| 1 | [Concepts](01-Concepts.md) | Every term used in these docs, in plain words: ATS, Project board, workflow, skill, ref, tier… |
| 2 | [Architecture](02-Architecture.md) | The three places code runs, the folders, and every data file: who writes it, who reads it |
| 3 | [A scheduled run, step by step](03-Scheduled-run.md) | What happens three times a day in GitHub Actions, followed through the code, with one real role's journey |
| 4 | [A Claude session, step by step](04-Claude-session.md) | What happens when the user opens Claude Code: the session brief, skills, scoring, tailoring, applying |
| 5 | [Code reference](05-Code-reference.md) | Every file and every function, one line each, with the subtle lines called out. An index page plus six lookup pages (5.1 entry points, 5.2 the package, 5.3 sources, 5.4 board and session tools, 5.5 application tools, 5.6 setup tools and config): skim the index now, open a sub-page when you open a file |
| 6 | [Tests](06-Tests.md) | How the tests are organised, what each covers, how they stay offline and isolated |
| 7 | [Changing it](07-Changing-it.md) | Recipes: add a source, a setting, a board field or view, a skill, a dependency |

## Deep dives (8–15: read when you need them)

| # | Page | Covers |
|---|---|---|
| 8 | [Sources](08-Sources.md) | Each place roles come from: what it costs, what breaks, how to add one |
| 9 | [Tiers and sponsorship](09-Tiers-and-sponsorship.md) | The fit score and the UK/NL visa-sponsor match, with worked examples |
| 10 | [Configuration](10-Configuration.md) | Every settings file in `profile/` |
| 11 | [Board internals](11-Board-internals.md) | Issues → cards, labels vs fields, views as code |
| 12 | [Job-alert emails](12-Job-alert-emails.md) | LinkedIn/Indeed/Glassdoor alerts: the secret isolation and anti-spoofing |
| 13 | [Security model](13-Security-model.md) | Threats and the defence for each |
| 14 | [Setup and publishing](14-Setup-and-publishing.md) | Public template vs private copy, first-time setup, auto-publishing |
| 15 | [Troubleshooting](15-Troubleshooting.md) | Symptoms → causes → fixes |

## Conventions in these pages

- Every page opens with **What this is**, **Read first** and **Code** (the files it covers).
- Paths are relative to the repo root: `tools/board_sync.py`, `profile/config.json`.
- `function()` names are given with their file the first time: `radar.py: select()`.
- **"Private"** means the file exists only in the user's private copy and is never
  published. **"Public"** means it ships in the public template.
- "The user" is the job seeker. "Claude" is the AI operating the system for them.
