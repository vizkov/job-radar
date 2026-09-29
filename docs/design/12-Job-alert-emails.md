# 12. Job-alert emails

**What this is:** How LinkedIn, Indeed and Glassdoor jobs get in without scraping those sites: their alert emails are read over IMAP, with the mailbox password isolated in one workflow step and every email checked for spoofing.  
**Read first:** [3.1, the workflow file](03-Scheduled-run.md#31-the-workflow-file-radaryml)  
**Code:** `tools/fetch_alert_emails.py`, `jobradar/alert_providers.py`, `jobradar/sources/alert_email.py`, `radar.yml` step 3

job-radar never logs in to LinkedIn, Indeed or Glassdoor and never scrapes them.
Their terms prohibit scraping, and GitHub Actions IPs get blocked quickly.
Instead, each site emails the user job alerts, and job-radar reads those emails.

```
LinkedIn / Indeed / Glassdoor ──alert email──▶ your main Gmail
          ──filter: auto-forward──▶ dedicated mailbox
          ──IMAP, read-only──▶ tools/fetch_alert_emails.py ──.eml files──▶ radar.py (alert_email source)
```

## Where the password goes (and doesn't)

The mailbox password exists in exactly one place: the **"Fetch job-alert emails"**
step of `radar.yml`. That step:

- runs **before** `pip install`, so no third-party package is on the machine yet;
- runs `python -I -S`, so Python loads no site-packages and no startup hooks;
- runs `tools/fetch_alert_emails.py`, which imports only the standard library
  (a test proves this) and saves the emails as files in `.alert_mail/` (never committed).

`radar.py` then parses those files **without** the secret. A compromised
dependency of the scrapers therefore never shares a process with the user's password.
The mailbox is opened read-only (IMAP `EXAMINE`, `BODY.PEEK[]`): nothing is
marked read or deleted.

The fetch step always runs. If the source is enabled before the secrets exist, the Radar
status card's Sources table shows
`FAILED: RuntimeError: JOBALERT_IMAP_USER / JOBALERT_IMAP_PASSWORD not set`. The other
sources are unaffected.

## Where it looks, and what it reports

The fetcher reads Gmail's **All Mail** folder (found by its `\All` flag, so localised names such as
"[Google Mail]/All Mail" work), falling back to the Inbox, so a filter or category that skips the
Inbox can't hide alerts. Every run it also counts, per provider, **all** emails from that provider's
domain and lists sender **addresses** (never contents) that aren't known alert senders. The log line
and `_status.json` show it; `AlertEmailSource` turns it into status-card warnings:

- *no emails at all from linkedin, indeed… : alerts not set up, paused, or going to a different mailbox*
- *N linkedin emails, none from a known alert sender (seen: …): the alert sender may have changed*

## Why not python-jobspy?

The original plan included an opt-in `python-jobspy` scraper for
LinkedIn/Indeed/Glassdoor. It was dropped (2026-09-28) because:

- It can't install alongside this project: it pins `numpy==1.26.3` (no Python
  3.13 wheels) and `pandas<3`.
- Its last release was July 2025, and these scrapers break whenever the sites change.
- It depends on `tls-client`, a prebuilt native library that fakes browser TLS
  fingerprints to get past bot detection.
- Scraping these sites breaks their terms and risks the user's account.

The providers' own alert emails cover the same postings without any of that.

## Why a dedicated mailbox

A Gmail app password gives full IMAP and SMTP access to its account. If the
GitHub secret ever leaked, an app password for the user's main account would expose
all the user's mail, including password-reset emails for everything else. An app
password for a mailbox that only receives job alerts exposes job alerts.

### Using the user's main Gmail instead

It works: the fetcher only searches for the providers' sender addresses, opens the
mailbox read-only, and drops any email without a valid provider DKIM signature. The
cost is the leak scenario above: that one GitHub secret would then unlock the user's whole
mailbox. If the user chooses this, skip steps 2 and 4 below, create the app password on the user's
main account, and set `JOBALERT_IMAP_USER` to the user's main address. Revoke the app password
(Google Account → Security → App passwords) the day they stop using job-radar.

## Setup (~30 minutes; Claude walks the user through it)

The user-facing version is in [Your part](../wiki/Your-part.md). The details:

1. **Create alerts.**
   - LinkedIn: Jobs → search (e.g. "application security", location "United
     Kingdom") → *Set alert*, daily. For a target company, filter the search by
     company first.
   - Indeed: search on the user's country's Indeed (uk.indeed.com, nl.indeed.com, …)
     → *Get new jobs for this search by email*.
   - Glassdoor: search → *Create job alert*.
2. **Create the dedicated Gmail account** (e.g. `yourname.jobalerts@gmail.com`).
   Turn on 2-Step Verification (needed for app passwords).
3. **Create an app password** for it: Google Account → Security → App passwords.
4. **Forward alerts from the user's main Gmail.** Settings → Forwarding → add the
   dedicated address and confirm. Then create a filter:
   `from:(jobalerts-noreply@linkedin.com OR jobs-listings@linkedin.com OR indeed.com OR glassdoor.com)`
   → *Forward to* the dedicated address.
5. **Add GitHub secrets** (repo → Settings → Secrets and variables → Actions):
   `JOBALERT_IMAP_USER` = the dedicated address, `JOBALERT_IMAP_PASSWORD` = the
   app password.
6. **Turn it on:** set `alert_email: enabled: true` in `profile/sources.yaml` (the
   sample in `examples/` ships with it off). The workflow already
   passes both secrets to the fetch step only.
   To use fewer providers, trim `--providers` in that step and `providers` in
   `sources.yaml`.

## Test it locally

```bash
# against the real mailbox (same two steps as the workflow)
export JOBALERT_IMAP_USER=... JOBALERT_IMAP_PASSWORD=...
python -I -S tools/fetch_alert_emails.py --out .alert_mail
unset JOBALERT_IMAP_USER JOBALERT_IMAP_PASSWORD
python radar.py --dry-run --source alert_email --include-outside

# or with exported .eml files (Gmail: open message → ⋮ → Download message):
#   put them in a folder and set  eml_dir: <folder>  under alert_email in sources.yaml
```

## How it defends against spoofed email

Anyone can send email to the user's dedicated address pretending to be LinkedIn.

- Only mail **from** a known provider's alert sender is read.
- By default (`require_dkim: true`) the message must carry a passing DKIM result
  for **that provider's** domain in Gmail's `Authentication-Results` header. A
  mail claiming to be from Indeed but signed by some other domain is rejected.
  DKIM signatures survive Gmail auto-forwarding because the body isn't modified.
- Job links are **rebuilt from the job ID**, even when it's buried in a tracking
  redirect:

  | Provider | ID in the email | Link on the card |
  |---|---|---|
  | LinkedIn | `/jobs/view/<digits>` | `https://www.linkedin.com/jobs/view/<id>/` |
  | Indeed | `jk=<16 hex>` | `https://www.indeed.com/viewjob?jk=<id>` |
  | Glassdoor | `jobListingId=` or `jl=<digits>` | `https://www.glassdoor.com/partner/jobListing.htm?jobListingId=<id>` |

  Indeed's alerts (seen 2026-09) no longer carry `jk=` at all: every link is an opaque
  `https://engage.indeed.com/f/a/…` tracking redirect, and resolving it would mean fetching Indeed.
  For providers with a `redirect` pattern (`jobradar/alert_providers.py`), a card whose link has no ID
  is keyed by a hash of title, company and location (`_content_id()`, stable across emails), and its
  link is the redirect itself, accepted only when it matches that https host exactly. A card needs a
  "Company - Location" line, so the email's own browse, unsubscribe and footer links aren't jobs.
  When a card's town isn't recognised, the country comes from the alert's subject ("… jobs in United
  Kingdom"). The JD fetcher still refuses these links (`NEVER_FETCH`): paste Indeed job descriptions.

- Titles and company names are escaped before they go into the GitHub issue.

Rejected and unknown-sender emails are counted in the Radar status card's Sources table.
If legitimate alerts are rejected, check one's headers (Gmail ⋮ → Show original)
before turning `require_dkim` off.

## What breaks

- **A provider changes its email layout.** The parser reads the plain-text part
  first and falls back to the HTML part. If an alert yields no jobs, the status card
  flags "<provider> alert emails with no jobs".
- **App password revoked** (e.g. that account's password is changed): the
  source fails with an IMAP login error in the Sources table.
- **Quiet weeks** with no alerts are normal and not flagged.

> **LinkedIn is tested against real alerts** (a sanitised copy from 2026-09 in
> `tests/fixtures/alert_email/real/`), which showed LinkedIn's card "insight" lines ("This company is
> actively hiring", "Fast growing") must not be read as titles. **Indeed and Glassdoor fixtures are still
> synthetic**: once those alerts are set up, save one real email of each the same way.
