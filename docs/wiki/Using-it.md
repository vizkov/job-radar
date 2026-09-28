# 2. Using it

**This page:** what to say to Claude, what happens without you, what it costs, and where
your data lives.

Open Claude Code in your private copy of job-radar and talk normally. Claude works out
what you want and follows the right procedure. You don't need to know any commands.
Not sure what's possible? Ask **"what can this do?"** or type `/manual`.

## Things you can say

### Getting going

| You say | Claude does |
|---|---|
| "Set this up for me" | Builds your profile from your CV and preferences, finds your target companies' job boards, creates your board, optionally sets up job-alert emails, and switches on the scheduled runs |
| "What can this do?" / `/manual` | Lists everything you can ask for, generated from the system itself so it's never out of date |

### Every day

| You say | Claude does |
|---|---|
| "What's new?" / "How's my search going?" | Tells you the few roles most worth your time (freshest first), what's not yet scored, what's waiting on a reply, anything broken |
| "Which of these fit me?" / "Is the Bridewell role worth it?" | Reads each job description and compares it with your CV: a Fit score, which requirements you meet (and the CV line that proves it), blockers such as security clearance or right to work, and Apply / Maybe / Skip. Puts Fit and Recommendation on the card |

### Applying

| You say | Claude does |
|---|---|
| "Tailor my CV for the MDSec role" | Builds a CV and cover letter from **your own** CV lines, picked and reordered for that job; a checker makes sure nothing was invented. You get a plain Word CV that applicant tracking systems read reliably, a Markdown copy (for a styled version), a cover letter, and a list of what changed |
| "Help me apply to the Fortinet role" | Opens the application form in your Chrome and fills it in from your CV and profile, page by page. You approve every page's answers, and **you** press Submit. Questions about visas, salary or diversity are always asked, never guessed |
| "I have an interview with Starling" | Likely questions, answers drawn from your STAR stories, gaps to prepare for |

### Tracking

| You say | Claude does |
|---|---|
| "I applied to Starling" / "Got an interview with Fortinet" / "Rejected by X" / "Not interested in Y" | Moves the card (final stages also close it). Dragging the card yourself works too: Claude notices at the next session |

### Improving the search and your CV

| You say | Claude does |
|---|---|
| "Stop showing DevSecOps roles" / "Add Checkmarx" / "Also look in Germany" | Changes your settings, shows you before/after numbers, saves when you agree |
| "How do I strengthen my CV?" / "Which certs matter?" | Looks across your scored roles for requirements you keep missing and suggests what to add or evidence better |
| "What could be better?" | Reviews the system and proposes fixes and new job boards for you to approve (Claude also offers this weekly) |
| "Is anything broken?" | Checks the runs and every source; fixes or explains |

## What Claude will not do

- Submit an application, or email or message anyone for you. It prepares; you send.
- Add experience, skills, numbers or links you don't have. The checker rejects it.
- Open LinkedIn, Indeed or Glassdoor pages. It asks you to paste those job descriptions.
- Ask for passwords in chat. Secrets go in GitHub's settings page, which you fill in yourself.

## What happens without you

Three times a day (02:47, 08:47 and 14:47 UTC, which is 08:17, 14:17 and 20:17 in India)
job-radar checks for new roles and adds them
to your board as **New** cards: Tier 1 and 2, at companies on your list. When you next
open Claude Code, a briefing is ready: new roles, cards you moved, follow-ups due,
anything broken. Scoring and tailoring happen when you ask. Say "what's new?" when you
sit down, or just look at the board.

## Costs

Nothing beyond your Claude subscription (Claude Pro or Max; there's no separate API bill).
Claude's work counts toward your plan's normal usage limits: briefings and tracking are
light, scoring or tailoring many roles in one go is heavier, so score the freshest ones
first. The automatic runs use about 15–25 minutes a day of GitHub Actions, within the free
plan's 2,000 minutes a month for private repos.

## Your data

| What | Where |
|---|---|
| Your CV, stories and cover-letter paragraphs | `profile/career/` |
| Tailored applications | `profile/applications/<date>-<company>-<role>/` |
| Every role ever found | `data/matches.csv` |
| Fit scores | `data/scores.jsonl` |
| Job descriptions Claude fetched (not saved to GitHub) | `work/jd/<Role ID>/` |

All of it stays in your **private** repo, which only you (and anyone you invite) can see.
The automatic runs save their results there; Claude saves your changes there only after
you agree. None of it is ever published: the public job-radar project receives code
improvements only. How that's enforced: [Security model](../design/13-Security-model.md).

## Who contacts whom

- job-radar **never contacts employers** and never applies anywhere.
- The automatic runs read public job boards from GitHub's servers.
- When Claude fetches a full job description, or checks a company's jobs page, that
  request comes from your computer, like opening the page in a browser.

**Next:** [3. Board](Board.md)
