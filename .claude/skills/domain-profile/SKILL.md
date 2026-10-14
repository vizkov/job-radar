---
name: domain-profile
description: Work out which industry domains the user's record backs (payments, banking, aviation AI…) by quizzing them about work their CV and stories never mention, then write profile/domains.json with the evidence IDs for each. Use when the user wants to target a domain (for example fintech), after a master change when the brief says domains.json is stale, or when tailoring or scoring needs to know whether the user's record fits a role's domain.
---

# Domain profile

What this is: a short record of which domains the user can honestly show expertise in, with the CV lines and stories that prove each,
and what they must **not** claim. `score-roles`, `tailor-application` and the sector tag in tiering read it instead of the masters.

Why it quizzes: the masters only hold what the user already wrote down. Nobody writes down work they do not know counts. Ask by
what they would have *seen*, in plain words, never by jargon ("did you see card numbers swapped for tokens?", not "tokenisation?").
The first run (2026-10-20, payments) found five defensible areas that were in no document.

## Steps

1. `python tools/domain_profile.py status`. Missing or stale? Continue. Current? Say so and stop.
2. Read `profile/domains.json` if it exists. Every quiz area with an answer is **not asked again** (a `no` or `unsure` counts; re-ask an
   `unsure` only if the user says they have found something). Read the masters only through `load_career` IDs; do not paste them into chat.
3. Pick the domain being targeted (the user named one, or the brief's sector) and its question bank in `quiz.md`. Ask a round of at
   most nine questions at a time, yes / no / unsure, with a free-text note. For each yes also ask: **could you explain it for five
   minutes in an interview?** and **what was your role** (assessor, oversight, reviewer, builder). Roles differ per client; keep
   them apart.
4. Turn answers into the user's own wording. Narrow, never widen: "key vaults" is not "HSMs"; "reviewed" is not "built"; testing a
   system is not scoping it. Show the draft lines and get a yes before writing anything.
5. On the user's yes: append "Also true (added <date>, the user)" lines to the matching story in `stories.md`. If the user wants a CV
   line, add a master bullet with the next free ID (domain-neutral wording; it must read true on a non-domain role too), and say it
   in one line. These are master changes: the `master-update` gates apply (rule 12: offer the consistency check, never run it unasked).
6. Write or update `profile/domains.json` (schema: `tools/domain_profile.py` docstring and the file itself): one entry per domain with
   `strength`, `sectors`, `evidence` IDs, `lead_ids` (what a tailored CV leads with for that sector, strongest first) and `not_claimed`.
7. `python tools/domain_profile.py validate` (every ID must exist, `strong` needs two pieces of evidence, `not_claimed` is required).
   Fix and re-run until it passes; it stamps the masters' digest so `status` knows when it goes stale.

## How the rest of the system uses it

- `tailor-application`: for a role whose sector is in a domain's `sectors`, `python tools/domain_profile.py lead <sector>` gives the
  IDs to put first within each section. Selection and order only; the static headline and rule 11 (no relevant bullet dropped) hold.
- `score-roles`: add one "domain fit" line citing the IDs (met / partial / none). It can lower confidence but never raises a band.
- Never claim anything under `not_claimed`; a cover letter that needs it asks the user first.

Rules: nothing the user did not say; no client names anywhere (the bank and the credit and payments client are descriptors); a
strength is a judgement and a domain can be `thin` or absent: say so plainly.
