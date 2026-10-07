# 5. Code reference

**What this is:** Every file and every function, one line each, with **Watch out** notes on lines whose purpose isn't obvious. It is split into six pages by where the code runs and what it does; this page is the index.
**Read first:** pages [2](02-Architecture.md) to [4](04-Claude-session.md)
**Code:** all of it

Files are grouped by where they run. A lookup section: skim the index now, open a sub-page when you open a file.

## The pages

| Page | Covers |
|---|---|
| [5.1 Entry points](05-1-Entry-points.md) | `radar.py` (the scheduled pipeline) and `verify_boards.py` |
| [5.2 The `jobradar` package](05-2-Package.md) | the shared data shapes, settings, matching, dedupe, health, tiering, sponsors, board payloads, trust boundary, career docs |
| [5.3 `jobradar/sources/`](05-3-Sources.md) | the adapters: ATS boards, search APIs, careers pages, alert emails |
| [5.4 Board and session tools](05-4-Board-and-session-tools.md) | `board_sync.py`, `cadence.py`, `session_brief.py`, `public_template.py`, referrals, post leads, sponsorship, calibration |
| [5.5 Application tools](05-5-Application-tools.md) | job descriptions, `jd_check.py`, the renderers, `cv_lint.py`, the consistency, drift and outcome checks |
| [5.6 Setup and upkeep tools, config and constants](05-6-Setup-tools-and-config.md) | mail fetching, registers, candidate boards, fixtures, workflow files, settings pointers, remaining constants |

## Every tool, and where it is described

| Tool | Is | Page |
|---|---|---|
| `tools/board_sync.py` | GitHub issues and the Project (standard library only) | [5.4](05-4-Board-and-session-tools.md) |
| `tools/cadence.py` | the cadence ledger (standard library only) | [5.4](05-4-Board-and-session-tools.md) |
| `tools/cover_sync.py` | the cover blocks follow the stories and CV lines they expand (`status`, `done`) | [5.5](05-5-Application-tools.md) |
| `tools/jd_cleanup.py` | trims `jd.txt` and `packet.md` of skipped and rejected roles after 14 and 30 days | [5.4](05-4-Board-and-session-tools.md) |
| `tools/session_brief.py` | the SessionStart hook (standard library only) | [5.4](05-4-Board-and-session-tools.md) |
| `tools/public_template.py` | keep the public template current and clean | [5.4](05-4-Board-and-session-tools.md) |
| `tools/manual.py` | the `man` page | [5.4](05-4-Board-and-session-tools.md) |
| `tools/referrals.py` | referral routes and asks (standard library only) | [5.4](05-4-Board-and-session-tools.md) |
| `tools/add_role.py` | add a role you found yourself (a job link) through the radar's own filters and bookkeeping | [5.4](05-4-Board-and-session-tools.md) |
| `tools/post_leads.py` | LinkedIn hiring-post discovery (standard library only) | [5.4](05-4-Board-and-session-tools.md) |
| `tools/sponsorship.py` | checked sponsorship verdicts (standard library only) | [5.4](05-4-Board-and-session-tools.md) |
| `tools/calibrate.py` | automatic tier tuning (standard library only) | [5.4](05-4-Board-and-session-tools.md) |
| `tools/jd_prep.py` | fetch job descriptions | [5.5](05-5-Application-tools.md) |
| `tools/jd_check.py` | validate Claude's output | [5.5](05-5-Application-tools.md) |
| `tools/render_resume.py` | CV and cover letter files | [5.5](05-5-Application-tools.md) |
| `tools/render_pdf.py` | the CV and cover letter as PDFs in the user's Claude Design layout | [5.5](05-5-Application-tools.md) |
| `tools/inbox_outcomes.py` | applications awaiting an answer, and an outcome-email classifier | [5.5](05-5-Application-tools.md) |
| `tools/fetch_application_mail.py` | the scheduled run's mailbox scan for replies about applied roles (standard library only) | [5.5](05-5-Application-tools.md) |
| `tools/app_mail.py` | application-mail ledger, plan and brief lines (standard library only) | [5.5](05-5-Application-tools.md) |
| `tools/master_drift.py` | which applications no longer match the master documents | [5.5](05-5-Application-tools.md) |
| `tools/cv_lint.py` | form and section rules for CV and letter text | [5.5](05-5-Application-tools.md) |
| `tools/consistency_check.py` | cross-check CV, cover letter and STAR stories | [5.5](05-5-Application-tools.md) |
| `tools/fetch_alert_emails.py` | IMAP (standard library only) | [5.6](05-6-Setup-tools-and-config.md) |
| `tools/refresh_registers.py` | sponsor registers | [5.6](05-6-Setup-tools-and-config.md) |
| `tools/build_candidates.py` | targets → candidate boards (setup) | [5.6](05-6-Setup-tools-and-config.md) |
| `tools/discover_boards.py` | find boards for uncovered targets | [5.6](05-6-Setup-tools-and-config.md) |
| `tools/check_doc_links.py` | doc link checker (standard library only) | [5.6](05-6-Setup-tools-and-config.md) |
| `tools/record_fixture.py` | capture a test fixture | [5.6](05-6-Setup-tools-and-config.md) |
