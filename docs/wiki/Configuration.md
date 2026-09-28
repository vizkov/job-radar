# Configuration

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
