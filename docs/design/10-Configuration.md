# 10. Configuration

**What this is:** Every settings file in `profile/`, key by key. Claude edits these for the user; this page is what each key means.  
**Read first:** [2. Architecture, Settings](02-Architecture.md#settings-profile-falling-back-to-examples)  
**Code:** `jobradar/paths.py` (where files are read from), `jobradar/common.py` (`CONFIG`), `examples/` (the samples)

The user's settings live in **`profile/`**, which exists only in the user's private copy.
Each file is read from `profile/` when it's there, otherwise from **`examples/`**
(the generic samples that ship with the public template). To start, copy the
files to change from `examples/` into `profile/`.

| File (in `profile/`) | Holds |
|---|---|
| `config.json` | **All filter rules**: countries, title include/exclude, tier weights, sponsor-match thresholds, timeouts |
| `sources.yaml` | Which sources run and how (YAML so risk notes can sit next to flags) |
| `targets.tsv` | The user's target companies |
| `aliases.csv` | Employer spellings that normalization can't fold into a target |
| `overrides.csv` | Extra ATS careers URLs for `verify_boards.py` |
| `board_blocklist.csv` | Boards `verify_boards.py` must never poll (`ats,slug,board_url,reason`; match on ats+slug or on the URL). For placeholder boards that list fake jobs |
| `careers_pages.yaml` | Careers pages without an ATS |
| `sponsor_overrides.csv` | Pinned sponsor-register matches |

Aliases only count when their `canonical` is one of the user's targets: an alias to a
company the user doesn't track is ignored rather than putting it on the user's list.

## Titles (`config.json`)

`title_include` lists the keywords a job title must contain (at least one); `title_exclude`
lists keywords that drop a title even if it matches.

- Case-insensitive **whole-word** matching: `"soc"` excludes "SOC Analyst" but not
  "Associate". End a keyword with `*` to match word prefixes: `"pentest*"`
  matches pentester, pentesting, pentestare.
- Exclude wins over include.
- Includes a few German/Swedish keywords (`penetrationstest*`,
  `anwendungssicherheit`, `applikationssäkerhet`) because public-portal ads often
  use local titles.
- Excludes seniority the user doesn't target (director, head of, vp, principal,
  manager), out-of-scope areas (soc, red team, cloud security, ai security, grc)
  and student roles (intern, thesis, werkstudent).

## Permanent roles only (`employment_exclude`)

A role is dropped when its title, or the employment type its ATS reports (`employment_type`,
`commitment`), contains one of these keywords (same whole-word/`*` rules as titles): contract,
fixed-term, temporary, interim, freelance, maternity cover, secondment, internship, and German,
Dutch and Swedish equivalents. "Smart contract" is exempt. Sources without an employment type
(public APIs, careers pages, alert emails) are filtered by title only; `score-roles` treats a
contract stated only in the job description as a blocker.

## Working languages (`languages`)

The languages the user works in, by English name (default `["English"]`). It is read by `tools/jd_prep.py`,
not by the daily run (which never sees an ad's text). For every job description it writes one
"Language check" line into `packet.md`: which language the ad is written in (stop-word counts for
English, German, French, Dutch, Spanish, Italian, Swedish, Portuguese), and any other language the ad
asks for ("fluent German", "Dutch language skills"; a sentence naming a language needs a proficiency cue,
so "our German bank clients" is ignored; "a plus" or "nice to have" next to it makes it optional). An ad
written in, or requiring, a language not in this list is a `language` blocker and `score-roles`
recommends skip. It is a hint: Claude still reads the text. Adding a language here (for example
`["English", "German"]`) stops both the flag and the blocker for it.

## Old roles (`max_age_days`)

A role is dropped when its posted date is more than `max_age_days` days ago (drop reason "posted too
long ago" in the digest). `0` means no limit. A role with no posted date is always kept: some
sources (alert emails, careers pages, a few ATSs) don't report one. The check runs in `radar.select`
before roles are deduplicated or marked seen, so it only affects roles found from now on; roles
already on the board are moved to Skipped separately (ask Claude).

## Countries

`priority_countries` are always searched; `extra_countries` only when
`include_extra_countries` is true. A location counts when the source's country
code or the location text names a country or a known city. A US, Canadian or
Australian location never counts as European because of a city name
("Cambridge, MA", "London, ON", "Sydney, New South Wales").

## Companies and aliases

A posting's employer is normalized (lower-case, accents and punctuation removed,
legal suffixes like Ltd/LLP/GmbH/B.V./AG dropped, regional qualifiers like
UK/NL/Cyber dropped) and looked up exactly. So "Deloitte LLP", "Deloitte UK" and
"Deloitte Netherlands B.V." all become **Deloitte**. There is deliberately no
fuzzy matching, because it would put strangers on the user's board.

When a target's postings land in "Outside your list" under another name, add a
row to `profile/aliases.csv`:

```csv
alias,canonical
PricewaterhouseCoopers,PwC UK Cyber
```

`canonical` can be any name from `targets.tsv`.

Known limitation: short generic target names (Bird, Box, Bolt, Exact, Orange,
Sky, Unity) match any employer with exactly that normalized name.

## Two different "include outside" switches

Employers not on `targets.tsv` are "outside your list". Two settings control them, in two
different files, for two different outputs:

| Setting | File | Controls |
|---|---|---|
| `include_outside_list` (top level, and per source) | `sources.yaml` | Whether `radar.py` keeps outsiders at all: they then appear in the digest's "Outside your list" section and in `matches.csv`. A per-source value overrides the top level (e.g. `eures.include_outside_list: true`). `--include-outside` on the command line forces it on for one run. |
| `board.include_outside` | `config.json` | Whether kept outsiders also become **board cards**. Only matters if the first switch let them through. |

## `sources.yaml` keys

Every source takes `enabled` and `timeout_seconds` (a cap on the whole source). Then:

| Source | Keys |
|---|---|
| `ats` | `boards_file` (default `boards.json`) |
| `bundesagentur`, `jobtech`, `eures` | `queries`, `health_query` (the canary), `days` (look-back), `max_pages`; `eures` also `countries` |
| `reed` | `queries`, `health_query`, `max_pages`, `location` (default "United Kingdom"); key from the `REED_API_KEY` environment variable |
| `careers_page` | `pages_file` (default `careers_pages.yaml` via the profile), `respect_robots` (default true) |
| `alert_email` | `providers` (default **linkedin only** when unset, while the mail fetcher defaults to all three: list every provider you set alerts up for), `eml_dir` (default `.alert_mail`), `require_dkim` (default true) |

## `careers_pages.yaml` keys (one entry per page)

| Key | Mode | Meaning |
|---|---|---|
| `company`, `url` | all | Target name (as in `targets.tsv`) and the page to fetch |
| `mode` | all | `selector` (default), `feed` or `hash` |
| `default_location` | all | Used when the page gives no recognisable location |
| `enabled` | all | Default true |
| `render: js` | all | Needs a browser (Playwright, local only; errors in Actions) |
| `tested` | all | Date the entry was last checked live (for humans) |
| `item` | selector | CSS selector matching one job |
| `title` | selector | Selector inside the item (default: the item's text) |
| `link` | selector | Selector inside the item (default: first `<a>`), or `"#id"` to use `url#<item id>` for one-page listings |
| `location` | selector | Selector inside the item (optional) |
| `anchor` | selector | Something present even with zero jobs; missing = "page layout changed" error |
| `expect_jobs` | selector/feed | True = zero jobs counts as broken |
| `feed_url` | feed | Feed URL (default: `url`) |
| `items_path` | feed (JSON) | Dotted path to the job list, e.g. `data.jobs` |
| `fields` | feed (JSON) | Key names: `{title:, url:, location:, id:}` |
| `container` | hash | Selector of the section to hash (default `body`) |
| `ignore_patterns` | hash | Regexes removed before hashing (dates, counters) |

## Board (`config.json` → `board`)

| Key | Default | Meaning |
|---|---|---|
| `enabled` | true in `examples/`; **off if the key is missing** | Queue new roles for the board at all |
| `tiers` | [1, 2] | Which tiers become cards |
| `baseline_tiers` | [1] | Which tiers become cards on the very first run |
| `include_outside` | false | Also make cards for employers not on the target list |
| `max_per_run` | 40 | Issues created per run; the rest wait in the queue |
| `stale_days` | 5 | Days unlisted before a card gets `possibly-closed` |

The board's fields and views are code, not settings: `FIELDS` and `VIEWS` in
`tools/board_sync.py` ([Board internals](11-Board-internals.md)).

## Scoring (`config.json` → `scoring`)

| Key | Default | Meaning |
|---|---|---|
| `auto_per_session` | 8 | Roles Claude scores automatically at the start of each session, before answering the user's first message: the freshest unscored Tier 1 roles on the list, skipping cards already closed or skipped. 0 = only when asked. 0.25–0.5% of a session per role (measured) |

## Referrals (`config.json` → `referrals`)

| Key | Default | Meaning |
|---|---|---|
| `wait_days` | 4 | Days an ask may go unanswered before the session brief suggests one follow-up or applying directly |
| `linkedin_lookup` | false | true lets the `referrals` skill use Claude in Chrome, in the user's logged-in browser, to read LinkedIn people-search results for **one** company when the user is about to apply to one role and asks. Read-only, at most 3 searches; never connects or messages. LinkedIn's terms ban automated access, so this is the user's risk to accept. false: Claude gives search links for the user to open |

Contacts are in `profile/network.csv` (see [2](02-Architecture.md)).

## Hiring-post discovery (`config.json` → `discovery.linkedin_posts`)

| Key | Default | Meaning |
|---|---|---|
| `enabled` | false | true lets the `post-discovery` skill use Claude in Chrome, in the user's logged-in browser, to read LinkedIn **post** searches and known recruiters' posts at the start of a session. Read-only; never reacts, comments, connects or messages. LinkedIn's terms ban automated access, so this is the user's risk to accept |
| `max_searches` | 8 | Post searches per session |
| `max_scrolls` | 12 | The ceiling on scrolls per search. A search scrolls until the newest-first results pass `max_post_age_days` (30), so the whole window is read; the ceiling only stops a runaway |
| `max_people_per_session` | 8 | Profiles opened (known people's posts, original authors) per session |
| `company_queries` | 6 | How many of the session's searches are `<company> "we're hiring" security`, walked in this order: companies in `profile/network.csv` that are also good fits first, then other scored apply/maybe employers, then `company_fit` targets; the rest are keyword searches (a small safety net; the user found keyword-only sweeps nearly useless) |
| `company_extra` | [] | Companies the user wants searched even before any of their roles is scored (named in chat; Claude edits the list). Searched in the same company slots, ahead of the scored apply/maybe employers; each employer once |
| `network_only` | false | true: the company searches walk only the user's own `company_extra` and employers where `profile/network.csv` has someone they know (a referral route); scored apply/maybe and `company_fit` employers with no contact are skipped. The sweep exists to find referrals, so the user's copy has it on (2026-10-05) |
| `company_fit` | High | Also search the `targets.tsv` companies whose Fit column has this value (after the user's `company_extra` and the scored apply/maybe employers). Blank: none. `targets.tsv` may have a `Fit` column (High / Medium / Watch); older files without it simply add nothing |
| `not_words` | contract, contractor, freelance | Appended to keyword searches as `NOT (...)`; filters on post text only |
| `max_post_age_days` | 30 | A post whose original is older than this is stale unless the role is confirmed open |
| `titles`, `places`, `phrases` | security titles; countries and cities; "we're hiring", "visa sponsorship", "relocation", "join my team" | The grid the search rotation walks (`tools/post_leads.py queries`) |

## Other `config.json` keys

| Key | Meaning |
|---|---|
| `tiering` | Score weights and `tier1_min_score`; see [Tiers and sponsorship](09-Tiers-and-sponsorship.md) |
| `sponsorship.fuzzy_yes` / `fuzzy_unknown` | Fuzzy name-match thresholds (0–100) for the sponsor registers |
| `board_timeout_seconds` | Time cap per ATS board fetch (180) |
| `workday_max_retries` | Retries per Workday page before a board fails (6). It can only raise the library's own value (3), never lower it, and it sets a module global inside ats-scrapers for the rest of the process. Big tenants such as Nvidia and Palo Alto get throttled deep into pagination |
| `concurrency` | ATS boards fetched at once (6) |
| `_comment` keys | Ignored by the code; notes for humans |

## Dependencies

See [7. Changing it](07-Changing-it.md#change-a-dependency).
