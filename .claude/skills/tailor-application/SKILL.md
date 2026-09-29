---
name: tailor-application
description: Build a tailored, ATS-safe CV and cover letter for one role from the user's own career docs, validate it, and render two Markdown files (resume.md and cover_letter.md) for review. Use when the user asks to tailor their CV, prep an application, or write a cover letter for a specific role.
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
   - Headline: the target role title and 1-2 strengths; no contact details.
   - Visa sponsorship: the CV header (from `master_resume.md`'s `location`) does not say "Requires visa sponsorship" by default;
     the user decides per application (often after a referral or a first conversation). Ask before adding it to `location` for that
     copy; the cover letter block `C13` states it either way. An ATS screening filter may reject on the phrase; a recruiter may want it.
   - Cover letter: 3-4 paragraphs from cover blocks and condensed STAR stories; mention sponsorship needs
     honestly if the role is abroad (block `C03`-style text if they have one).
4. **Validate:** `python tools/jd_check.py tailor <folder>`. Fix every error; never work around one.
   Warnings about heavy rewording mean you drifted from what the user actually did — tighten it.
5. **Render:** `python tools/render_resume.py <folder>` → **two files only, the user's rule**: `resume.md` and
   `cover_letter.md`. Master documents (career docs, stories) already exist and don't change per application;
   the folder holds nothing else the user must read (`tailored.json` and `validated.sha256` are the checker's own
   files). **No `resume.docx` unless asked or an application form needs a Word upload** (`--docx`, needs
   `pip install --require-hashes -r requirements-career.txt`). No `review.md`, no other extra documents.
6. **Review gate.** Run the `application-review` skill on this folder (ATS, recruiter and consistency
   subagents plus `tools/consistency_check.py`); its findings go to the user **in the chat, not in a file**. Fix or
   ask the user about every "fix before applying" finding, then re-validate and re-render. Skip only if the user
   says not to. If the user only asked for the CV, still build both files (they need both eventually), but lead
   with the CV.
7. **Hand over for review.** Show the user the diff the checker printed (what changed from their master
   CV), where the two files are, any JD must-haves their CV couldn't evidence, and the review verdict. They review, edit and
   apply themselves. Then offer to move the card to Shortlisted (`track`).
