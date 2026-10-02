# 5.3 `jobradar/sources/`: the adapters

**What this is:** The source adapters: the registry and runner, polite HTTP, company ATS boards, the keyword-search APIs, hand-made careers pages and saved alert emails.  
**Read first:** [8. Sources](08-Sources.md) for what each costs and how it breaks  
**Code:** `jobradar/sources/*.py`  

Part of the [5. Code reference](05-Code-reference.md) (the index of every file and function).

---

## `sources/__init__.py`: registry and runner

| Name | Is |
|---|---|
| `_FACTORIES`, `_MODULES` | Registered adapters; the modules to import so they register. |
| `register(name)` | Decorator-style: `register("ats")(AtsSource)`. |
| `load_sources_config()` | `sources.yaml` via `yaml.safe_load` (never `yaml.load`, which can run code). |
| `build_sources(cfg, only)` | Adapters for enabled sources (or just `only`); unknown names are an error. |
| `_run_one(src)` | One source under its timeout; exceptions become a failed result. |
| `run_sources(sources)` | All of them concurrently. |

## `sources/_http.py`: polite HTTP

`USER_AGENT` identifies the tool. `client()` makes an httpx client. `request()` retries
on 429/5xx with backoff (or the server's `Retry-After`, capped at 60 s) and pauses 0.5 s
after each request. `PAUSE`/`BACKOFF` are module variables so tests can set them to 0.

## `sources/ats.py`: company ATS boards

| Name | Is |
|---|---|
| `job_to_posting(job, board)` | ats-scrapers `Job` → `Posting`, with the board's targets as `company_hint`. |
| `workday_detail_url(url)` | A Workday job URL → its detail-API URL. |
| `resolve_workday_rollups(postings, client)` | For Workday jobs listed as "N Locations" whose title matches, fetch the real offices. |
| `AtsSource.fetch()` | Read `boards.json`, fetch all boards, one unit per board, then resolve Workday roll-ups. |

**Watch out**: `ext = gid if ":" in gid else str(job.url)`: ats-scrapers invents a random
UUID when a board has no job ID; that would look new every run, so only `ats:id`-form IDs
are trusted and the URL is used otherwise.

## `sources/search.py`: base for keyword-search APIs

`SearchSource.fetch()` runs each configured query (one unit each, `track_empty=False`
because a narrow query can legitimately return nothing), then a **canary** query
(`health_query`, broad, must never be empty). Subclasses implement `search(client, query)
-> (postings, total)` and optionally a cheap `count()`.

## `sources/bundesagentur.py`, `jobtech.py`, `eures.py`: public job APIs

Each has `parse(item) -> Posting` for one API result and a `SearchSource` subclass with
default queries and paging. Specifics:
- **bundesagentur**: `X-API-Key: jobboerse-jobsuche` is the public key from the API docs,
  not a secret. `veroeffentlichtseit` = days back.
- **jobtech**: multi-word queries are sent in quotes; otherwise the API ORs the words.
- **eures**: POSTs a search body; title search only (`specificSearchCode: TITLE`); UK isn't
  in EURES and DE is skipped because it mirrors Bundesagentur; region lists can contain
  `null`, which `parse()` filters.

## `sources/reed.py`: reed.co.uk (UK)

`parse(job)` (one API result → `Posting`; `dd/mm/yyyy` dates; a bare town is read as GB), `ReedSource`
(`_auth()` = HTTP Basic with the key as username, error if unset; `_page`, `search`, `count` with
`permanent=true`, UK location).

## `sources/careers_page.py`: hand-made careers pages

| Name | Is |
|---|---|
| `clean(text)` | Collapse whitespace, drop soft hyphens. |
| `parse_selector(html, page)` | CSS selectors → postings. A missing `anchor` raises "page layout changed". |
| `_pick(item, path)` | A JSON job field by dotted path (`data.title`). |
| `parse_feed(body, page)` | JSON (with `items_path`/`fields`, where fields may be dotted paths, and an optional `url_template` that builds the job link from its id when items carry no public URL) or RSS/Atom via `defusedxml`. |
| `parse_hash(html, page)` | Hash the listing section's text; the hash is the posting ID, so any change surfaces once as "Careers page changed". |
| `_posting(...)` | Build a `Posting` with the page's company as hint. |
| `render_js(url)` | Playwright, only if installed (local only). |
| `CareersPageSource` | `load_pages()`, `allowed()` (robots.txt per RFC 9309 via `robots_rules()`: 200 = follow the rules, 4xx = no rules, 5xx or unreachable = disallowed; cached per host), `fetch_page()`, `fetch()` (pages one after another, not in parallel; one unit per page, keyed by URL; 90 s cap each; 300 s for the whole source by default). |
| `robots_rules(status, text)` | robots.txt per RFC 9309; also used by `jd_prep.py`. |
| `PAGE_CHANGED`, `PARSERS` | The `raw` flag marking a hash-mode notice (it bypasses the title filter); mode → parser function. |

**Watch out**: the `anchor` exists to tell "no openings" (anchor present, zero jobs) apart
from "the site was redesigned and our selectors broke" (anchor missing). Both would
otherwise look like an empty list.

**Watch out**: selector postings use `external_id = url|title`, because several jobs can
share one link. So if an employer edits a job's title, it's reported as a new role.

## `sources/alert_email.py`: parse saved alert emails

| Name | Is |
|---|---|
| `_NOISE` | Card lines that are never company or location ("Easy Apply", "3 connections", salaries…). |
| `_part(msg, type)` | The text/plain or text/html body. |
| `_find_id(provider, s)` | The job ID in a link, also after URL-decoding (tracking redirects encode it). |
| `_split_company_location(lines)` | "Acme · London" or two lines → (company, location). |
| `_find_link(p, s)`, `_content_id(...)`, `_has_company_line(line)` | A job ID from a link, or (for ID-less providers like Indeed) the provider's pinned redirect URL; a stable hash ID from title/company/location; whether a card line is "Company - Location". |
| `parse_text(p, body)` | Plain-text cards: a short paragraph followed by the job URL. ID-less cards also need a company line; the alert's subject supplies the country for unknown towns (`to_postings`). |
| `parse_html(p, body)` | HTML cards: from each job link (keyed by ID, or by the pinned redirect for ID-less providers), climb to the largest element containing only that job. The title is the shortest link text for that job (Indeed wraps the whole card in the same link); a "Company" line followed by "- Location" is joined, and ID-less cards need that company line. |
| `is_match_mail(msg)`, `parse_match(body)` | Indeed "job match" mail (`@match.indeed.com`): one recommended job (title, company, location, then `View job:` with a `cts.indeed.com/v3/` tracking link, the only link accepted). |
| `to_postings(msg, p)` | Match mail via `parse_match`; otherwise text first, HTML as fallback; URL **rebuilt from the job ID**. |
| `_mailbox_units()` | Turns the fetcher's per-provider counts into health units: nothing from any provider at all, or provider mail only from unknown sender addresses. |
| `AlertEmailSource` | `_messages()` reads `.alert_mail/*.eml` and fails if `_status.json` says the fetch failed; `fetch()` drops unknown senders and DKIM failures, and reports per provider: jobs, rejected, and emails that yielded no jobs (layout change), not counting account mail such as "your job alert is now active" (`_ACCOUNT_MAIL`); the failure message names up to three subjects of those empty emails. Unknown senders are informational (a bank notice is not a fault) unless the sender's address names a provider (the provider changed its sender), which is a failure. |
