---
name: tailor-application
description: Build a tailored, ATS-safe CV and cover letter for one role from the user's own career docs, validate it, and render the CV and cover letter as two PDFs in the user's own layout (resume.pdf, cover_letter.pdf). Use when the user asks to tailor their CV, prep an application, or write a cover letter for a specific role.
---

# Tailor an application

1. **Identify the role.** Find its ref in `data/matches.csv` (match company/title) or on the board card.
   If it isn't scored yet, run the `score-roles` steps for it first — the must-haves drive the tailoring.
2. **Make the folder** `profile/applications/<YYYY-MM-DD>-<company>-<role>/` (lowercase, hyphens).
3. **Write `tailored.json`:**
   ```json
   {"key": "<ref>",
    "headline": "one line, e.g. Application Security Engineer — secure code review & threat modeling",
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
   - Skills must appear somewhere in the career docs.
   - Put the strongest evidence for the JD's must-haves first; drop irrelevant lines; keep it to what fits
     two pages.
   - **Match the user's design (their `cv.pdf` / `cover.pdf`)**: sections in this order:
     `Summary` (the `P` lines under "Summary", which become the profile paragraph), `Key achievements`
     (**always include it**: it is part of the user's design and their master CV. **Tailor it like every other section:**
     choose and order `P05`-`P08` by fit to the JD's must-haves, and lightly rephrase each toward the JD's own words
     (including its bold label, e.g. "Chained attack paths:" instead of "Impact:") **only where that line supports it**,
     with no new facts, numbers or names, and nothing merged in from other lines. That they repeat some experience bullets is fine: the user's own CV does
     the same. Never leave it out to save space or avoid repetition; trim elsewhere), an `Experience` block (`B01`
     first: the company's one-line description) then one section per role in reverse-chronological order, then
     `Projects`, `Volunteering` (if it fits), `Education`. **Skills are tailored too**: a `Skills` section of `K` lines,
     the rows most relevant to the JD first, the least relevant rows dropped, and the items inside a row reordered
     JD-first (drop or reorder only; never add a skill). The renderer draws it as the skills grid, so a `Skills`
     section replaces the master's full seven rows. City and dates come from the master CV, so don't invent them.
     The CV must fit **two pages** and the cover letter **one**: cut the least relevant bullets (a bullet
     that duplicates a Key achievement goes first) and make `C12` (why in-house) the first paragraph to drop.
   - Headline: the target role title and 1-2 strengths; no contact details.
   - Visa sponsorship: the CV header (from `master_resume.md`'s `location`) does not say "Requires visa sponsorship" by default;
     the user decides per application (often after a referral or a first conversation). Ask before adding it to `location` for that
     copy; the cover letter block `C13` states it either way. An ATS screening filter may reject on the phrase; a recruiter may want it.
   - Cover letter: 3-4 paragraphs from cover blocks and condensed STAR stories; mention sponsorship needs
     honestly if the role is abroad (block `C03`-style text if they have one).
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
   ask the user about every "fix before applying" finding, then re-validate and re-render. Skip only if the user
   says not to. If the user only asked for the CV, still build both files (they need both eventually), but lead
   with the CV.
7. **Hand over for review.** Print the **Key achievements section in full** in your reply (the checker's diff lists only
   changed lines, and these are master lines, so they don't show there), with one line on why each was chosen or left out
   and what you changed in its wording, and the **Skills rows chosen and dropped** the same way. Then show the user the diff the checker printed (what changed from their master
   CV), where the two files are, any JD must-haves their CV couldn't evidence, and the review verdict. They review, edit and
   apply themselves. Then offer to move the card to Shortlisted (`track`).
