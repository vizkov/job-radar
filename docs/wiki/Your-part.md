# 1. Your part

**This page:** what you need before you start, the setup steps in order (most are
Claude's; a few are yours), and how to pause, stop or take access back.

## Before you start

| You need | Why | Cost |
|---|---|---|
| A **GitHub account** | Your copy of job-radar and your board live there | free |
| A **Claude Pro or Max** plan, with **Claude Code** installed (the free Claude plan doesn't include Claude Code) | Claude operates everything. No separate API account or key | your plan |
| **git**, **Python 3.13** and GitHub's **`gh`** tool on your computer | Claude uses them to run job-radar for you. git saves your changes to GitHub; job-radar's own scripts are written in Python, and Claude runs them on your computer for scoring, board updates and PDFs (you never run them yourself); `gh` is how Claude talks to your GitHub account | free |
| *Optional:* **Chrome** with the **Claude in Chrome** extension | Only if you want Claude to pre-fill application forms | free |
| *Optional:* a **Gmail** account for job-alert emails | Only if you want LinkedIn/Indeed/Glassdoor jobs included | free |

**Installing them** (works on Windows, macOS and Linux; on Windows use PowerShell or Windows Terminal). After each
install, open a **new** terminal window and run the check command; it should print a version number, not an error:

| Tool | Get it from | Check it worked |
|---|---|---|
| Claude Code | Anthropic's Claude Code docs (search "Claude Code quickstart") | `claude --version` |
| git | **git-scm.com** | `git --version` |
| Python 3.13 | **python.org**. On Windows, tick **Add python.exe to PATH** on the installer's first screen, then **close and reopen the terminal**: a terminal that was open during the install does not see the new `python` | `python --version` |
| GitHub's `gh` tool | **cli.github.com**, then log in once: `gh auth login` and follow the prompts | `gh auth status` |

If `gh auth login` fails or the browser step never finishes: run `gh auth status` to see whether you are already logged in, then try `gh auth login --web` (if the browser doesn't open, open the page `gh` prints and type the one-time code it shows). A work laptop or proxy that blocks github.com sign-in is the usual cause: use a personal machine or ask your IT team.

Stuck on any of these? Once Claude Code runs, say "check my setup" and Claude tells you what's missing and walks you through it.

GitHub's free plan includes 2,000 minutes a month of automated runs for private
projects; job-radar uses roughly 450–750 a month (15–25 minutes a day across its scheduled runs).
If you ever pass the 2,000, GitHub stops the runs until the next month. It only charges you if you have raised your Actions spending limit above its default of $0, so with the default nothing is billed; the radar simply pauses.

## Setup, in order

Two steps start it; Claude does the rest and pauses when it needs you. The few clicks only you can make are collected in [one checklist](#your-manual-clicks-one-checklist) below.

1. **Make your private copy.** job-radar's public project holds only code. Your search
   must live in a **private** copy that only you can see. Make an empty folder (for example `job-radar-start` in Documents), open a terminal in it (on Windows: right-click inside the folder, then **Open in Terminal**), type `claude` and press Enter (the first time, Claude Code asks you to sign in with your Claude account: do that, then carry on). Then say: *"Make me a private copy of https://github.com/vizkov/job-radar called
   my-job-radar."* Claude creates the private repository on your GitHub account and
   copies the code into a new folder called `my-job-radar` (it tells you the exact path); there's nothing for you to type. (`vizkov/job-radar` is the author's public template: it holds only code, never anyone's data.) Claude Code asks your permission before it runs commands or writes files; read what it proposes, and approve the ones for creating your repository and copying the project. Don't use GitHub's "Fork"
   button: a fork of a public project can't be made private.
   **Which folder is "your copy"?** The `my-job-radar` folder Claude names. From now on you always open Claude Code there. The empty folder you started in was only a launch point: it stays empty, and you can keep it or delete it.
2. **Open Claude Code in your copy and say "set this up for me".** In the terminal, `cd` into the `my-job-radar` folder, run `claude` again, and say it. Claude does the work
   and pauses when it needs you:
   1. **Your CV and preferences.** Paste or attach your CV; say which countries, job
      titles and companies you want. Claude converts your CV into its own format and
      shows you the result to confirm nothing changed.
   2. **Let Claude manage your board.** Claude asks you to type
      `! gh auth refresh -s project` into Claude Code (the only command you type in the whole setup).
      The `!` at the start tells Claude Code to run it as a command; it opens your browser to a
      GitHub page asking you to approve the **project** permission, where you click **Authorize**. `gh` is GitHub's official command-line tool, already
      logged in as you (that's how Claude saves to your repository). This adds the
      **project** permission: reading and changing the GitHub Projects boards you have access
      to, including organisation boards you can edit. It gives no access to anything outside
      GitHub, and the login stays on your computer. To take it back later:
      GitHub → Settings → Applications → Authorized OAuth Apps → GitHub CLI → Revoke
      (this logs `gh` out entirely; log in again with `gh auth login` if you still need it).
   3. **Two questions with a default of no.** Claude asks whether to let it read LinkedIn job
      pages when scoring, and whether you want job-alert emails. Both are explained below
      ([LinkedIn consent](#linkedin-consent-the-four-opt-ins),
      [job-alert emails](#optional-job-alert-emails-linkedin-indeed-glassdoor)); say no to either and setup is still complete.
3. **Make the manual clicks** (checklist below). Claude tells you in chat when each one is due; the first, board auto-add, comes right after your board is created.

The first run records everything currently open and puts only the strongest matches
(**Tier 1**, the top automatic rating; see [Home](Home.md)) on your board, so you don't start with hundreds of cards. After that, only new
jobs appear.

### Your manual clicks: one checklist

GitHub gives Claude no way to do these three, so they are yours. Claude tells you the exact menu items when each is due.

- [ ] **Board auto-add (once, right after Claude creates your board).** Open the board → **⋯ →
  Workflows → Auto-add to project**, set the filter to `is:issue label:role`, and turn
  it on. This is what puts each new job on the board.
- [ ] **View sort order (once per view).** Claude prints the menu item to pick, for example
  "All Roles → Sort by → Fit, descending → Save view".
- [ ] **Stop the email flood (once).** On your repository page: **Watch → Participating and
  @mentions**. Otherwise GitHub emails you about every new job.

### Optional extras

Setup is complete without these; do any of them afterwards, in any order.

- **Job-alert emails** (LinkedIn, Indeed, Glassdoor jobs): [below](#optional-job-alert-emails-linkedin-indeed-glassdoor).
- **Reed** (more UK jobs): [below](#optional-reed-uk-job-board).
- **Form filling.** Install the Claude in Chrome extension. It works in your **real Chrome**, where
  you're already logged in to sites, and asks Chrome for broad permissions when you install it.
  How Claude limits what it does with it: [What Claude can do in your browser](#what-claude-can-do-in-your-browser).
- **LinkedIn uses** (job pages, contact lookup, hiring posts, date lookup): off until you say yes; see
  [LinkedIn consent](#linkedin-consent-the-four-opt-ins).

## Optional: job-alert emails (LinkedIn, Indeed, Glassdoor)

job-radar never logs in to or scrapes those sites. Instead you set up job alerts there,
and job-radar reads the alert emails.

**Recommendation: use a new Gmail account that receives only your job alerts.** A Gmail app
password (the key you give GitHub, below) opens the whole account: the job-radar code only reads, but a
leaked password could do more, such as read password-reset emails for your other accounts. On a
dedicated mailbox, the worst case is that someone reads job alerts.

1. Create the alerts on each site (Claude suggests the searches).
2. Create the dedicated Gmail account and, in your main Gmail, add a filter that forwards the
   alert emails to it.
3. Turn on 2-Step Verification for the dedicated account (Google requires it), then create an
   **app password** (a one-off password for one app, here job-radar's read-only mailbox access over IMAP, the standard way programs read mail): Google Account → Security → App passwords. It's a separate password
   just for this, and you can revoke it any time without changing your real one.
4. Add two **secrets** to your repository: **Settings → Secrets and variables → Actions →
   New repository secret**: `JOBALERT_IMAP_USER` (the address) and
   `JOBALERT_IMAP_PASSWORD` (the app password). Secrets are stored encrypted by GitHub
   and are never shown again, not even to Claude. **Never paste the password into Claude or a file.**

**What GitHub's servers can reach, for each choice:**

| The secret points to | What GitHub's servers can reach | Alert emails | Reply tracking |
|---|---|---|---|
| **A dedicated alert-only mailbox (recommended)** | A mailbox holding only forwarded alerts. The code opens it read-only and never marks, moves or deletes mail | Yes, six times a day | No. The daily scan looks for replies in that mailbox, and employers write to your normal address, so it finds nothing. You still get reply checks in a session through the Gmail connector (below) |
| **Your normal inbox** | Your whole mailbox. The code still only reads: it checks the sender, subject and date of recent mail, and reads the start of the text only for mail that looks like it comes from a recruiting system or names a company you applied to. It keeps sender, subject, date and type in your private repository, never the email text | Yes | Yes, six times a day: receipts, rejections, interview invitations, assessments. If you choose this, create the app password on your main account, skip the forwarding filter, and revoke the password the day you stop using job-radar |
| **No mailbox** | Nothing | No (you lose only roles that appear solely on LinkedIn, Indeed or Glassdoor) | Session checks only |

**The Gmail connector is a separate access.** When you ask "did anyone reply?", Claude reads *your* Gmail in the session through the
Gmail connector in Claude (you approve it once; read-only: it searches and reads, and never sends, labels or deletes). It can read a whole
conversation, nothing about it goes through GitHub, and it works with any of the three choices above. It only runs while you have a session open.

What the dedicated-mailbox option does: six times a day GitHub's servers log in to that mailbox and fetch the emails from
LinkedIn, Indeed and Glassdoor (emails that fail the sender's security signature are ignored). Sign-in codes, password resets
and newsletters are skipped. Claude tells you what it found at the start of a session.

## Optional: Reed (UK job board)

1. Register for a free API key at **reed.co.uk/developers** (your own Reed account).
2. Add it as a repository secret named `REED_API_KEY` (Settings → Secrets and variables → Actions),
   the same way as the mail secrets. Never paste it into Claude.
3. Tell Claude it's added; it switches the Reed source on. The key only allows searching jobs.

## LinkedIn consent: the four opt-ins

This is the one place that lists every way Claude touches LinkedIn. Everything else on LinkedIn, Indeed and Glassdoor stays
untouched: job-radar never scrapes those sites, never opens Indeed or Glassdoor pages (you paste those descriptions), and
never opens LinkedIn job-search pages beyond the date lookup in the last row, if you switch it on.

**The risk, stated once:** LinkedIn's terms ban any automated use of the site, even read-only and at low volume, so each use below could
get your LinkedIn account restricted. That is your risk to accept. All reading happens in your own logged-in Chrome, never from the
automatic GitHub runs. Claude never reacts, comments, reposts, connects, messages or follows, and stops at any login wall or CAPTCHA.

| Use | What Claude reads | Default | Turn it on or off |
|---|---|---|---|
| **Job-description pages** | One LinkedIn job page at a time, for a role already on your list that it is scoring, and saves only the description text. No searching or browsing | Off in a fresh copy; setup asks you | Say "switch on / off the LinkedIn job-page reading", or set `scoring.linkedin_job_pages` to `true` / `false` in `profile/config.json`. Off means Claude asks you to paste the description |
| **Referral lookup** | LinkedIn people-search results for one company, for one role you are about to apply to, only when you ask, to find a likely hiring manager and a recruiter | Off | Say "switch on / off the LinkedIn lookup", or `referrals.linkedin_lookup` |
| **Hiring-post discovery** | LinkedIn post-search results and known recruiters' own posts, at the start of a session or when you ask, capped (a set number of searches, scrolls and people per session), to find roles announced in posts | Off | Say "switch on / off the LinkedIn post search", or `discovery.linkedin_posts.enabled` |
| **Date lookup** (narrow) | When a role found on a company's own careers site shows no posted date and the age filter needs one: one LinkedIn job search for that exact company and title, reading only the matching listing's posted date and location. At most 3 a session; never a sweep | Off in a fresh copy; setup asks you | Say "switch on / off the LinkedIn date lookup", or `scoring.linkedin_date_lookup`. Off means Claude leaves such roles undated and says so |

With the lookup off, Claude gives you LinkedIn search links to open yourself.

## What Claude can do in your browser

Only when you ask it to help with an application, or for a LinkedIn use you've switched on. Claude
works in tabs it opens itself for the task, on the employer's own application site. The extension could see
your other logged-in tabs; Claude doesn't use them. You approve the answers for every
page before they're typed. It never answers questions about visas, salary, diversity or
consent for you, never logs in or creates accounts for you (you do that in the tab), and
never clicks the final Submit. It won't touch LinkedIn, Indeed or Glassdoor applications at all (the
only LinkedIn uses are in [LinkedIn consent](#linkedin-consent-the-four-opt-ins)).

## Every so often

| When | You do |
|---|---|
| Claude has a tailored CV or cover letter ready | Read it: Claude only reuses your own lines, but you're the one sending it |
| Claude has filled an application form | Check each page; **you** click Submit |
| An Indeed/Glassdoor job needs scoring | Paste the job description (Claude never opens those sites). LinkedIn job descriptions it reads itself in your Chrome if you switched that on ([LinkedIn consent](#linkedin-consent-the-four-opt-ins)) |
| Claude proposes a settings change, new job boards or a fix | Say yes or no; these wait for your answer. The routine things Claude does by itself (filling card columns, moving Skip-scored and closed roles to Skipped, the weekly title-rating adjustment) are described in [Using it](Using-it.md) and [Board](Board.md) |
| Claude asks who can help at a company you'd apply to | Tell it the names. Message people you know yourself (Claude gives you the role links); for recruiters or hiring managers it drafts the note in the chat (never saved to a file) after a fresh reviewer has read it as the recruiter would. **You** send everything, then tell it what happened |
| You get a new job, certification or achievement | Tell Claude; it adds it to your CV lines so future applications can use it |

## Questions people ask

- **My laptop is off. Does it still work?** The daily search runs on GitHub's servers six times a day whether or not
  your computer is on, and new roles wait for you. What needs you: Claude scoring roles, filling in the board's
  details and checking your inbox happen when you open a Claude Code session.
- **Where is my board?** Ask Claude "give me the link to my board". It's on your GitHub account under Projects.
- **Does an employer see that I looked at their job?** Not in any way tied to you. The search reads public job lists
  and pages, so a company's website may log the page request like any other visitor, with no name attached. An
  employer learns about you only from an application you submit yourself.
- **What does the Claude in Chrome extension see?** It works in your real Chrome with your logins, so give it access only
  to the sites you want (Chrome's extension settings let you limit it to specific sites), and keep banking and
  email tabs out of the session. job-radar only asks it to open job pages and application forms.
- **Does it change my settings without asking?** Almost never. The exception: about once a week it nudges the
  scoring weight of a job-title keyword by one small step when your own scores justify it, and tells you with a
  one-line undo. Everything else (what to search, which countries, your CV) changes only after you say yes.
- **I'm not relocating / don't need a visa.** Tell Claude during setup: the sponsorship checks are written for someone relocating, so ask
  Claude to turn them off or adapt them for you.
- **Is my CV going to the public project?** No. Your CV and everything personal live only in your private copy.
  Code improvements are published to the public project by a script that refuses to send private files.
- **New computer or backup?** Your private repository on GitHub is the backup. On a new machine install the four tools,
  run `gh auth login`, then tell Claude: "clone my-job-radar and get me going".
- **Who holds my CV and career notes?** Your private GitHub repository (GitHub is owned by Microsoft) holds your career documents, scores and match list; only you can see it. Claude reads them in your session.
- **Where do the costs come from?** The only money is your paid Claude plan. GitHub's free minutes cover the daily runs.
  How much of a session scoring and tailoring use is in [Using it](Using-it.md) under Costs.

## Pausing, stopping, taking access back

| To | Do |
|---|---|
| Pause the search | Tell Claude "pause the radar" (it switches off the scheduled runs), or on GitHub: Actions → job-radar → ⋯ → Disable workflow |
| Revoke board access | GitHub → Settings → Applications → Authorized OAuth Apps → GitHub CLI → Revoke |
| Revoke mailbox access | Delete the app password in your Google Account, and the two secrets in the repo settings |
| Delete everything | Delete your private repository, its board and the folder on your computer. Also remove what sits outside those, if you set it up: the two scheduled tasks on your PC, `job-radar-workday` and `job-radar-trigger` (ask Claude to remove them before you delete the folder), the app password and any mail forwarding filter in your Google Account, the Gmail connector in Claude and the Chrome extension, and the GitHub CLI's authorisation. Two more things are kept elsewhere: Claude Code keeps its own conversation history on your computer, and what you paste into a Claude conversation (your CV, job descriptions) is processed by Anthropic under your account's data settings, so check those if that matters to you |

**Next:** [2. Using it](Using-it.md)
