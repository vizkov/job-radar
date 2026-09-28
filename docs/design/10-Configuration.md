# 10. Configuration

**What this is:** Every settings file in `profile/`, key by key. Claude edits these for the user; this page is what each key means.  
**Read first:** [2. Architecture, Settings](02-Architecture.md#settings-profile-falling-back-to-examples)  
**Code:** `jobradar/paths.py` (where files are read from), `jobradar/common.py` (`CONFIG`), `examples/` (the samples)

Your settings live in **`profile/`**, which exists only in your private copy.
Each file is read from `profile/` when it's there, otherwise from **`examples/`**
(the generic samples that ship with the public template). To start, copy the
files you want to change from `examples/` into `profile/`.

| File (in `profile/`) | Holds |
|---|---|
| `config.json` | **All filter rules**: countries, title include/exclude, tier weights, sponsor-match thresholds, timeouts |
| `sources.yaml` | Which sources run and how (YAML so risk notes can sit next to flags) |
| `targets.tsv` | Your target companies |
| `aliases.csv` | Employer spellings that normalization can't fold into a target |
| `overrides.csv` | Extra ATS careers URLs for `verify_boards.py` |
| `careers_pages.yaml` | Careers pages without an ATS |
| `sponsor_overrides.csv` | Pinned sponsor-register matches |

Aliases only count when their `canonical` is one of your targets: an alias to a
company you don't track is ignored rather than putting it on your list.

## Titles (`config.json`)

- Case-insensitive **whole-word** matching: `"soc"` excludes "SOC Analyst" but not
  "Associate". End a keyword with `*` to match word prefixes: `"pentest*"`
  matches pentester, pentesting, pentestare.
- Exclude wins over include.
- Includes a few German/Swedish keywords (`penetrationstest*`,
  `anwendungssicherheit`, `applikationssäkerhet`) because public-portal ads often
  use local titles.
- Excludes seniority you don't target (director, head of, vp, principal,
  manager), out-of-scope areas (soc, red team, cloud security, ai security, grc)
  and student roles (intern, thesis, werkstudent).

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
fuzzy matching, because it would put strangers on your board.

When a target's postings land in "Outside your list" under another name, add a
row to `profile/aliases.csv`:

```csv
alias,canonical
PricewaterhouseCoopers,PwC UK Cyber
```

`canonical` can be any name from `targets.tsv`.

Known limitation: short generic target names (Bird, Box, Bolt, Exact, Orange,
Sky, Unity) match any employer with exactly that normalized name.

## Board (`config.json` → `board`)

| Key | Default | Meaning |
|---|---|---|
| `enabled` | true | Queue new roles for the board at all |
| `tiers` | [1, 2] | Which tiers become cards |
| `baseline_tiers` | [1] | Which tiers become cards on the very first run |
| `include_outside` | false | Also make cards for employers not on the target list |
| `max_per_run` | 40 | Issues created per run; the rest wait in the queue |
| `stale_days` | 5 | Days unlisted before a card gets `possibly-closed` |

The board's fields and views are code, not settings: `FIELDS` and `VIEWS` in
`tools/board_sync.py` ([Board internals](11-Board-internals.md)).

## Other `config.json` keys

| Key | Meaning |
|---|---|
| `tiering` | Score weights and `tier1_min_score`; see [Tiers and sponsorship](09-Tiers-and-sponsorship.md) |
| `sponsorship.fuzzy_yes` / `fuzzy_unknown` | Fuzzy name-match thresholds (0–100) for the sponsor registers |
| `board_timeout_seconds` | Time cap per ATS board fetch (180) |
| `concurrency` | ATS boards fetched at once (6) |
| `_comment` keys | Ignored by the code; notes for humans |

## Dependencies

`requirements.in` lists direct dependencies; `requirements.txt` is the
hash-locked result, installed with `--require-hashes` in CI. To change one:

```bash
pip install pip-tools
pip-compile --generate-hashes --strip-extras --allow-unsafe -o requirements.txt requirements.in
pip-compile --generate-hashes --strip-extras --allow-unsafe -o requirements-dev.txt requirements-dev.in
```

Review the upstream diff before bumping `ats-scrapers`: it's the main
third-party code that runs against live sites in your workflow.
