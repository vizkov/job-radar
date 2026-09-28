# Using it

Open Claude Code in your private copy of job-radar and talk normally. Claude
follows `CLAUDE.md` and picks the right procedure (a *skill* in `.claude/skills/`)
for what you ask. You don't need to know the skill names.

## Things you can say

| You say | Claude does |
|---|---|
| "What can this do?" / "man" | Prints the manual: every skill (what you can ask for) and every tool, generated from the code so it is never out of date. In Claude Code you can also type `/manual` |
| "Set this up for me" | Builds your profile from your CV and preferences, maps your target companies to job boards, creates the Project board, optionally sets up alert emails, switches on the daily run |
| "What's new?" / "How's my search going?" | Pulls the latest data, tells you the 3-5 roles most worth your time, what's unscored, what's waiting on a reply, anything broken |
| "Which of these fit me?" / "Is the Bridewell role worth it?" | Fetches each job description, compares it with your CV: fit score, requirements met/missing (with your evidence), blockers such as security clearance or right-to-work, and a recommendation. Puts Fit and Recommendation on the card |
| "Tailor my CV for the MDSec role" | Builds a CV and cover letter from **your own** bullet points, reordered and rephrased for that job; checks nothing was invented; gives you `resume.docx` (plain, ATS-safe), `resume.md` (paste into Claude Design for a styled version) and `cover_letter.md`, plus a list of what changed |
| "I applied to Starling" / "Got an interview with Fortinet" / "Rejected by X" | Moves the card to Applied / Interview / Rejected (final stages also close it) |
| "Stop showing DevSecOps roles" / "Add Checkmarx" / "Also look in Germany" | Changes your settings, shows you before/after numbers, saves when you agree |
| "Is anything broken?" | Checks the status, the workflow runs and each source; fixes or explains |
| "Help me apply to the Fortinet role" | Opens the application form in Chrome and fills it from your profile and tailored CV, page by page; you check each page and press Submit yourself |
| "How do I strengthen my CV?" / "Which certs matter?" | Looks across your fit scores for requirements you keep missing and suggests what to add or evidence better |
| "I have an interview with Starling" | Prepares likely questions mapped to your STAR stories, and gaps to prepare for |
| "What could be better?" (or when the brief says a weekly review is due) | Reviews sources, coverage, noise and freshness; proposes fixes and new job boards for you to approve |

## What Claude will not do

- Apply, submit or email anything for you. It prepares; you review and send.
- Add experience, skills, numbers or links you don't have. The checker rejects it.
- Fetch LinkedIn, Indeed or Glassdoor pages. It asks you to paste those job descriptions.
- Ask for passwords in chat. Secrets go in GitHub's settings page, which you fill in yourself.

## What happens without you

Three times a day (08:17, 14:17, 20:17 IST) the GitHub Action finds new roles and adds
them to the board as **New** cards (Tier 1 and 2 at companies on your list); fresh
listings rank higher because applying early matters. When you open Claude Code, a
session brief is ready: new roles, cards you moved, follow-ups due, anything broken. Scoring and tailoring
happen when you ask, because they use your Claude subscription rather than an
API key. Say "what's new?" when you sit down, or just look at the board.

## Costs

Nothing beyond your Claude Pro subscription. Claude's work counts toward your
normal Pro usage limits. The scheduled runs use free GitHub Actions minutes (about
15-25 minutes a day).

## Your data

- CV, stories and cover-letter blocks: `profile/career/`
- Tailored applications: `profile/applications/<date>-<company>-<role>/`
- Every role ever found: `data/matches.csv`; fit scores: `data/scores.jsonl`
- Fetched job descriptions (not committed): `work/jd/<Role ID>/`

All of it stays in your private repo. See [Security model](Security-model.md).
