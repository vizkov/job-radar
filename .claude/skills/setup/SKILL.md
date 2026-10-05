---
name: setup
description: First-time setup of the user's private job-radar — profile, career docs, target companies, board discovery, sponsor registers, GitHub Project board, optional alert emails, and enabling the daily workflow. Use when the user asks to set things up or profile/ doesn't exist.
---

# Set up job-radar for the user

Work through these in order, asking only what you need. Check each step before moving on. Explain in
plain language; do the typing yourself.

1. **Repo.** Confirm this is a **private** repo (`gh repo view --json visibility`). If it's the public
   template, stop and explain the private-copy steps in docs/design/14-Setup-and-publishing.md (clone, `git remote rename
   origin template`, new private `origin`). Install: `python -m venv .venv`, then
   `pip install --require-hashes -r requirements.txt -r requirements-career.txt`.
2. **Profile.** `mkdir profile` and copy `examples/*` into it. Interview the user:
   - countries (priority / extra), role titles they want and don't want, seniority → `profile/config.json`;
   - target companies → `profile/targets.tsv` (Company<TAB>Offices);
   - their CV → `profile/career/master_resume.md` in the ID format (see `examples/career/`). If they paste
     or attach a CV, convert it yourself: one ID per bullet, contact details in the front matter, and show
     them the result to confirm nothing was changed. Same for STAR stories and cover-letter paragraphs.
3. **Data.** `python tools/refresh_registers.py`; clone `atss/` and `agg/` (docs/design/14-Setup-and-publishing.md) and run
   `python tools/build_candidates.py` then `python verify_boards.py --quiet`. Report coverage from
   `data/coverage_report.csv`: which targets have no board, and offer careers pages / alerts for those.
4. **Board.** Ask the user to run `gh auth refresh -s project` (a browser login — suggest typing
   `! gh auth refresh -s project` here). Then `python tools/board_sync.py setup-project --repo OWNER/REPO`. It creates the fields and the
   views defined in `VIEWS` (tools/board_sync.py), then prints the sort/grouping clicks the API can't do:
   relay those to the user.
   Walk them through the one manual step it prints (Project → Workflows → Auto-add, filter
   `is:issue label:role`), and optionally "Item closed → Done".
4b. **LinkedIn job pages (ask, default off).** Say the risk plainly: LinkedIn's terms ban automated access, so reading job pages in their
   logged-in Chrome could get the account restricted, even one page at a time. Ask whether to switch it on; set `scoring.linkedin_job_pages`
   in `profile/config.json` to `true` only on a clear yes, otherwise leave it `false` (scoring then asks them to paste LinkedIn descriptions).
5. **Alert emails (optional).** Explain why a dedicated Gmail is needed (docs/design/12-Job-alert-emails.md),
   guide them through alerts, forwarding filter and app password, and adding the two secrets in the GitHub
   UI themselves. Never ask them to paste the password into chat or a file.
6. **Template sync (only if this user also maintains a public template).** `git config core.hooksPath
   .githooks` and `git config jobradar.templateDir <path to template clone>`; after that every commit
   publishes code changes. Skip for a normal user: the hook does nothing without `jobradar.templateDir`.
7. **Go live.** Commit `profile/`, `data/`, `boards.json`; push to `origin`; enable Actions
   (`gh workflow enable` for radar, verify-boards, sponsor-registers); run the first one:
   `gh workflow run job-radar`. The first run is a baseline: Tier 1 roles go to the board.
8. **Wrap up.** Tell them: from now on they just talk to you and watch the board; suggest they set the
   repo's watch level to "Participating and @mentions" so role issues don't email them.
