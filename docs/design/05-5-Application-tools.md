# 5.5 Tools: job descriptions, checks and application documents

**What this is:** The tools behind scoring and tailoring: fetching job descriptions, validating Claude's scores and tailored text, rendering the CV and cover letter, and the consistency, drift and outcome checks.  
**Read first:** [4. A Claude session](04-Claude-session.md)  
**Code:** `tools/jd_prep.py`, `jd_check.py`, `render_resume.py`, `render_pdf.py`, `draft_experiment.py`, `inbox_outcomes.py`, `master_drift.py`, `cv_lint.py`, `consistency_check.py`  

Part of the [5. Code reference](05-Code-reference.md) (the index of every file and function).

---

## `tools/jd_prep.py`: fetch job descriptions

Walkthrough: [4.3](04-Claude-session.md). It turns a `matches.csv` row into a job-description packet in `work/jd/<ref>/`. The ATS scraper's text is used only if it is at least 200 characters; otherwise it falls back to the page. `--refresh` re-fetches even when `jd.txt` exists.

Getting the text:

| Function | Does |
|---|---|
| `html_to_text()` | Main text of an HTML page, without nav and scripts. |
| `_as_text()` | An HTML fragment to text; plain text passed through trimmed. |
| `via_scraper()` | The ATS scraper's description; `None` if the row has no ATS, slug or external id. |
| `job_api()` | Public per-job APIs for Greenhouse, Apple and EURES. `_greenhouse_text()`, `_apple_text()` and `_eures_text()` turn each JSON reply into text; `_EURES_PAGE` matches EURES portal links. |
| `public_url()` | Amazon's login-walled links to the public page. |
| `jsonld_description()` | The description from a page's JSON-LD `script` tag. |
| `Fetcher` | `_allowed` (robots.txt cache) and `fetch` (the ordered fallbacks). |

Choosing roles:

| Function | Does |
|---|---|
| `load_rows()` | The rows of `data/matches.csv` that have a ref. |
| `scored_refs()` | Refs already in `data/scores.jsonl`. |
| `select()` | The named refs, or else recent roles of the wanted tiers that are not yet scored, once each. |

Language check and the packet:

| Function | Does |
|---|---|
| `allowed_languages()` | The user's working languages (config `languages`). |
| `detect_language()` | The ad's language, by stop-word counts. |
| `language_requirements()` | Languages the ad asks for, required or optional. |
| `language_line()` | The "Language check" line in every packet. |
| `render_packet()` | The packet text: role facts, JD status, language line, then the JD wrapped as untrusted data and cut to `MAX_CHARS`. |
| `prepare()` | Writes `jd.txt`, `meta.json` and `packet.md`. |
| `main()` | The CLI. |

## `tools/jd_check.py`: validate Claude's output

Walkthrough: [4.3 and 4.4](04-Claude-session.md). `check_score()`, `upsert_score()`,
`cmd_score()` (the `score` action: reads `work/jd/<ref>/score.json`, validates it with `check_score()`, upserts the record into `data/scores.jsonl`, and with `--board` sets Fit, Recommendation and the fit section on the card); `new_names()` (capitalised words and acronyms not in the career docs),
`_planted()` (URLs/emails/phones the user didn't write), `check_tailor()` (with the inner
`check_line()`), `_digest()` (SHA-256 hex of a file's bytes, written as the `validated.sha256` stamp), `cmd_tailor()` (the `tailor` action: reads `tailored.json`, refuses if the masters are not cleared or the check finds errors, prints each bullet against its master line, and on success writes the stamp), `main()`. Helpers: `_norm()` (lower-case,
collapse whitespace; all comparisons use it), `_NUM` (numbers), `APPS`
(`profile/applications/`). `cmd_tailor()` deletes any old `validated.sha256` **before**
checking, so a failed check never leaves a stale stamp.

`recommendation_cap(fit, blockers, sponsor)` is the recommendation-band rule that `check_score()` applies: **apply** at fit 70 or more (`APPLY_MIN`), **maybe** at 50-69 (`MAYBE_MIN`), **skip** below 50 or with any blocker; a sponsorship verdict of `unlikely` caps at maybe and `no` at skip. Judgement (scope risk, seniority) may only lower the recommendation, never raise it, so a higher one is rejected. `LEVELS` (`below`, `at`, `above`) are the allowed values of the optional `level` field; `below` lowers the fit ceiling by `LEVEL_PENALTY`. Why: the same-looking score was apply on one role and maybe on another.

The `score.json` and `tailored.json` contracts are on page 4, [4.3](04-Claude-session.md#43-scoring-a-role-score-roles) and [4.4](04-Claude-session.md#44-tailoring-an-application-tailor-application).

**Watch out**: `_NAME`'s lookbehinds skip the first word of a sentence, which is
capitalised anyway, so "Led the review" doesn't flag "Led" as a new name.

## `tools/draft_experiment.py`: the tailored draft against an Opus draft, before any PDF

Step 4b of `tailor-application`. `prep <folder>` renders only the text of the validated tailored draft (`render_resume.py --text-only`, no PDF) as draft **A** in
`work/apps/<folder>/experiment/` and writes one brief file per agent: an Opus writer (draft **B**, from the job description plus `profile/career/`) and the four readers of
`application-review` (ATS, recruiter, consistency auditor, copy editor; their personas are read from `personas.md`, the copy editor also gets `writing-rules.md`). `--with-ad-only` (only on
the user's request) adds draft **C**, an Opus draft from the ad alone with placeholder facts; it was dropped from the default after two runs in which it gave nothing the session could
use. The writer runs as part of tailoring without asking (`prep` only writes files); the four readers start only after the user says yes, once for the drafts and once for the PDFs
(CLAUDE.md rule 12). The session spawns every agent with one line, "Read and follow <brief path>", so no long prompt passes through the conversation. The readers see the drafts under
letters and are not told which is the tailored one; each writes its report next to the drafts and replies with it. `pdf <folder>` (run after the writer has written draft B) renders A's real PDFs and B's sample PDFs (`experiment/pdf_B`, never leaves the scratch folder) and converts both to text with `pdftotext` so the readers judge structure as well as content; a CV-only application (no `cover_letter` in `tailored.json`) renders and reads no letter. `status <folder>` lists which files exist. The session then fixes A (only
what the stories and rules back), validates, renders the PDFs, and runs the same checks and the four readers again on the PDFs. Why: two real applications (Anthropic, Cloudflare)
showed the tailored draft carried claims the stories did not support and phrases that echoed the ad; the readers' reports are judgement, so every finding is checked against the stories first.

## `tools/render_resume.py`: CV and cover letter files

`contact_line()` (email, phone, location and links joined with " | "), `to_markdown()` (CV as Markdown: name, contact line, bold headline, one `##` section per heading with bullets, and a Skills section unless one is already there), `cover_letter()` (the letter text: "Dear Hiring Manager,", the `cover_letter` paragraphs, "Kind regards,", the name), `to_docx()` (python-docx: title,
contact line, headline, one heading per section, bullet list, skills), `main()` (refuses
unless `validated.sha256` matches the current `tailored.json`). By default it writes only `resume.pdf` and
`cover_letter.pdf` (via `tools/render_pdf.py`, in the next section of this page) and puts the Markdown in `work/apps/<folder>/` (`SCRATCH`) for the
reviewers; `--md` also writes it into the application folder, `--docx` adds the Word file. With no Chrome or Edge it
falls back to Markdown in the folder.

## `tools/render_pdf.py`: the CV and cover letter as PDFs

Called by `render_resume.py` (the default). No LLM, nothing to pip install: HTML is printed to PDF with headless Chrome or Edge (`find_browser()`, `print_pdf()` with a throwaway user-data dir so an open browser doesn't interfere). `resume_html(data, career, contact)` takes the **tailored text** and the **structure from the master CV**, so the PDF cannot show a date or employer the master doesn't have.

To change the look, change `CSS` and the `@page` rules:

- CV: Roboto (the files in `tools/fonts/`, SIL OFL, inlined into the page so a render needs no network), A4, 43 pt side margins, black headings with a rule under each, teal `#0f766e` only on links, skill category names and bold words in list items, thin rules between roles, a heavier rule under the header, no "Profile" heading, 9.6 pt body at a 1.43 line height, right-aligned city and dates. Phrases in `tailored.json` `highlight` are bold in Key achievements; hyphenated words never break (`keep_hyphens()`), because a text extractor joins the halves; `cv_company_summary: false` in `profile/config.json` omits the company's one-line description (`without_company_summary()`).
- Cover letter: US Letter, 54 pt margins, 10.5 pt at 1.5.

Small helpers:

| Function | Does |
|---|---|
| `all_names()` | Turns "X (formerly part of A, then B)" into "X / A / B". |
| `smart_title()` | Title-cases a phrase but keeps acronyms, mixed case and small words like "and". |
| `short_link()` | Strips `https://www.` and a trailing slash for display. |
| `split_label()` | Splits "Label: text" into its two parts (empty label if no colon). |
| `header_html()` | Builds the name, headline, contact lines and rule. |
| `role_and_company()` | Looks up a ref's title and company in `data/matches.csv`. |
| `pretty_headline()` | Turns the tailored headline into the design's middot line. |

Building the pages:

| Function | Does |
|---|---|
| `experience_structure()` | Groups every `B` line by its master heading (company block with city and dates, roles under it; a four-part heading `Title — Company — City — Dates` is its own company). |
| `resume_html()` | `P` lines under "Summary" become the profile paragraph, "Key achievements" lines get their bold label, the tailored `K` lines (a `Skills` section in `tailored.json`; every master `K` line if none were chosen) become the skills grid, `E` and volunteering lines get right-aligned years. |
| `cover_html()` | Merges `C01`+`C02` into the opening, lists the middle blocks as bullets titled from their master heading (an "(optional)" block becomes a sub-point of the block before it), puts `C12`-`C14` after them; the role title and company come from `data/matches.csv` by the key. |
| `render_pdfs()` | Writes `resume.pdf` and `cover_letter.pdf`. |

All text is HTML-escaped. **Watch out:** the design is two pages for the CV and one for the letter; the tailoring skill trims low-value lines to fit, and the renderer never shrinks the type.

## `tools/inbox_outcomes.py`: applications awaiting an answer, and an outcome-email classifier

Used by the `inbox-check` skill ([4.10](04-Claude-session.md)). No mailbox access and no LLM. `pending()` lists refs in Stage Applied or Interview
(`latest_stages()` overlays the stage log on `data/pipeline_snapshot.json`; `applied_dates()` gives the date each moved there) with a Gmail
search string; `classify()` matches phrase rules in the order rejection, offer, referral ("X has referred you"), interview, acknowledgement (unknown otherwise); `seen_ids()` and
`add_seen()` keep `state/inbox_seen.json`; `main()` is the CLI (`pending`, `classify`, `seen`, `checked`).

## `tools/inbox_hook.py`: inbox-check bookkeeping without the model

A PostToolUse hook for the Gmail read tools, wired in `.claude/settings.json` (standard library only; always exits 0, prints nothing, so it can never block a session).
`handle()` reads the hook JSON: for `get_thread`/`get_message` it adds every message and thread id in the result to `state/inbox_seen.json` (`opened_ids()`); for `search_threads` whose query
is `"<Company>" ...` for exactly one company with an application awaiting an answer (`company_of()`), it stamps that role as checked today in `state/inbox_checked.json`. Broad or multi-company
searches stamp nothing. Only ids and a date are stored, never mail text.

## `tools/fetch_application_mail.py`, `tools/app_mail.py`, `jobradar/application_mail.py`: the application-mail ledger

The user kept missing replies, so the scheduled run now watches the mailbox for them ([4.10](04-Claude-session.md)). Three standard-library-only files:

- `jobradar/application_mail.py` (no secrets, imported by the password-holding step): `targets()` lists roles whose card is Shortlisted, Applied or Interview
  (`latest_stages()` overlays the stage log on the committed snapshot; Shortlisted is included because the receipt is often the first sign the user applied);
  `candidate()` is the header-only filter (recruiting-system senders: `is_ats()` matches whole domain labels, a domain in `ATS_DOMAINS` or a subdomain such as `hire.` or `recruiting.`, never a substring; or the company named in the sender or subject; sign-in codes
  and password resets in `NOISE_SUBJECT`, job-alert senders and bulk mail with `List-Unsubscribe` are skipped); `resolve()` ties an email to a role:
  `exact` (the role's full title is in the text, longest title wins), `company` (only one watched role at that company), `ambiguous` or `none`.
- `tools/fetch_application_mail.py` (run `python -I -S` before `pip install`, the second step that sees the mailbox password): read-only `EXAMINE` of All Mail,
  `BODY.PEEK[]`, headers first, then Gmail's thread id and the first 2,500 characters of text for candidates only (capped at 120 a run). Writes
  `.app_mail/messages.json` and `_status.json` (never committed); a failure is reported, never raised.
- `tools/app_mail.py` (no secret): `ingest` classifies those messages (`classify_mail()` reuses `inbox_outcomes.classify`; a receipt-like subject
  keeps a receipt a receipt even when its body mentions interviews; only an invitation to speak or schedule counts as a `strong` interview) and appends
  new ones to `state/application_mail.jsonl`: sender address, subject, date, thread id, type, matched role. **No message text is stored.** It also writes
  `state/application_mail_status.json` (the scan's health). `plan()` sorts unhandled mail into `auto` (an exact-title rejection, an interview invitation or an
  offer tied to one role: the session makes the move and tells the user), `ask` (a rejection that is not an exact match, a receipt for a card still
  Shortlisted, an unmatched offer: wait for the user's yes), `action` (assessments, scheduling, anything the user must do) and `info` (receipts and
  referral notices from the last 3 days). `ack` appends an acknowledgement row so an item stops being listed; `status` prints the scan's health line (`scan_status()` reads `state/application_mail_status.json`). The fetch reads headers of the newest 600 messages in the window (`MAX_SCANNED`) and bodies of at most 120 candidates (`MAX_CANDIDATES`). `brief_lines()` and `scan_line()` feed the
  session brief (`MAIL` lines and the CADENCE line for the scan).

**Watch out:** the Action cannot move board cards (its token cannot reach the Project), so the ledger is acted on in the next session. The
snapshot the Action reads is only as fresh as the user's last push, which is why Shortlisted roles are watched too.

## `tools/cover_sync.py`: the cover blocks follow the stories and CV lines

Each cover block in `profile/career/cover_blocks.md` has a metadata comment naming the CV lines (anchor) and stories (sources) it expands. `jobradar/career.py` fingerprints those lines (`cover_blocks_stale`, `record_cover_sync`, `cover_sync_message`; the record is `profile/career/.cover_sync.json`). `python tools/cover_sync.py status` lists the blocks whose sources changed, `done` records the sync after they are reviewed. `jd_check.py tailor` and `master_drift.py clear` refuse while any block is stale. Blocks without metadata, and the example career, are ignored.

## `tools/master_drift.py`: which applications no longer match the master documents

Two more actions: `status` says whether the masters are **cleared** (they passed the `master-update` check exactly as they are now) and `clear` records it. `jobradar/career.py` holds the stamp: `masters_digest()` (SHA-256 of the three masters, line endings ignored), `masters_cleared()`, `clear_masters()`; the stamp is `profile/career/.master_cleared`. `tools/jd_check.py tailor` calls `masters_cleared()` and refuses (removing the validation stamp, so `render_resume.py` refuses too) when the masters changed after the last clean check.

Used by the `master-update` skill ([4.5](04-Claude-session.md)). Read-only, no LLM. `check_app()` compares each cited line in an
application's `tailored.json` with the master line (`STALE` if a master file is newer than `resume.pdf`; `MISSING` ids; lines under 90%
similar, most of which are deliberate condensations), `main()` prints one block per application folder. `stages()` reads the latest board stage
per role from `data/pipeline_log.jsonl` (`LOG`); an application whose stage is in `SUBMITTED` (Applied, Interview, Offer, Rejected) is printed as
`SUBMITTED` and not checked, because its PDFs are the record of what was sent (only a `MISSING` note is kept); `--all` checks those too.

## `tools/cv_lint.py`: form and section rules for CV and letter text

Used by `jd_check.py tailor` (errors fail validation) and by `master-update` (`python tools/cv_lint.py master`). No LLM. The rules are in `.claude/skills/tailor-application/writing-rules.md`; this is the pattern-matching half.

Line-level checks:

| Function | Does |
|---|---|
| `line_issues()` | Flags meta-commentary ("too new for measured results", "came afterwards", "my own team", "from other teams"), "from about X to about Y", "extended deadline", dangling hyphens, RAG outside Skills, stacked hedges, "Briefed" without impact and repeated phrases. |
| `ad_overlaps()` | Runs of five or more words a letter block shares with the ad (`work/jd/<ref>/jd.txt`); `tailored_issues()` makes each one an error (the letter must reword the ad). |
| `ad_paraphrases()` | Warns when a letter sentence keeps an ad sentence's content words in order (a reworded copy). |
| `skill_issues()` | Requires every skill item to start with a capital letter and checks language lists; `skill_items()` splits a skills line into items on commas outside parentheses. |
| `cross_line_repeats()` | A three-word phrase that two Profile lines share (warning; not checked against the bullets, where an achievement and its experience bullet name the same event by design). |

Structure checks:

| Function | Does |
|---|---|
| `master_issues()` | The header rules for the master CV (no relocation destination, no Medium link). |
| `tailored_issues()` | The section rules (below), plus the errors and warnings from the functions above. |
| `is_company_level()` | Whether a master heading is a company-level one (another heading has three or more parts and names the same company). |
| `sid_is_role()` | Whether a line is a `B` bullet under a job (not Projects or Volunteering), for the depth-floor check. |

What `tailored_issues()` enforces: static lines (projects, volunteering, education) present and verbatim; every skills row present; each role at its depth floor (3 bullets, or all if the master has fewer); a Key achievement that restates an experience bullet (warning). A master bullet of a role left out of the CV is an error unless `tailored.json` carries `"dropped": {id: "no JD match: ..."}` for it (roles with more than 5 master bullets may drop down to 5 freely; `jd_check.py` allows the optional `dropped` field). Skills capitalisation (every word) lives in the masters, not in the lint.

**Watch out**: it is pattern-matching. Tone, tense and whether a section does its job are the copy-editor reviewer's (`application-review`).

## `tools/consistency_check.py`: cross-check CV, cover letter and STAR stories

Used by the `application-review` skill ([4.6](04-Claude-session.md)). No LLM. It reads the three documents, extracts figures and names, and lists the ones only one document has.

| Function | Does |
|---|---|
| `read_doc()` | Reads `.md`/`.txt`, or `.pdf` through `pdftotext`. |
| `clean()` | Drops front matter, comments, `[Bxx]` IDs, heading marks, all-caps headings and the STAR story-picker table. |
| `figures()` | Numbers and percentages with the noun after them; spelled-out numbers become digits; keyed by the number alone so "eight assessors" matches "8 assessors". |
| `names()` | Acronyms, CamelCase and mid-sentence capitalised words. |
| `facts()` | The figures and names of one document together. |
| `compare()` | `unsupported`: in the cover letter or stories but in neither other document; `cv-only`: a CV figure nothing backs up; `placeholders`. |
| `locate()` | Finds the documents (`--folder` or the career docs; `--cv/--cover/--stories` override). |
| `report()` | Formats the result. |
| `main()` | The CLI; exit 1 on unsupported items, or placeholders with `--final`. |

**Watch out**: it finds *candidates*. Two sentences that contradict each other in words (a rating "confirmed" in one document and "compromised" in another) share no figure or name, so only the reviewer subagent reading the pages catches them.


### `tools/domain_profile.py`

The deterministic half of the `domain-profile` skill. `validate` checks `profile/domains.json` against the masters (every cited ID exists, a `strong` domain has at least two pieces of evidence, `lead_ids` are evidence, `not_claimed` is present) and stamps the masters' digest on success; `status` says whether the file is missing or older than the masters; `lead <domain|sector>` prints the IDs a tailored CV and cover letter lead with. It never edits a master. Consumers read the small JSON instead of the masters.
