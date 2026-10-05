---
name: rejection-review
description: After a rejection, read what it says about the search: compare the role's scored must-haves with the CV, the timing of the email, sponsorship and location, and other applications to the same company, then say what is worth changing. Use when a card moves to Rejected, when inbox-check finds a rejection, or when the user asks why a role was rejected.
---

# Rejection review: what does this rejection tell us?

A rejection is data, not a verdict. This reads what the files already hold and says what is likely and what is only a guess. **Read-only**: it
changes no card and sends nothing. The user decides every change.

## Steps
1. **Gather, without new board reads:** for each rejected ref, `work/jd/<ref>/score.json` (fit score, must-haves met/partial/missing, blockers, summary),
   `sponsorship.json`, the `data/matches.csv` row (title, location, posted), the stage log `data/pipeline_log.jsonl` (when it was applied and rejected),
   `state/application_mail.jsonl` (the rejection email and any referral email), and `profile/application_answers.json` (what was answered about
   sponsorship and relocation; read only those keys). If `jd.txt` has been trimmed by `jd_cleanup.py`, the score is enough.
2. **Timing:** days from applying to the rejection, and whether several rejections arrived within minutes of each other (one automated decision,
   not a per-role review) or after weeks (a person read it).
3. **Content:** which must-haves were partial or missing, and whether any blocker was flagged. A role scored apply with every stated requirement met was
   not rejected for its content. A stretch role (score under 70, a missing second domain) may have been.
4. **Filters:** the sponsorship need, the location, the number of applications to the same company in the same week, and whether a referral was attached.
   These are guesses; label them as such and say which one the evidence favours.
5. **Recurring gaps:** a must-haves gap that appears in several rejections or scores goes to `cv-review` as an input; never change the CV from one rejection.
6. **Report in chat, briefly:** a table (role, score, must-haves met, real gaps), the timing pattern, the most likely cause with your confidence, and one or
   two next steps (for example fewer simultaneous applications per company, a sponsorship answer to check, a gap for `cv-review`). Say what you could not know.

## Never
- Treat one rejection as proof the CV is wrong; contact the company or a person; reopen a card; change a master document from a rejection alone.
