# Your part

Claude does everything it can. These steps it can't, because they need your login,
your judgement, or a page GitHub gives no command for. Claude tells you when each is
due and what to click.

## Once, at setup

| Step | Why only you |
|---|---|
| Give Claude your CV, target countries, role titles and companies | It's your career; Claude converts it and shows you the result to confirm |
| Type `! gh auth refresh -s project` in Claude Code and finish the browser login | Lets Claude update your board; it's your GitHub login |
| Project → **⋯ → Workflows → Auto-add to project**: filter `is:issue label:role`, turn on | GitHub has no command for this setting |
| Optional: Project → Workflows → **Item closed** → set Stage | Same |
| Repo → **Watch → Participating and @mentions** | Stops an email per new role card |

## Optional: job-alert emails (LinkedIn, Indeed, Glassdoor)

1. Create the alerts on each site (Claude suggests the searches).
2. Create a Gmail **app password** (Google Account → Security → App passwords);
   a separate mailbox just for alerts is safer, your main one works.
3. Add two secrets in the repo: **Settings → Secrets and variables → Actions**:
   `JOBALERT_IMAP_USER` and `JOBALERT_IMAP_PASSWORD`.

Never paste the password into chat or a file. Details and trade-offs:
[Job-alert emails](../design/Job-alert-emails.md).

## Every so often

| When | You do |
|---|---|
| Claude has a tailored CV or cover letter ready | Read it: Claude only reuses your own lines, but you're the one sending it |
| Claude has filled an application form (`apply-assist`) | Check each page; **you** click Submit |
| A LinkedIn/Indeed/Glassdoor role needs scoring | Paste the job description (Claude never opens those sites) |
| You want a board view changed (columns, sort) | Change it in the Project and **Save view**: GitHub has no API for view layout. Claude then publishes the design |
| Claude proposes config changes, new job boards or fixes | Say yes or no |
