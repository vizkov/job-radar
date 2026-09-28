# job-radar

A job-search assistant for AppSec, product security, pentest and security-consulting
roles in Europe. Three times a day it checks the job boards of the companies you want to
work for (plus public EU job portals and, optionally, your LinkedIn/Indeed/Glassdoor alert
emails), keeps the roles that match, rates them, flags UK/NL visa sponsors, and puts each
new one on your GitHub Projects board.

You use it through **two interfaces**:

1. **Claude** (Claude Code, in your private copy of this repo) acts as your recruitment
   consultant and operates everything: setup, briefings, fit scoring against your CV,
   tailored CVs and cover letters, tracking, tuning, fixes. It runs on your Claude
   subscription: **no API key**.
2. **A GitHub Projects board**: one card per role, moving from New to Offer.

## What it will never do

- Log in to LinkedIn or any job portal with your credentials, or scrape LinkedIn, Indeed
  or Glassdoor. Their own alert emails are read instead. (One opt-in exception you can switch
  on: looking up a recruiter or hiring manager on LinkedIn for one role you're applying to.)
- Submit an application, or email or message anyone. It can pre-fill a form for you to
  check; you click Submit.
- Invent experience. Tailored CVs only reuse your own lines, and code checks that.
- Publish your job search. It runs from a private copy; the public repo holds code only.

## Get started

1. Make a **private** copy: clone this repo, rename the remote to `template`, and push to
   a new empty private repo (don't fork: a fork of a public repo can't be private).
   Exact commands: [Setup and publishing](docs/design/14-Setup-and-publishing.md).
2. Open **Claude Code** in that folder and say **"set this up for me"**.

Claude asks only for what it can't do itself: your CV and preferences, one GitHub login,
two clicks on the board, and optionally a mail secret.

## Read next

| If you want to… | Read |
|---|---|
| use it | the user guide: [docs/wiki](docs/wiki/Home.md) (also in this repo's Wiki tab) |
| understand how it works, file by file | the design docs: [docs/design](docs/design/README.md) |
| check what protects your data and accounts | [Security model](docs/design/13-Security-model.md) |

## Credits

Built on [ats-scrapers](https://github.com/kalil0321/ats-scrapers) (fetching company job
boards) and company→board mappings from ats-scrapers and
[job-board-aggregator](https://github.com/Feashliaa/job-board-aggregator).
