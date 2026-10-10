---
name: cv-review
description: Compare what the user's target roles keep asking for (from scored job descriptions) with their CV and career docs, and recommend CV improvements, missing evidence to write up, and certifications or skills worth pursuing. Use when the session brief shows recurring CV gaps, after a batch of scoring, or when the user asks how to strengthen their CV.
---

# CV and career-docs review

Evidence first: every recommendation must point at real job descriptions the user is targeting.

1. **Collect demand.** From `data/scores.jsonl`: every `missing` requirement and blocker, counted across
   roles, split by recommendation (apply/maybe vs skip) and by country. From `work/jd/*/jd.txt` for the
   scored roles, count recurring must-have terms (certifications like CREST CRT/CCT, OSCP, CISSP, OSWE;
   languages; cloud; frameworks). Ignore requirements that appear only once.
2. **Collect supply.** Read `profile/career/` (master CV, stories, cover blocks).
3. **Classify each recurring gap**:
   - **Wording gap:** the user has the experience but the CV doesn't say it in the words the roles use.
     Propose a rephrase of an existing line; the user confirms it's accurate before you edit
     `master_resume.md` (keep the same ID).
   - **Evidence gap:** likely true but undocumented (a project, a story). Ask the user; if they confirm,
     draft a new ID'd bullet or STAR story from their own words for them to approve.
   - **Real gap:** they don't have it. Say so plainly, with how often it blocks their target roles, and
     the cheapest credible way to close it (e.g. which certification, typical time/cost, whether UK
     consultancies accept an alternative). No advice on paying for anything without the user asking.
   - **Hard blocker** (clearance, citizenship, right to work): not fixable by CV; suggest filtering or
     de-prioritising those roles instead (`tune-radar`).
   - **Proof-of-work gap:** the CV has no public evidence a reader can open (write-ups, CVEs, CTF or lab rankings, GitHub
     tooling, certs). Recommend the cheapest one or two that fit the target roles (a threat-model write-up of a generic flow,
     a small tool, a lab ranking), as a long game next to applications. Never use client data or anything under NDA; nothing
     goes into the career docs until the user has it and confirms it. Link the best three items at most, from one hub page.
4. **Check freshness of docs:** roles or dates that look out of date, a summary that no longer matches the
   roles being targeted, missing STAR stories / cover blocks.
5. **Report** the top 5 items: gap, how many target roles it affects, type, proposed action. Never add
   anything to the career docs the user hasn't confirmed is true.
6. Stamp the cadence job: `python tools/cadence.py done cv_review` (the CADENCE block offers this review at most once a week,
   while the brief shows recurring CV gaps).
