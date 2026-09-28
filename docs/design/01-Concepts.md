# 1. Concepts

**What this is:** Every term the other pages use, defined once and grouped by the world it comes from.  
**Read first:** nothing  
**Code:** none: this page is vocabulary

Skim it now; come back when a word is unclear.

## The job-search world

| Term | Meaning |
|---|---|
| **Posting** / **role** / **job ad** | One advertised job. The same role is often advertised in several places. |
| **ATS** (applicant tracking system) | The software a company uses to publish jobs and receive applications: Greenhouse, Lever, Workday, Ashby, Personio, SmartRecruiters and so on. Each company has a **board** on its ATS, a page listing its open jobs, usually with a machine-readable API behind it. |
| **Slug** | The company's short name inside an ATS URL: `bridewell` in `apply.workable.com/bridewell`. With the ATS name, it identifies a board. |
| **Careers page** | A company's own jobs web page. Some are just a front for an ATS; some are hand-made HTML with no API. |
| **Public job portal** | A government job site with a public search API: Germany's Bundesagentur für Arbeit, Sweden's JobTech (Arbetsförmedlingen), the EU's EURES. |
| **Job-alert email** | An email LinkedIn, Indeed or Glassdoor sends when new jobs match a saved search. job-radar reads these instead of scraping those sites, which their terms forbid. |
| **JD** (job description) | The full text of a job ad: responsibilities, requirements. |
| **Sponsor licence / register** | The UK and the Netherlands publish lists of employers licensed to sponsor work visas. A match means the employer *can* sponsor, not that it will for this role. |

## The GitHub world

| Term | Meaning |
|---|---|
| **Repository (repo)** | A folder of files with full version history (git), hosted on GitHub. **Public** repos are visible to anyone; **private** ones only to their owner. |
| **Template repo** / **private copy** | job-radar's code lives in a public repo (the *template*, `vizkov/job-radar`). Each user runs their own *private copy*, which has the same code plus their personal settings and data. The private copy knows the public one as the git remote `template`. |
| **Commit** / **push** / **pull** | Save a set of changes into history / send commits to GitHub / fetch commits from GitHub. |
| **Issue** | A GitHub discussion item (title, body, labels). job-radar creates one issue per role. |
| **Label** | A coloured tag on an issue: `role`, `tier-1`, `country-GB`, `sponsor-yes`, `possibly-closed`. |
| **Project** / **board** | GitHub Projects: a spreadsheet- or kanban-like view over issues. Each issue on it is a **card** (an *item* in the API). |
| **Field** | A column on a Project, with a value per card. job-radar's: *Stage*, *Tier*, *Recommendation*, *Sponsor*, *Referral* (single-selects), *Fit* (a number), *Posted* (a date). Fields belong to the Project; labels belong to the issue. |
| **View** | A saved way of looking at a Project: which columns show, which filter applies, sort order, and table or board layout. job-radar has *All Roles*, *Act now* and *Pipeline*. |
| **GitHub Actions** / **workflow** | GitHub's automation: a YAML file in `.github/workflows/` describes steps that GitHub runs on its own servers, on a schedule or on demand. A **run** is one execution. |
| **cron** | The schedule format in a workflow: `47 2,8,14 * * *` = minute 47 of hours 2, 8 and 14 UTC, every day. GitHub treats schedules as best-effort: runs can be late or skipped. |
| **Secret** | A value stored encrypted in the repo's settings (Settings → Secrets) and given to a workflow step as an environment variable. Never in files. |
| **GITHUB_TOKEN** | A short-lived credential GitHub gives every workflow run, limited to that repo. It can create issues but **cannot edit a user-owned Project**, which shapes the whole board design. |
| **`gh`** | GitHub's command-line tool. On the user's machine it uses their own login; in Actions it uses GITHUB_TOKEN. |
| **GraphQL API** | GitHub's query API. Used for things `gh` has no command for, like creating a Project view. |
| **Wiki** | A separate mini-repo attached to a GitHub repo, shown in its Wiki tab. job-radar copies the user guide into it. |

## The Claude world

| Term | Meaning |
|---|---|
| **Claude Code** | Anthropic's AI coding assistant, running in a terminal (or desktop/web app) inside the user's private copy. It can read and edit files and run commands. It runs on the user's Claude subscription: **there is no API key anywhere in job-radar.** |
| **`CLAUDE.md`** | A file Claude Code reads at the start of every session. job-radar's tells Claude its role (the user's job-search consultant), which skill to use for what, and the rules it must never break. |
| **Skill** | A Markdown file in `.claude/skills/<name>/SKILL.md`: a written procedure Claude follows for one kind of request ("score the new roles"). The user never calls skills by name; Claude picks one from what they say. |
| **Hook** | A command Claude Code runs automatically at an event. job-radar uses a *SessionStart* hook to prepare a briefing each time a session opens. |
| **Subagent** | A second Claude instance that a session starts for one bounded task, optionally on a smaller model. |
| **Claude in Chrome** | A browser extension that lets Claude read and operate pages in the user's Chrome. Used only to pre-fill application forms, with the user approving each page. |

## job-radar's own terms

| Term | Meaning | Where in code |
|---|---|---|
| **ats-scrapers** | The third-party Python package that knows how to read each ATS's job list (Greenhouse, Workday…). The `ats` source is built on it. | `requirements.in`, `common.py: fetch_board()` |
| **Digest** | The per-run Markdown report of new roles (`digests/<date>.md`), for Claude and for debugging. | `radar.py: render_digest()` |
| **Radar status issue** | One pinned GitHub issue, rewritten each run with counts and source health (no job titles). It appears as a card on the board. | `radar.py: render_status()`, `board_sync.py: sync_status()` |
| **REMOTE-EU** | A pseudo-country for "remote, Europe/EMEA/EU" locations; treated like a target country. | `common.py: _REMOTE_EUROPE` |
| **Canary query** | A deliberately broad search each API source runs; if even that returns nothing, the API itself is probably broken. | `sources/search.py` |
| **track_empty** | Per unit: whether zero results counts as a problem (False for narrow searches and quiet mailboxes). | `model.py: UnitStatus` |
| **Design diff** | The difference between the board's actual views and the views defined in code (`VIEWS`). | `board_sync.py: design_diff()` |
| **Source** / **adapter** | One place postings come from (`ats`, `bundesagentur`, `jobtech`, `eures`, `careers_page`, `alert_email`), and the code that reads it. Every adapter turns its input into `Posting` objects. | `jobradar/sources/` |
| **Unit** | One thing a source polls: one ATS board, one search query, one careers page, one email provider. Health is tracked per unit. | `model.py: UnitStatus` |
| **Target** | A company the user wants to work for, listed in `targets.tsv`. Roles at other companies are "outside your list" and dropped by default. | `profile/targets.tsv` |
| **Alias** | Another spelling of a target's name ("PricewaterhouseCoopers" → "PwC"). | `profile/aliases.csv` |
| **Normalize** | Turning a company name into a comparable key: lower-case, no accents or punctuation, no "Ltd/GmbH/B.V.", no "UK/NL/Cyber". `Pen Test Partners LLP` → `pentestpartners`. | `matching.py: normalize()` |
| **Canonical name** | The target name a posting's employer resolved to. `None` means "not on the list". | `Posting.company_canonical` |
| **Content key** | `c:<company>|<title>|<country>`, all normalized. Two postings with the same content key are the same role. | `dedupe.py: content_key()` |
| **Group** | All postings sharing a content key. The best one (by source rank) supplies the link; the others become "also on". | `dedupe.py: Group` |
| **ref** (Role ID) | The first 16 hex characters of the SHA-1 of the content key, e.g. `3140f52f7d4f47fc`. It links a role's issue, its `matches.csv` row, its JD folder, its score and its application. | `board.py: role_ref()` |
| **Seen** | `state/seen.json` remembers every posting ID and content key already reported, with the last date seen. A role is "new" only if none of its keys were seen. | `radar.py: diff_seen()` |
| **Baseline** | The very first run (empty `seen.json`). Everything open is recorded, but only Tier 1 goes to the board so the user doesn't start with hundreds of cards. | `board.py: select_for_board()` |
| **Score** / **tier** | A rule-based number from title keywords, seniority, country, list membership, sponsor status and freshness. Tier 1 if score ≥ 6, else Tier 2. No AI involved. | `tiering.py` |
| **Fit** | A different, AI-judged score (0–100): Claude compares the JD with the user's CV. Set on the board as the *Fit* field. | `tools/jd_check.py` |
| **Sponsorship verdict** | Claude's checked answer to "will this employer sponsor this role for this user?": confirmed, likely, licensed, unclear, unlikely, no, with evidence (ad quotes, register, company pages). Replaces the register-only value on the Sponsor field. | `tools/sponsorship.py`, `sponsorship-check` skill |
| **Calibration** | Weekly automatic adjustment of tier title-keyword weights from Fit scores: one step, bounded, logged, reversible. | `tools/calibrate.py` |
| **Sponsor tag** | `yes` / `unknown` / `no`, plus the register entry it matched. | `sponsors.py: SponsorTag` |
| **Board queue** | Roles chosen for the board, waiting to become issues (at most 40 per run). | `state/board_queue.json` |
| **Payload** | One queued role: `{ref, title, body, labels}`, ready to become an issue. | `board.py: payload()` |
| **Stale** / **possibly-closed** | A board role no source has listed for more than `stale_days` (5) days. Its issue gets the `possibly-closed` label. | `board.py: stale_refs()` |
| **Profile** / **examples** | `profile/` holds the user's real settings (private). `examples/` holds generic samples (public). Every settings file is read from `profile/` if present, else `examples/`. | `paths.py: profile_path()` |
| **Career docs** / **IDs** | The user's CV, STAR stories and cover-letter paragraphs, one ID per line, e.g. `[B07]`. The letter says what kind of line it is (table below). Tailored CVs may only reuse these lines, cited by ID. | `career.py` |
| **Referral route** | How the user might get referred for a role, tried in their order: friends and family, their network (connections), then recruiters and hiring managers. Each ask and answer is logged; the card's Referral field shows where it stands. | `tools/referrals.py`, `referrals` skill |
| **Fit breakdown** | The block on a scored card listing what matches the user's CV, what partly does and what doesn't (blockers first), between `<!-- job-radar:fit -->` markers. | `board_sync.py: fit_section()` |
| **Packet** | `work/jd/<ref>/packet.md`: a role's facts plus its JD wrapped as untrusted data, prepared for Claude to read. | `tools/jd_prep.py` |
| **Untrusted text** | Anything a stranger wrote: job titles, company names, JDs, emails. It is data to analyse, never instructions to follow. | `untrusted.py` |
| **Drift** | Code changed in the private copy that the public template doesn't have yet. | `tools/public_template.py: drift()` |

### Career-doc ID prefixes

| Prefix | Kind of line | File | May appear in |
|---|---|---|---|
| `P` | Profile / summary line | `master_resume.md` | CV sections |
| `B` | Experience bullet | `master_resume.md` | CV sections |
| `K` | Skills line | `master_resume.md` | nowhere directly; like every line, its words count as "in the career docs" for the skills and names checks |
| `E` | Education / certification | `master_resume.md` | CV sections |
| `S` | STAR story | `stories.md` | cover letter |
| `C` | Cover-letter paragraph | `cover_blocks.md` | cover letter |

Enforced by `SECTION_KINDS` (`P`, `B`, `E`) and `COVER_KINDS` (`C`, `S`) in `tools/jd_check.py`.

### Source names vs posting sources

A source adapter's name (the key in `sources.yaml`) is usually also the `source` of the
postings it produces (`ats`, `eures`, …). The exception is `alert_email`: its postings are
labelled per provider, `linkedin_email`, `indeed_email` or `glassdoor_email`, so the
digest, `matches.csv` and `dedupe.SOURCE_RANK` can tell them apart.
