# 1. Your part

**This page:** what you need before you start, the setup steps in order (most are
Claude's; a few are yours), and how to pause, stop or take access back.

## Before you start

| You need | Why | Cost |
|---|---|---|
| A **GitHub account** | Your copy of job-radar and your board live there | free |
| A **Claude Pro or Max** plan, with **Claude Code** installed | Claude operates everything. No separate API account or key | your plan |
| **git**, **Python 3.13** and GitHub's **`gh`** tool on your computer | Claude uses them to run job-radar for you | free |
| *Optional:* **Chrome** with the **Claude in Chrome** extension | Only if you want Claude to pre-fill application forms | free |
| *Optional:* a **Gmail** account for job-alert emails | Only if you want LinkedIn/Indeed/Glassdoor jobs included | free |

**Installing them** (works on Windows, macOS and Linux; on Windows use PowerShell or Windows Terminal). After each
install, open a **new** terminal window and run the check command; it should print a version number, not an error:

| Tool | Get it from | Check it worked |
|---|---|---|
| Claude Code | Anthropic's Claude Code docs (search "Claude Code quickstart") | `claude --version` |
| git | **git-scm.com** | `git --version` |
| Python 3.13 (job-radar's code and the daily run use it) | **python.org** (on Windows tick "Add python.exe to PATH") | `python --version` |
| GitHub's `gh` tool | **cli.github.com**, then log in once: `gh auth login` and follow the prompts | `gh auth status` |

Stuck on any of these? Once Claude Code runs, say "check my setup" and Claude tells you what's missing and walks you through it.

GitHub's free plan includes 2,000 minutes a month of automated runs for private
projects; job-radar uses roughly 450–750.

## Setup, in order

1. **Make your private copy.** job-radar's public project holds only code. Your search
   must live in a **private** copy that only you can see. Open Claude Code in an empty
   folder and say: *"Make me a private copy of https://github.com/vizkov/job-radar called
   my-job-radar."* Claude creates the private repository on your GitHub account and
   copies the code into it; there's nothing for you to type. Don't use GitHub's "Fork"
   button: a fork of a public project can't be made private.
2. **Open Claude Code in your copy and say "set this up for me".** Claude does the work
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
   3. **One board setting.** After Claude creates your board, open it → **⋯ →
      Workflows → Auto-add to project**, set the filter to `is:issue label:role`, and turn
      it on. This is what puts each new job on the board; GitHub offers no way for Claude
      to switch it on.
   4. **A couple of clicks on the views.** GitHub doesn't let Claude set a view's sort
      order, so Claude tells you exactly which menu item to pick (for example "Act now →
      Sort by → Posted, descending → Save view").
   5. **Stop the email flood.** On your repository page: **Watch → Participating and
      @mentions**. Otherwise GitHub emails you about every new job.
**Optional extras (steps 3 to 6).** Setup is complete without them; do any of them afterwards, in any order.

3. **Job-alert emails** (LinkedIn, Indeed, Glassdoor jobs). See below.
4. **Reed** (more UK jobs). See below.
5. **Form filling.** Install the Claude in Chrome extension. It works in your **real Chrome**, where
   you're already logged in to sites, and asks Chrome for broad permissions when you install it.
   How Claude limits what it does with it is below.
6. **LinkedIn contact lookup** (for referrals). Off unless you switch it on. See below.

The first run records everything currently open and puts only the strongest matches
(Tier 1) on your board, so you don't start with hundreds of cards. After that, only new
jobs appear.

## Optional: job-alert emails (LinkedIn, Indeed, Glassdoor)

job-radar never logs in to or scrapes those sites. Instead you set up job alerts there,
and job-radar reads the alert emails.

1. Create the alerts on each site (Claude suggests the searches).
2. Choose the mailbox. **Recommended: a new Gmail account used only for alerts**, with a
   filter in your main Gmail forwarding alerts to it. You *can* use your main Gmail, but
   then the password below unlocks your whole inbox if it ever leaked.
3. Turn on 2-Step Verification for that account (Google requires it), then create an
   **app password**: Google Account → Security → App passwords. It's a separate password
   just for this, and you can revoke it any time without changing your real one.
4. Add two **secrets** to your repository: **Settings → Secrets and variables → Actions →
   New repository secret**: `JOBALERT_IMAP_USER` (the address) and
   `JOBALERT_IMAP_PASSWORD` (the app password). Secrets are stored encrypted by GitHub
   and are never shown again, not even to Claude.

What happens with it: three times a day GitHub's servers log in to that mailbox
**read-only**, fetch only emails from LinkedIn, Indeed and Glassdoor, and never mark
anything read, move or delete it. Emails that fail the sender's security signature are
ignored. **Never paste the password into Claude or a file.**

**Two separate Gmail accesses, don't mix them up.** (1) The alert mailbox above is read by GitHub's servers every
run, over IMAP with its own app password, and only for alert emails. (2) Separately, when you ask "did anyone reply?",
Claude reads *your* Gmail in the session through the Gmail connector in Claude (you approve it once; read-only). Use
your normal inbox for (2): that is where employers answer.

## Optional: Reed (UK job board)

1. Register for a free API key at **reed.co.uk/developers** (your own Reed account).
2. Add it as a repository secret named `REED_API_KEY` (Settings → Secrets and variables → Actions),
   the same way as the mail secrets. Never paste it into Claude.
3. Tell Claude it's added; it switches the Reed source on. The key only allows searching jobs.

## Optional: LinkedIn contact lookup

When you're about to apply to a role and know nobody there, Claude can find the likely hiring manager and a
recruiter. By default it gives you LinkedIn search links to open yourself. If you'd rather it looked for you,
say **"switch on the LinkedIn lookup"**: it then reads LinkedIn's search results in your logged-in Chrome,
for one role at a time and only when you ask, and never connects, messages or follows anyone.
**The risk:** LinkedIn's terms ban any automated use of the site, so this could get your LinkedIn account
restricted, even at this low volume. Say "switch off the LinkedIn lookup" to stop it.

**Separate and always on:** when Claude scores a role that comes from LinkedIn, it reads that one job page in your
logged-in Chrome to get the description (one page at a time, read-only, no searching or browsing). Same risk. Say
"don't open LinkedIn pages, I'll paste them" and it goes back to asking you to paste the description.

## What Claude can do in your browser

Only when you ask it to help with an application, or for the LinkedIn lookup if you've switched it on. Claude
works in tabs it opens itself for the task, on the employer's own application site. The extension could see
your other logged-in tabs; Claude doesn't use them. You approve the answers for every
page before they're typed. It never answers questions about visas, salary, diversity or
consent for you, never logs in or creates accounts for you (you do that in the tab), and
never clicks the final Submit. It won't touch LinkedIn, Indeed or Glassdoor applications at all (the
only LinkedIn uses are the opt-in contact lookup for referrals and the opt-in hiring-post search). The
hiring-post search (`discovery.linkedin_posts.enabled`) reads LinkedIn posts in your Chrome at the start of a
session, read-only and capped. It breaches LinkedIn's terms like the contact lookup does, so it is off until you say yes.

## Every so often

| When | You do |
|---|---|
| Claude has a tailored CV or cover letter ready | Read it: Claude only reuses your own lines, but you're the one sending it |
| Claude has filled an application form | Check each page; **you** click Submit |
| An Indeed/Glassdoor job needs scoring | Paste the job description (Claude never opens those sites). LinkedIn job descriptions it reads itself in your Chrome, one page at a time |
| Claude proposes a settings change, new job boards or a fix | Say yes or no. Nothing changes without your yes |
| Claude asks who can help at a company you'd apply to | Tell it the names. Message people you know yourself (Claude gives you the role links); for recruiters or hiring managers it drafts the note in the chat (never saved to a file) after a fresh reviewer has read it as the recruiter would. **You** send everything, then tell it what happened |
| You get a new job, certification or achievement | Tell Claude; it adds it to your CV lines so future applications can use it |

## Questions people ask

- **My laptop is off. Does it still work?** The daily search runs on GitHub's servers three times a day whether or not
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
- **Where do the costs come from?** The only money is your Claude plan. GitHub's free minutes cover the daily runs.
  How much of a session scoring and tailoring use is in [Using it](Using-it.md) under Costs.

## Pausing, stopping, taking access back

| To | Do |
|---|---|
| Pause the search | Tell Claude "pause the radar" (it switches off the scheduled runs), or on GitHub: Actions → job-radar → ⋯ → Disable workflow |
| Revoke board access | GitHub → Settings → Applications → Authorized OAuth Apps → GitHub CLI → Revoke |
| Revoke mailbox access | Delete the app password in your Google Account, and the two secrets in the repo settings |
| Delete everything | Delete your private repository, its board and the folder on your computer. job-radar stores nothing anywhere else (Claude Code keeps its own conversation history on your computer) |

**Next:** [2. Using it](Using-it.md)
