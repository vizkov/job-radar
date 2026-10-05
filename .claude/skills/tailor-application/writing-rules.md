# Writing rules: CV, cover letter, stories, and each CV section

Read this before building or reviewing any CV or cover letter. The user's rule (2026-10-01): the three
documents have different jobs and must not read alike, and a CV reads as a CV, never as a chat message.
The rules come from the failures in this user's Amazon, Allianz and Meta drafts, checked on 2026-10-01 against current resume guidance
(Jobscan, Indeed, TealHQ, Monster, ResumeBuilder, Zety and similar; sources listed in section 6). Where the web disagreed with the user's own rule, the user's rule stands and the difference is noted.

## 1. The three documents: intent, voice, how they relate

| | CV | Cover letter | STAR stories |
|---|---|---|---|
| Job | Get shortlisted in a 6-second scan and pass the ATS | Make a human want to interview: *why this company, why me for it* | Let the candidate answer any interview question from the record |
| Reader | ATS, then recruiter | Hiring manager | The user, before an interview (never sent) |
| Voice | Telegraphic: verb-led fragments, no "I", no "we", no narrative | First person, connected prose, three or four paragraphs, one idea each | First person, full detail, honest about what was the team's and what was theirs |
| Content | Claim + result + scale; nothing that needs the next sentence to make sense | One or two proof points told as a short story, tied to *this* role and company; adds what the CV cannot (motive, judgement, how) | Situation, task, action, result, lesson, plus "Also true" facts and private notes |
| Never | Spoken phrasing and casual asides ("so I don't have a measured saving yet", "a lot", "much less", "really"): the user's rule, 2026-10-01, for every draft including application-form answers; state what was done in plain, specific prose, and a missing figure is simply left out; commentary on the work ("the X came afterwards"), hedges ("too new for measured results"), process asides, chatty clauses | A paragraph-by-paragraph replay of the CV; a claim the CV cannot back | Polish |

How they relate: the CV *claims*, the letter *argues* (one or two of those claims, with the reasoning), the
stories *prove* (every CV and letter claim traces to a story; the letter and CV never say more than the story
supports). A fact sits in the **most fitting document only**: a scope aside such as "my team stayed on web and API,
and mobile testing went to another team" belongs in a story or, when the role makes it relevant, in the letter
(cover block C25); a chronology aside ("the first threat model was delivered before the workflow existed") belongs in a story.
The same event can appear in all three, told for each one's job, in different words.

## 2. CV sections: purpose, shape, how each reads, what tailoring may change

**Tailored (only these four):** Profile, Key achievements, Experience, Skills.
**Static (never tailored, never cut, never reworded):** Projects and writing, Volunteering, Education (and the header's
contact line). They are copied from the master verbatim; the checker requires them. Fit the page by trimming the tailored
sections, never these.

**Profile** (P00-P04 and any P line under Summary; 2-3 sentences, about 40-60 words, three lines (the user, 2026-10-02: five lines was too long and repeated the achievements; `cv_lint.py` warns above 65)). **Tailored heavily, per role** (the user, 2026-10-01: the Profile is not
static like the other sections; it converges a lot on the particular role). Who you are for *this* job: title, years, domain, the two or three strengths the JD
asks for, your working level. Rewrite the P lines freely in the JD's own vocabulary (the checker only warns about heavy rewording here) as long as every
statement is backed by the master lines and the stories: no new facts, numbers, employers or tools, and no JD term the stories do not support. It is the first
thing read and the **main place to converge with the JD's vocabulary**: a JD term that does not fit naturally in an experience bullet or a skills row
("security by design", "risk-based decision making") goes here, in a sentence the user's stories support. Weave the JD's words into the user's own facts; never copy
whole sentences from the ad. No first person ("I", "my"), no objective statements, not a list of duties. The masters' P lines are raw material, not text to send.

**Key achievements** (P05-P10; 3-5 lines; each needs a number or a concrete outcome, otherwise it is an experience bullet). The career-defining *outcomes* the reader should remember even if they read
nothing else: what changed or what was found, at what scale, for whom, with the number if there is one. Outcome-first,
one or two lines, no method detail. They are **not** a second copy of the experience section: an event is told once in
full. The matching experience bullet carries the *how* (the method, the technical detail, who was involved), so the two
never share a sentence. If a selected achievement and an experience bullet say nearly the same thing, reword the bullet
toward method or drop it (keeping the role above its floor, section 4). The label ("Impact:", "Efficiency:") may be
reworded toward the JD's word where the line supports it.
**Length in a tailored CV (the user, 2026-10-02: the section was reading like a CV plus a cover letter).** The master keeps the full line; the tailored copy is a headline of **35 words at most** (`cv_lint.py` warns above 35, and the five together should stay near 150 words). **State the outcome only**: the finding or the result and its one proof of impact. How it landed (who was shown what, the demonstrations, the pushback) is method and belongs in the matching experience bullet, never in both; **drop the secondary clause** in this copy: a second proof point ("disproved assumptions in a previous vendor's review"), a recognition (RSUs, an award, a bonus) or a follow-on outcome ("the findings set the scope of the follow-on penetration testing"). A semicolon that joins a finding to a story about how it landed is the sign of a cover-letter sentence; keep it only when the second half is the outcome. Dropped clauses stay in the master and the story, so other roles can use them.

**Experience** (B lines; one block per role, reverse-chronological, bullets grouped by context). The *scope and method*:
what you were responsible for and what you did, then the result where the line has one. Verb first, past tense for
finished roles (and finished events in a current role), present tense only for what is ongoing. Bullets that share a
context stay together (all the bank's bullets, then the other client's; never interleave). Per role keep enough depth to
show the role (section 4).

**Skills** (K lines; always all seven rows: Application security, Vulnerability management, Threat modelling, AI security,
Cloud security, Tools, Languages). The row headings are static (all seven, never dropped or renamed). Tailoring may reorder items inside a row (JD-relevant first), drop items the JD
does not want, and reword an item toward the JD's own term where the stories back it (the user, 2026-10-01: "update the skills themselves to converge if needed"); converged items live in the draft only, never in the master. It may not add an unbacked skill. Items are **nouns of
competence**: techniques, standards, tools, languages. Not approach phrases, sentences or claims: "security by design",
"federated and shared-responsibility architectures", "agent and MCP tool permissions" are experience or profile language, not
skills. Do not list a skill its parent already covers ("authentication and authorisation testing" sits under OWASP Top 10).
Mirror the JD's exact words for genuine skill nouns and tools (ATS match on exact phrases, and a dedicated skills block carries weight). Put the core, most-asked items first (secure code review, secure design review, SAST/DAST, business-logic testing before
the long tail). Capitalisation: every word of a row label and of an item starts with a capital letter (Secure Code Review, Bug Bounty Triage, Business-Logic Testing, AWS, Burp Suite; the user, 2026-10-02, replacing 2026-10-01's first-letter-only rule; the short joiners and/for stay lowercase); the masters carry it, so it is not linted (the user: update the masters and nothing has to be caught); items inside a parenthesis are capitalised the same way (MCP Plugins) except acronyms and file names (HTTP, Node.js). Separators: commas; a language is listed on its own (`JavaScript, TypeScript (Node.js)`, not
`JavaScript/TypeScript`).

**Header.** Name, headline, location, email, phone, LinkedIn, GitHub. **The headline is static (the user, 2026-10-05): master `P00` verbatim, never tailored per role.** Location reads `Bangalore, India · Open to relocation`
(no destination, in every copy). Blog links live in the Projects entry, not in the header.

## 3. Register: how a CV line must read

1. **Fragment, not conversation.** One fact per sentence, no asides, no "also", no "so that ... and with ..., this could".
   If a line needs three clauses to be understood, split it or cut a clause; never stack them.
2. **No meta-commentary.** A CV does not explain its own evidence or admit its limits: no "(too new for measured results)",
   "the X came afterwards", "from other teams" caveats, "my own team", "as stated above". If a limit matters, the
   stories carry it.
3. **Impact, not attendance.** "Briefed the VPs" says you were in a room. Say what the room did: "Walked the Payments
   Senior VP and AppSec VPs through the chain with live exploit demonstrations, which turned the bank's pushback into
   acceptance." A verb of communication needs its outcome or audience-level effect.
4. **Numbers once, plain.** "around 50% less triage time", not "from about a day to about half a day (around 50% less ...)".
   No "about / around" stacked twice, no duplicated units. Counts in a parenthetical only when they are the point.
5. **Tense.** Finished = past. Ongoing = present ("Lead", "Provide"). One tense per bullet; a role that has ended has no
   present-tense bullets. "Having onboarded" for finished onboarding, "onboarding" only while it is in progress.
6. **No repeated phrase** within a bullet, a section or a page ("by the end ... by the end of the engagement"). Reword the
   second. Also no pet phrases reused across neighbouring bullets ("end to end", "across"). The Profile is read as one paragraph: no
   phrase may appear in two of its lines ("large-scale systems" twice, the user, 2026-10-02); `cv_lint.py` warns (`cross_line_repeats`).
7. **Strip what is implied.** "my own team", "(from other teams)", "the client's development teams confirmed" when
   "confirmed exploitable" is enough. Keep qualifiers only where dropping them makes the claim false.
8. **Precise words.** `expedited deadline`, not `extended`, where that is what happened; "go-live fast approaching" for
   urgency. Use the user's own term for a fact, never the near-synonym.
9. **Punctuation and form.** **Key achievements start with a capital after the label (the user, 2026-10-05: "Chained logic flaws: found" sat beside "AI security: Found" and nobody caught it); `cv_lint.py` now errors on a mix, and when you relabel a master achievement, copy its capital.** No dangling hyphen pairs ("passenger- and customer-data": write "passenger and customer data");
   no mixed list styles in one section (capitalisation, separators, ending full stops: decide once per section and keep it);
   no "(RAG)"-style acronym glosses in prose where the acronym is a skill (it lives in Skills); spell out an acronym once
   only if the reader may not know it; British spelling throughout (the user's documents use it); no double spaces; en dash
   for ranges; a line is a sentence or a fragment, not both.
10. **Self-contained.** Every bullet reads alone: "the bank" / "the client" needs its referent introduced earlier in the same
    document.
11. **Dates** only on job titles (education and volunteering years are exempt and stay).
12. **No first person in CV lines** (no I, me, my, we, our; the user's rule, 2026-10-01): the fact belongs in the letter or the stories. No exceptions (B16 was reworded 2026-10-01).
13. **Links.** Every mentioned publication or repository has a clickable link in its entry.
15. **One verb form in the Profile (the user, 2026-10-01).** The Profile sentences use one form throughout (here: third-person present, "Tests ..., provides ..., leads ..."); never "Hands-on in ..." next to "Provides ..." next to "Currently leads ...". The copy editor checks it.
16. **No mechanism and no context clauses in a CV line (the user, 2026-10-01).** A CV line says what was done and what came of it. How a flaw works ("one token served the GPT layer, so a token meant only for ... also opened ...") belongs in the story or the letter, and so does background ("as the global practice moves there"). If dropping a clause leaves the claim and its impact intact, drop it.
17. **Skills: genuine skill nouns only, related items grouped in parentheses (the user, 2026-10-01).** Testing areas that a parent term covers ("authentication and authorisation testing", "microservice testing") do not go in Skills; JD terms like these converge in the Profile. A sub-technology goes inside its parent's parentheses (RAG inside "LLM-assisted security workflows (LLMs, skills, MCP plugins, RAG)"), and a tool lives in Tools (AWS Threat Designer is a tool, not a threat-modelling technique).
18. **A capability that Skills already names need not be repeated as an Experience bullet (the user, 2026-10-01).** B15 keeps only the workshop; "network penetration testing" is carried by K01. Recruiters then see one clear claim, not two.
14. **Name the thing, not the category (the user's rule, 2026-10-01, from recruiter advice on ATS matching).** A keyword screen matches exact phrases from the
    ad, so write the platform, tool, standard or language where the work happened ("automated exploit revalidation in Python", "Checkmarx", "OWASP Top 10"), not
    "scripting ability", "scanning tools" or "familiar with frameworks". A bullet reads verb + named tool + object ("Automated exploit revalidation in Python"), and a
    certificate is named in full. `cv_lint.py` warns on the vague phrases. **Only names the stories back:** advice written for other candidates (Splunk,
    CrowdStrike, MITRE ATT&CK, Jira, Security+ ...) is a pattern, never a list to paste. If an ad names a tool, standard or certificate the masters don't mention,
    do not add it: list it in the hand-over and ask the user whether they have really used or hold it; if yes it goes into `stories.md` as an "Also true" line first.
    The converse: no soft-skill filler ("team player", "strong communication", "detail-oriented", "passionate about"): the claim filters nothing and proves nothing;
    the evidence (a result with a number or an audience) does the job. `cv_lint.py` warns on the common phrases in Profile, bullets and Skills.
    Keyword matching ranks and searches more than it auto-rejects: never bend a fact to chase a term.

## 4. Tailoring limits (so a good JD match does not gut the CV)

- **Depth.** Each role keeps at least 3 bullets and at most 5, or all of its master bullets if the master has fewer (Senior
  Associate: 2). **No relevant bullet is dropped (the user, 2026-10-02, after B11 was cut from the Amazon CVs although the ad's duties fit it):** a role keeps every master bullet unless the line matches nothing in the JD at all, and the cut is recorded with its reason in `tailored.json` (`"dropped": {"B11": "no JD match: ..."}`); `cv_lint.py` errors without it. A role whose master has more than 5 bullets may drop down to 5 freely. Cut inside a role by shortening wording, never by losing a relevant line; never the line that
  names the role's distinct contribution (for Senior Associate: the thick-client white paper).
- **Taper with recency (the user, 2026-10-02, after research: bullets per role fall as the role gets older).** The most recent role gets the most (4 to 5, up to 6 when it is the best match), the next 3 to 4, older roles 2 to 3, within the floor and cap above. A more recent role never carries fewer bullets than an older one while its master has more to give. The taper never justifies dropping a relevant bullet: it only decides which role gets the extra space when a master has more than 5. `cv_lint.py` warns when an older role has more bullets than a more recent one that could carry more.
- **Two pages.** Fit by, in order: shorten wording in tailored sections; drop a bullet that restates a Key achievement
  (while the role stays above its floor); drop the least relevant bullet above the floor. Never cut a static section,
  a skills row, or a role. Tell the user exactly which lines went.
- **No approved content is changed to fit the page** (spacing is fixed in `tools/render_pdf.py`).
- **Convergence terms live in the tailored draft only, never in the masters** (the user's rule, 2026-10-01: the masters cannot carry every term
  from every role; that is the tailor's job). The master stays the honest, polished, untailored record. The tailor may use a JD term where the
  user's stories back it, and lists every converged term in the hand-over. A term the stories do not back stays missing.
- **Convergence order:** JD vocabulary goes in Profile first, then bullets where the work really is that, and
  into a Skills row only when it is a genuine skill noun. A term that does not fit any of the three is left missing and
  listed in the hand-over.

## 5. Checking

`tools/cv_lint.py` (run by `jd_check.py tailor` and by `master-update`) finds the mechanical violations of sections 2-4.
The fourth reviewer of `application-review` (the copy editor) reads for everything the lint cannot: tone, tense, register,
repetition, awkward constructions, whether a section is doing its job. Both run on every application and on every master change.

## 6. Sources checked on 2026-10-01 (and where they agree or differ)

- Key achievements block: 3-5 bullets, pulled from across a career, quantified; "if you can't attach a number or a concrete outcome it belongs in
  the experience bullets" (ResumeBuilder, Indeed, TopResume). Adopted. Experience: 3-5 bullets per role, action verb first, mostly achievements (TealHQ, Adobe). Adopted (floor 3, cap 5).
- Summary: 3-5 sentences or about 50-100 words in the sources (the user shortened it on 2026-10-02 to 2-3 sentences, about 40-60 words), job title and years first, two or three strengths that match the job, JD keywords without
  copying sentences, third person without I/me/my (Jobscan, Indeed, MyPerfectResume). Adopted.
- Skills: group by label plus comma-separated list; 3-6 categories; about 12-20 skills is the sweet spot; mirror the JD's exact phrases
  (Resume Worded, Interview Guys). Adopted except: the user keeps all seven rows and a longer list, and approach phrases stay out of Skills
  (their rule wins; exact-phrase mirroring applies to skill nouns and tools).
- Cover letter: narrative paragraphs, 2-3 paragraphs suggested, connects the most relevant achievements to the employer's needs and adds
  motivation and context the resume cannot (Monster, Zety, Kickresume). Adopted; this user's letters keep 3-4 paragraphs on one page.
- STAR stories are not a submitted document: they are interview preparation (spoken answers), so they are the fullest and most candid of the three.

## 7. Decided by the user: reviewers and tailors must not re-flag or "fix" these

Give this section to the copy editor only; the cold readers (ATS, recruiter, auditor) never see it. They must not re-propose rewrites of these choices; they may still report a decided line that causes a factual contradiction or a new problem. Problems no rule covers are never dropped: they are reported as "No rule yet" and the main session brings them to the user, who decides whether they become a rule.

- "with go-live fast approaching" (B06): the user's wording for urgency. P05 was reworded on 2026-10-02 to the outcome only ("Found four chained attack vectors in ... payment settlement platform; all accepted as high-severity risks and fixed before go-live").
- "expedited deadline" (S02, C10), never "extended" (B12 was removed from the master on 2026-10-02; the story stays).
- "around 50%" triage saving stated once ("onboarding its first set of assessors" was cut from P09 and B03 on 2026-10-02).
- Skills rows, labels and item wording (K01-K07) as set on 2026-10-01: all seven rows kept, `JavaScript, TypeScript (Node.js)`, no approach phrases, every word capitalised (2026-10-02). Do not rewrite the lists or drop rows.
- E01 "graduate coursework, focused on adversarial AI/ML" (no degree is claimed; do not add one).
- B17 opens with the clickable name "OSS" (link text, not the raw URL; 2026-10-01); B06, B17, B18, B21 shapes and lengths (B06 and B21 stay single bullets); both B18 links point to the Medium profile (the user's choice).
- Role headings name every employer (Consultant: Synopsys / Black Duck / UltraViolet Cyber): the user's choice, for ATS and recruiter lookups.
- Role-heading dates only on titles; education and volunteering years stay.
- "Fortune 100 global financial and banking institution" is the defined term; "the bank" is used after it is introduced in the same document (tailoring fixes dangling referents, not the master).
- The masters carry no JD-specific terms (e.g. "security by design"); converged terms appear in tailored drafts only.
- **Cover-letter blocks open with the challenge (the user, 2026-10-05, after the cover-letter research).** Each of the three labelled blocks (C03, C08, C10) says what made it hard first, then what you did, then the result, and carries two instances where the record has two. C01 is the one dynamic opening, "With 6+ years in application security, I have extensive experience in {need}, {need} and {need}", where the needs are what the role asks for in your own words (never the ad's sentences), so it says who you are and why this role in one; C12 gives the reason for this role with the evidence first; the closing names the role's work, not "contribute to the team". The letter adds detail the CV does not carry and never repeats the CV's title, years or current role.
- **Cover-letter content rules (the user, 2026-10-05).** (a) **Reword the ad, never copy it.** Keep the intent and drop the ad's sentence (ad: "identify logic flaws, chained vulnerabilities and access control weaknesses that automated tooling does not surface" becomes "find niche vulnerabilities that common tooling misses"); skill nouns and tool names stay as written because ATS matches them, but no phrase of a sentence from the ad goes into the letter, the opener included. (b) **No sub-bullets in a letter**: it is a fast read, not a report; `cv_lint.py` errors on an `(optional)` block in a letter. (c) **The letter expands the CV (the user, 2026-10-05)**: the same situations the CV carries, with the situation, the challenge, the approach and the outcome the CV bullet leaves out; never CV wording, and never a situation the CV does not carry (the "other situations" blocks need the user's word). `profile/career/cover_blocks.md` is a ranked bank for this: each block names its CV anchor and what the CV leaves out; prefer the lowest rank number. (d) **"Why this company" is about the company and the role**, not the user's current employer or role. (f) **The reader is a recruiter, not an engineer (the user, 2026-10-05)**: plain language, no unexplained technical terms (not "blind SSRF" or "attack surface": say what it meant); the CV keeps the technical terms. (g) **Outcomes close the paragraph**, like every other block, and say what the work achieved (a deadline met, flaws fixed before launch), not only that it was praised. (h) **Each bullet also conveys the user's intent (the user, 2026-10-05)**: one clause saying what you were trying to protect or achieve and why, taken from the story's Task and Lesson lines ("I judged all three would leave a critical system exposed", "evidence and a clear walkthrough are what make that land"), so the point reads as how you work and what the employer gets, not only as an event. Never invent an intent the story does not record. (j) **Three more letter rules (the user, 2026-10-05, agreeing to the copy editor's proposals):** a fact appears in one chosen block only (when two chosen blocks share a fact, cut it from the lower-ranked one; e.g. the trial-to-annual-contract move sits in both C36 and C11); no sentence over 40 words (`cv_lint.py` errors; split a sentence that lists more than three items); put the intent clause before the action and let the outcome close the block. (i) **Run-in labels are per letter (the user, 2026-10-05)**: master cover blocks carry no titles, because one block can serve several angles; they list candidate `labels`. Set `"label"` on each body block in `tailored.json` to the need it answers in this letter (e.g. the same words as the opening); `cv_lint.py` errors when it is missing. (e) **Delivering under pressure shows impact fast** (the outcome, in the first lines), is short, and may carry a second instance in one sentence.
- "Bangalore" is the city spelling everywhere (header, role lines, letters). Sponsorship stays out of the CV header (per-application choice, stated in the letter). The letters' structure (run-in block labels, "What I would bring to the team:", greeting) is the user's own cover-letter design: do not change it.
- Skills items may converge to JD terms in drafts (see section 2); row headings stay.
- The RSUs are not on the CV (2026-10-02: stories and cover letters only), and B10 says the user "won the Synopsys ACE Award for Customer Focus" without "with the team" (the award was the team's, 2022; the user will say so if asked). Do not flag either again.
- B05 "quality assurance of every deliverable" for the bank team of 4, and B14 "communicating risks effectively to stakeholders" (2026-10-02): the user stands by the wording and will explain it from the stories if asked. Do not flag again.

## 8. Already answered in earlier sessions (main session: check `stories.md` "Also true" lines before asking the user anything)

The user said (2026-10-01) that re-asking these wastes their time. Reviewers without context will keep raising them; verify against the stories, and answer from the record.

- The timeline of technical oversight (8 assessors mid-2025 to mid-2026, bank team of 4 from August 2026), quality assurance and performance reviews for the bank team, the 100+ assessments and who highlighted what, the renewals and the account timeline: `stories.md` S01, S09 "Also true".
- The live exploit demonstrations (the VPs saw them; "where useful" was dropped 2026-10-01), the previous vendor's review, "6+ years": the user's approved wording; not open questions.
- "Interviewed 10+ candidates" was removed (no story; 2026-10-01). Do not re-add it.
- Around 50% triage saving: accepted as written.
- K03 starts with the US spelling "Threat modeling" beside the British row label "Threat modelling" (2026-10-02, the user's decision after the ATS reader found exact-phrase "threat modeling" missing). It is the one deliberate exception to British spelling, and a tailored K03 keeps the US item somewhere in the row. Do not flag it as a stutter or a spelling error.
