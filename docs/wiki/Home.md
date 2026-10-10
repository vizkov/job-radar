# job-radar

**This page:** what job-radar is, the words you'll see, and what to read next.

job-radar is a job-search assistant. Out of the box it's set up for AppSec, product
security, pentest and security-consulting roles in Europe; the job titles, countries and
companies are your settings, and Claude changes them for you. Three times a day it checks
the job boards of the companies you want to work for, plus public job services (EURES for the EU, the German
and Swedish employment agencies, and optionally Reed for the UK) and, optionally, your job-alert emails.
LinkedIn, Indeed and Glassdoor jobs come in only through those alert emails; job-radar never scrapes those sites (it only reads the description of a single LinkedIn role it is scoring, in your own Chrome). It puts every new matching role on a board for you. You
use it through **two things only**:

1. **Claude.** You talk to it in Claude Code, in your private copy of this project. It
   acts as your recruitment consultant and does all the operating for you: setup,
   briefings, judging how well a role fits you, tailored CVs and cover letters,
   tracking, tuning the search, fixing what breaks.
2. **Your board.** A GitHub Project where every new role is a card. You (or Claude) move
   each card along: New → Shortlisted → Applied → Interview → Offer.

You don't write code or edit settings files. At most, you type one command Claude gives you
and click a few settings on GitHub; [Your part](Your-part.md) lists every one.

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
| **Tier** | A quick automatic rating, worked out by fixed rules (no AI judges each job) from the job title, seniority, country, company, visa sponsorship and how fresh the ad is. **Tier 1** = strongest match to what you're looking for; **Tier 2** = worth a look. It's a first guess made before anyone reads the ad: once Claude scores a role against your CV, a recommended **Apply** becomes Tier 1 and a **Skip** becomes Tier 2 (a **Maybe** keeps its first guess). There's no Tier 3: roles that don't match your titles and countries at all never reach the board. |
| **Fit** | Claude's 0–100 judgement of how well your CV matches the job description, set when you ask it to score roles. |
| **Recommendation** | Claude's call after scoring: Apply, Maybe or Skip. |
| **Sponsor** | Will the employer sponsor your work visa for this job? It starts as a register check (**Licensed** = on the UK/Dutch list of employers allowed to sponsor, which means *can*, not *will*). When Claude researches a role it becomes **Confirmed**, **Likely**, **Unlikely** or **No**, with the evidence on the card. **Unclear** means the register check couldn't tie the employer to a licence, or the country has no public register (Ireland, Germany, Sweden, Switzerland). |
| **Referral** | Whether someone has referred you for the job: Finding contact, Asked, Referred, No route, or Not needed. You ask the people you know; Claude drafts only notes to recruiters or hiring managers, and keeps track. |
| **Posted** | When the employer posted the job. Some sources don't say; then it's the day job-radar first found it, which is usually within hours. Newer is better: early applications do better. |
| **Role ID** | A 16-character code on each card. Mention it (or just the company and role) and Claude finds everything about that job. |
| **Target companies** | The list of employers you want. Roles at other employers are left off your board, wherever they were found, unless you ask otherwise. |
| **Repository (repo)** | Your project's folder on GitHub. Yours is **private**: only you (and anyone you invite) can see it, its issues and its board. |
| **Issue** / **label** | GitHub's name for a discussion item, and a coloured tag on it. Each card on your board is an issue; labels like `role` or `possibly-closed` are how the automatic runs pass information to it. |
| **GitHub Actions** | GitHub's service that runs job-radar's automatic search on its servers, on a schedule, without your computer being on. |
| **Secret** | A password stored encrypted in your repo's settings, readable only by the automatic runs. |
| **Session** | One conversation with Claude in Claude Code. Each one starts with a short briefing. Separately, Claude plans limit how much you can use Claude in each few-hour window; costs below are given as a share of that allowance, and typing `/usage` in Claude Code shows how much is left. |
| **STAR story** | A short account of something you did: Situation, Task, Action, Result. Used for cover letters and interview answers. |
| **ATS** (applicant tracking system) | The software employers use to post jobs and receive applications (Greenhouse, Workday…). "ATS-safe" CVs are plain enough for it to read. |
| **The checker** | Code that inspects everything Claude writes for you (scores, tailored CVs) and rejects anything invented. |

## The picture

```
 3x a day on GitHub's servers (02:47, 08:47, 14:47 UTC), no one involved
   (new cards appear on their own; some columns, such as Tier and Fit, fill in at your next session)
   → check your target companies' job boards, public job portals, your job-alert emails
   → keep matching roles → rate them → one card per new role on your board
                                                        ▲            ◀── you look, drag cards
 You ──talk──▶ CLAUDE (your Claude subscription) ───────┘ fills in Fit, Stage, …
               briefs you, scores fit, tailors CVs, fills forms for you to submit,
               tunes the search, fixes what breaks
```

**Next:** [1. Your part](Your-part.md)
