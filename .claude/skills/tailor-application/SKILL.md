---
name: tailor-application
description: Build a tailored, ATS-safe CV and cover letter for one role from the user's own career docs, validate it, and render the CV and cover letter as two PDFs in the user's own layout (resume.pdf, cover_letter.pdf). Use when the user asks to tailor their CV, prep an application, or write a cover letter for a specific role.
---

# Tailor an application

**Read `writing-rules.md` (next to this file) first**: what the CV, cover letter and stories are each for, what each CV section is for and how it reads, which sections are static, the skills rules, and the register rules. `jd_check.py tailor` runs `tools/cv_lint.py`, which enforces the mechanical ones.

0. **Masters first.** Run `python tools/master_drift.py status`. If it says the masters are not cleared, offer the `master-update` check (deterministic pass plus two
   fresh reviewers), fix what it finds, `python tools/master_drift.py clear`, and only then build or refresh the draft: drafts come from clean masters, once (the
   user's rule, 2026-09-30). `jd_check.py tailor` refuses otherwise.
1. **Identify the role.** Find its ref in `data/matches.csv` (match company/title) or on the board card.
   **"The roles on the board" means the live board, never `state/issue_map.json` or `matches.csv`** (2026-10-02: a request for "the remaining Amazon roles on the board" was answered from the issue map, which also lists cards that are archived; two aged-out roles got drafts the user never wanted). Read the board first (`session_brief.board_items`, or `gh project item-list` from `profile/board.json`: it returns only live cards) and take the roles from it. A role with an issue but no live card is **Skipped and archived**, usually by the age rule (`max_age_days`, posted too long ago) even when it was later scored apply/maybe. Don't tailor it: tell the user it is archived and why, and restore it only if they ask. When a request names a group ("all", "remaining", "the rest of company X"), list the roles you found and which of them are live before building anything.
   If it isn't scored yet, run the `score-roles` steps for it first — the must-haves drive the tailoring.
2. **Make the folder** `profile/applications/<YYYY-MM-DD>-<company>-<role>/` (lowercase, hyphens).
3. **Write `tailored.json`, always from the master documents** (the `master-update` skill re-runs this when they change).** Take every line from `profile/career/master_resume.md`
   and `cover_blocks.md`. **Never copy or start from another application's `tailored.json`**: it carries that
   role's wording, its company name and its decisions (this once put "Amazon Web Services" in an Apple and a Sonar
   letter, and dropped lines the user had approved in the master). If the checker's 450-character limit forces a
   shorter line, drop clauses from the master line; don't import another application's version. Build the file from a
   small script that reads the master by ID, so every line starts as the user's own text.
   The checker rejects capitalised names that are not in the career docs, so the letter's opening names the role in
   lowercase (`I am applying for the application security engineer role.`) and the company appears only in the
   "why this company" line at the start of a sentence. Read every rendered letter for a wrong company name.
   **Role lines in the PDF come from the master's own `## Role — Company — dates` headings** (`render_pdf.py`), not from the `tailored.json`
   section headings; the master's Consultant heading names all three employers and the PDF prints it in full. To change what the PDF shows,
   edit the master heading (the `tailored.json` heading is only for the review text and the checker's 80-character limit).
   **Header location** is always `Bangalore, India · Open to relocation` (no destination; the user's rule, 2026-10-01). No per-copy `location` field. The header carries no blog links.
   **Facts the user tells you** (a fuller version of an event, how something came about) are appended to `stories.md` as an
   "Also true (added <date>)" line on that story, in their words, so the CV, letter and stories agree.
   Note: JSON schema for the file:
   ```json
   {"key": "<ref>",
    "headline": "master P00, verbatim (static, never retitled per role)",
    "sections": [{"heading": "Summary", "bullets": [{"source_id": "P01", "text": "..."}]},
                 {"heading": "Experience — <Employer> (<dates>)", "bullets": [{"source_id": "B03", "text": "..."}]},
                 {"heading": "Certifications", "bullets": [{"source_id": "E01", "text": "..."}]}],
    "skills": ["Burp Suite", "Semgrep"],
    "cover_letter": [{"source_id": "C01", "text": "..."}, {"source_id": "S01", "text": "..."}]}
   ```
   Rules (enforced by the checker):
   - Every bullet comes from one of the user's lines: `P`/`B`/`E` IDs in sections, `C`/`S` IDs in the
     cover letter. Each ID at most once.
   - You may select, reorder and lightly rephrase — mirror the JD's vocabulary **only where the original
     line supports it**. No new numbers, employers, tools, links, emails or phone numbers.
   - **Converge with the JD's vocabulary (the user's rule, 2026-09-30; refined 2026-10-01: the Profile is the first home for convergence terms that don't fit a bullet or a skills row).** Where a JD term means the same as work in the user's
     lines (the user's examples: "security by design" for secure design review and threat modelling; "authentication and
     authorisation testing" for the auth findings; "microservice" testing for their payments work), use the JD's word: it lifts
     the ATS match. **Converged terms live in this tailored draft only and are never added to the masters** (the user's rule, 2026-10-01: the masters are untailored, polished logs and cannot carry every term from every role). Use a term when the stories back it; list it in the hand-over. Only terms the stories back up: a guardrail *review* is not
     "responsible AI", and NIST CSF, COBIT, certifications or tools they haven't used stay missing. In the hand-over, list
     the terms you converged and the ones you left missing and why.
   - **Page fit.** Static sections (Projects and writing, Volunteering, Education) are never cut; **every master bullet of a role stays unless it matches nothing in the JD at all** (the user, 2026-10-02: a relevant bullet was dropped to fit the page). Page fit is not a reason: fit two pages by shortening wording, then dropping a bullet that restates a Key achievement; if that is not enough, tell the user and ask, never cut a relevant experience bullet. A bullet that truly matches nothing is recorded in `tailored.json` as `"dropped": {"B11": "no JD match: <what the JD asks for that this line does not touch>"}`; `cv_lint.py` (so `jd_check.py tailor`) errors on any dropped master bullet without that reason, except bullets above the cap of 5 per role. All seven Skills rows stay. Tell the user exactly which lines you dropped and why.
   - **Bullet order inside a role follows the master** (the user's order, 2026-09-30: Consultant = oversight of the 8 assessors, coaching them, the four-flaws finding, the
     triage script; Staff Consultant = the appointment to lead, the airline threat models, oversight of the bank team); drop bullets, don't reshuffle them. The CV carries only job-title dates (the user's rule, 2026-09-30): no dates inside bullets. **Education years and volunteering years are exempt** (they are standard and stay); reviewers must not flag them, and neither may you.
   - Skills must appear somewhere in the career docs.
   - Put the strongest evidence for the JD's must-haves first; drop irrelevant lines; keep it to what fits
     two pages.
   - **Match the user's design (their `cv.pdf` / `cover.pdf`)**: sections in this order:
     `Summary` (the `P` lines under "Summary", which become the profile paragraph; **rewrite them heavily for the role**, in the JD's vocabulary, from facts the master and stories back: the Profile is the section that converges most; `writing-rules.md` section 2), `Key achievements`
     (**always include it**: it is part of the user's design and their master CV. **Tailor it like every other section (but it tells outcomes, not methods; `writing-rules.md` section 2):**
     choose and order `P05`-`P08` by fit to the JD's must-haves, and lightly rephrase each toward the JD's own words
     (including its bold label, e.g. "Chained attack paths:" instead of "Impact:") **only where that line supports it**,
     with no new facts, numbers or names, and nothing merged in from other lines. An event is told once in full: the achievement gives the outcome, the experience bullet the method; don't pick both when they read alike (the lint warns). Never leave the section out to save space; trim elsewhere). **Keep each achievement to a headline of 35 words or fewer, outcome only** (the user, 2026-10-02): the finding or result plus its one proof of impact; drop a second proof point, a recognition, a follow-on clause and how it landed (demonstrations, who was shown, pushback: the experience bullet carries that) in the tailored copy, and read it aloud once for awkward phrasing (`writing-rules.md` section 2; `cv_lint.py` warns above 35 words), an `Experience` block (`B01`
     first: the company's one-line description) then one section per role in reverse-chronological order, then
     `Projects`, `Volunteering`, `Education` (these three are **static**: copied verbatim from the master, always present; only Profile, Key achievements, Experience and Skills are tailored). **Skills are tailored too**: a `Skills` section of all seven `K` lines (none dropped), rows ordered by JD relevance, the items inside a row reordered JD-first or trimmed (never add a skill). Items are skill nouns only; JD phrases that are approaches ("security by design") go in the Profile, not in Skills. City and dates come from the master CV, so don't invent them.
     The CV must fit **two pages** and the cover letter **one**: cut the least relevant bullets (a bullet
     that duplicates a Key achievement goes first) and make `C12` (why in-house) the first paragraph to drop. The letter and the CV must not read alike (`writing-rules.md` section 1).
   **Read the CV and letter as a copy editor before validating**: no meta-commentary, no chat-style clauses, no repeated phrases, one tense per bullet, bullets grouped by context.
   - Headline: **static (the user, 2026-10-05)**: copy master `P00` verbatim into `headline` and never retitle it per role or per JD; the Profile and Skills carry the convergence.
   - Visa sponsorship: the CV header (from `master_resume.md`'s `location`) does not say "Requires visa sponsorship" by default;
     the user decides per application (often after a referral or a first conversation). Ask before adding it to `location` for that
     copy; the cover letter block `C13` states it either way. An ATS screening filter may reject on the phrase; a recruiter may want it.
   - **Picking the letter's points (the user, 2026-10-05):** the header of `profile/career/cover_blocks.md` is the procedure. Name the JD's 3-4 requirements in your own words, then choose up to three blocks whose `cv anchor` is in the tailored CV and whose `proves` tags match, preferring the lowest `rank` (what the CV leaves out), draft each in plain language (challenge, what you did, impact last) with one clause of your intent (what you were trying to protect or achieve and why, from the story's Task and Lesson lines; never invented) and shorten to one page. Blocks under "other situations" need the user's word. **Label each block for this letter (the user, 2026-10-05):** master cover blocks have no titles (a block covers several angles) but a `labels` list of candidate titles in their metadata comment; pick from it, combine or rephrase to name the JD need the block answers here (the same need words as the opening), and set it as `"label"` on every body block in `cover_letter` (2-40 plain characters, no punctuation). Related blocks may be merged when they answer the same need. **Before validating, run the letter pass in `writing-rules.md` section 1 (k):** exact JD nouns the CV lacks, no claim beyond its story (hedge inferences), open on the stake and close on a result, plain words, one fact per block, sentences of 40 words or fewer. `jd_check.py` accepts the field, `render_pdf.py` prints it as the run-in label, `cv_lint.py` errors when a title-less block has none.
   - Cover letter content rules (the user, 2026-10-05; full text in `writing-rules.md`): reword the ad's requirements in your own words (never its sentences), no sub-bullets, add what the CV does not say, "why this company" is about the company and role, and pressure stories lead with impact.
   - Cover letter: 3-4 paragraphs from cover blocks and condensed STAR stories; mention sponsorship needs
     honestly if the role is abroad (block `C03`-style text if they have one).
   **Self-contained lines and matching documents (read the finished CV and letter top to bottom before validating):**
   - A line that says "the bank", "the same bank", "the client" or "the team" needs its referent introduced *earlier in that same document*. Tailoring
     reorders and drops lines, so a reference that worked in the master can dangle. Fix by reordering (put the paragraph that names the bank first) or by
     swapping the phrase for a generic noun ("a global financial institution"). Add no facts, and no numbers: the checker rejects a number the line
     didn't have, so "Fortune 100" cannot be added to a line that lacks it.
   - Everything the letter claims in its opening (C01) must be backed by a line in the CV. If the CV dropped the supporting line (e.g. technical oversight of a
     team), drop the clause from the letter, or restore the line.
   - The masters stay as the user's logs; fix these in the tailored file, not in `master_resume.md`.
4. **Validate:** `python tools/jd_check.py tailor <folder>`. Fix every error; never work around one.
   Warnings about heavy rewording mean you drifted from what the user actually did — tighten it.
5. **Render:** `python tools/render_resume.py <folder>` → **two files only, the user's rule**: `resume.pdf` (two pages)
   and `cover_letter.pdf` (one page), in the layout of the user's own `cv.pdf` / `cover.pdf`. It uses Chrome or
   Edge, which are already installed; nothing to pip install. The same text as Markdown is written to
   `work/apps/<folder>/` as scratch for the review skills (not a deliverable). Master documents (career docs,
   stories) already exist and don't change per application. The folder holds nothing else the user must read
   (`tailored.json` and `validated.sha256` are the checker's own files). **No `--md` (Markdown in the folder),
   no `--docx`, unless asked or an application form needs a Word upload.** No `review.md`, no other extra documents.
   After rendering, check the page count (CV 2, letter 1).
   **Once the user has approved the content, never change it to fit the page**: adjust spacing in
   `tools/render_pdf.py` or ask; changing approved text needs their yes.
6. **Review gate.** Run the `application-review` skill on this folder (ATS, recruiter and consistency
   subagents plus `tools/consistency_check.py`); its findings go to the user **in the chat, not in a file**. Fix or
   ask the user about every "fix before applying" finding, then re-validate and re-render. **Never run it unasked** (the user's rule, 2026-10-05, replacing 2026-09-30's "never skip"): offer it in one line when the build is done and launch the readers only on the user's word. When asked, all four readers (ATS, recruiter, consistency, copy editor) on the application named.
   If the user only asked for the CV, still build both files (they need both eventually), but lead
   with the CV.
7. **Hand over for review.** Print the **Key achievements section in full** in your reply (the checker's diff lists only
   changed lines, and these are master lines, so they don't show there), with one line on why each was chosen or left out
   and what you changed in its wording, and the **Skills rows chosen and dropped** the same way. Then show the user the diff the checker printed (what changed from their master
   CV), where the two files are, any JD must-haves their CV couldn't evidence, and the review verdict. They review, edit and
   apply themselves. Then offer to move the card to Shortlisted (`track`).
