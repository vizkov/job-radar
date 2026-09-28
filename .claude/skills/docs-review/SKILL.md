---
name: docs-review
description: Test the docs by having two fresh subagents read them cold — a developer new to the project reading docs/design, and a job seeker who has never used it reading docs/wiki — then verify each finding against the code and fix the docs (and any code bugs found). Use when the session brief says a docs review is due, after a big change to the system, or when the user asks whether the docs are still accurate or understandable.
---

# Docs review (cold read by two subagents)

Why subagents: you already know the system, so you can't notice what a newcomer can't
follow. Each reader must start with no context. Use two, because a reader who has read the
design docs is no longer a zero-knowledge user of the guide.

## 1. Launch both readers in parallel (read-only)

Spawn two Agents (`subagent_type: general-purpose`) in the same message, each with a
self-contained brief. Both must be told: READ-ONLY, edit nothing, no network, no commands
that change anything.

**Design reader** (default model: it has to check claims against code):
> You are a competent Python developer who has never seen this project. Test whether
> docs/design delivers its promise: a zero-knowledge reader ends up knowing what each file
> and function does. (1) Read docs/design/README.md then pages 01–15 in order; note every
> confusion, undefined term, wrong order, repetition or contradiction, with page and quote.
> (2) Before opening code, write what you believe radar.py, jobradar/dedupe.py,
> jobradar/health.py, tools/board_sync.py, tools/session_brief.py, tools/jd_check.py,
> tools/public_template.py and one file changed recently (name it: <pick from git log>)
> do. (3) Open them and compare; list files in the repo the docs never mention (excluding
> profile/, state/, data/, digests/, work/, tests/fixtures/, .venv/, atss/, agg/).
> (4) Check 10 factual claims (names, constants, thresholds, paths, flags) against code.
> Report under 900 words: A verdict; B top 10 problems (page, quote, problem, fix);
> C factual errors (claim, page, what code says, file:line); D files/functions not covered.
> Be blunt; no praise.

**Guide reader** (`model: "sonnet"` is enough; it reads four short pages):
> You are a job seeker, comfortable with computers but not a developer, who has never used
> this tool. Read ONLY docs/wiki/Home.md and the pages it lists, in its order (plus README.md
> if a page sends you there). Never read docs/design or code. Note every unexplained word,
> unclear step or order, unaddressed worry (privacy, cost, accounts, consent), contradiction,
> and unanswered question. Then say whether you could (1) set it up, (2) use it day to day,
> (3) read the board, (4) know what it will and won't do with your accounts.
> Report under 600 words: A verdict; B top 8 problems (page, quote, problem, fix);
> C questions a new user would still have. Be blunt; no praise.

## 2. Verify before fixing

Treat every finding as a claim to check, not a fact. For each factual error, open the
cited code and confirm. Drop what doesn't hold up. Findings that reveal a **code** bug (not
just a doc error) go to the user as a proposed fix unless trivially safe; say which.

## 3. Fix

- Docs: correct the facts, add missing contracts/keys/files, keep each page's opening
  block (What this is / Read first / Code) and the guide's "This page / Next" framing.
  User-guide text addresses "you"; design text says "the user".
- Keep the two audiences apart: step-by-step user instructions belong in docs/wiki;
  mechanisms belong in docs/design, linking to the guide rather than repeating it.
- Run `python tools/check_doc_links.py .` (every relative link and every `docs/…/*.md` path
  resolves) and `pytest -q`.

## 4. Record and report

- Write the current UTC time to `work/.last_docs_review`.
  **Only a completed review writes this stamp.** Never set it by hand or when adding the
  trigger: anything changed between the last real review and the stamp would become
  invisible to the counter. (The one exception is the trigger's own first run on a fresh
  copy, which writes it once to start counting.)
- Commit (the post-commit hook publishes docs and the wiki mirror).
- Tell the user: each reader's verdict in one line, what you fixed (grouped), what you
  rejected as not holding up, and any code issue that needs their decision.
