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

**Profile** (P00-P04 and any P line under Summary; 3-5 sentences, roughly 50-100 words). **Tailored heavily, per role** (the user, 2026-10-01: the Profile is not
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
the long tail). Capitalisation: lowercase, except proper nouns and acronyms (AWS, OWASP Top 10, Burp Suite, Java), every
item, including the first in a row. Separators: commas; a language is listed on its own (`JavaScript, TypeScript (Node.js)`, not
`JavaScript/TypeScript`).

**Header.** Name, headline, location, email, phone, LinkedIn, GitHub. Location reads `Bangalore, India · Open to relocation`
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
   second. Also no pet phrases reused across neighbouring bullets ("end to end", "across").
7. **Strip what is implied.** "my own team", "(from other teams)", "the client's development teams confirmed" when
   "confirmed exploitable" is enough. Keep qualifiers only where dropping them makes the claim false.
8. **Precise words.** `expedited deadline`, not `extended`, where that is what happened; "go-live fast approaching" for
   urgency. Use the user's own term for a fact, never the near-synonym.
9. **Punctuation and form.** No dangling hyphen pairs ("passenger- and customer-data": write "passenger and customer data");
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
  Associate: 2). Cut inside a role by shortening wording before dropping a bullet; drop from the tail of the role first, never the line that
  names the role's distinct contribution (for Senior Associate: the thick-client white paper).
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
- Summary: 3-5 sentences or about 50-100 words, job title and years first, two or three strengths that match the job, JD keywords without
  copying sentences, third person without I/me/my (Jobscan, Indeed, MyPerfectResume). Adopted.
- Skills: group by label plus comma-separated list; 3-6 categories; about 12-20 skills is the sweet spot; mirror the JD's exact phrases
  (Resume Worded, Interview Guys). Adopted except: the user keeps all seven rows and a longer list, and approach phrases stay out of Skills
  (their rule wins; exact-phrase mirroring applies to skill nouns and tools).
- Cover letter: narrative paragraphs, 2-3 paragraphs suggested, connects the most relevant achievements to the employer's needs and adds
  motivation and context the resume cannot (Monster, Zety, Kickresume). Adopted; this user's letters keep 3-4 paragraphs on one page.
- STAR stories are not a submitted document: they are interview preparation (spoken answers), so they are the fullest and most candid of the three.

## 7. Decided by the user: reviewers and tailors must not re-flag or "fix" these

Give this section to the copy editor only; the cold readers (ATS, recruiter, auditor) never see it. They must not re-propose rewrites of these choices; they may still report a decided line that causes a factual contradiction or a new problem. Problems no rule covers are never dropped: they are reported as "No rule yet" and the main session brings them to the user, who decides whether they become a rule.

- "with go-live fast approaching" / "found with go-live fast approaching" (P05, B06): the user's wording for urgency.
- "expedited deadline" (B12, S02, C10), never "extended".
- "around 50%" triage saving stated once; "onboarding its first set of assessors" (still in progress, present tense; "first set" is deliberate, no count).
- Skills rows, labels and item wording (K01-K07) as set on 2026-10-01: all seven rows kept, `JavaScript, TypeScript (Node.js)`, no approach phrases, lowercase items. Do not rewrite the lists or drop rows.
- E01 "graduate coursework, focused on adversarial AI/ML" (no degree is claimed; do not add one).
- B17 opens with the clickable name "OSS" (link text, not the raw URL; 2026-10-01); B06, B17, B18, B21 shapes and lengths (B06 and B21 stay single bullets); both B18 links point to the Medium profile (the user's choice).
- Role headings name every employer (Consultant: Synopsys / Black Duck / UltraViolet Cyber): the user's choice, for ATS and recruiter lookups.
- Role-heading dates only on titles; education and volunteering years stay.
- "Fortune 100 global financial institution" is the defined term; "the bank" is used after it is introduced in the same document (tailoring fixes dangling referents, not the master).
- The masters carry no JD-specific terms (e.g. "security by design"); converged terms appear in tailored drafts only.
- "Bangalore" is the city spelling everywhere (header, role lines, letters). Sponsorship stays out of the CV header (per-application choice, stated in the letter). The letters' structure (run-in block labels, "What I would bring to the team:", greeting) is the user's own cover-letter design: do not change it.
- Skills items may converge to JD terms in drafts (see section 2); row headings stay.

## 8. Already answered in earlier sessions (main session: check `stories.md` "Also true" lines before asking the user anything)

The user said (2026-10-01) that re-asking these wastes their time. Reviewers without context will keep raising them; verify against the stories, and answer from the record.

- The timeline of technical oversight (8 assessors mid-2025 to mid-2026, bank team of 4 from August 2026), quality assurance and performance reviews for the bank team, the 100+ assessments and who highlighted what, the renewals and the account timeline: `stories.md` S01, S09 "Also true".
- The live exploit demonstrations (the VPs saw them; "where useful" was dropped 2026-10-01), the previous vendor's review, "6+ years": the user's approved wording; not open questions.
- "Interviewed 10+ candidates" was removed (no story; 2026-10-01). Do not re-add it.
- Around 50% triage saving: accepted as written.
