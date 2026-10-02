# 9. Tiers and sponsorship

**What this is:** The two automatic labels every new role gets: a rule-based fit **tier** (1 or 2) and, for UK and Dutch roles, a **visa-sponsor** signal. No AI is involved in either.  
**Read first:** [3.2, Enrich](03-Scheduled-run.md#enrich-enrich)  
**Code:** `jobradar/tiering.py`, `jobradar/sponsors.py`, `tools/refresh_registers.py`, `profile/config.json` → `tiering`, `profile/sponsor_overrides.csv`

Every new role gets a **fit tier** and, for UK and Dutch roles, a
**visa-sponsor signal**. Both are simple rules, with no LLM involved.

## Sponsor signal

```
- [Senior Penetration Tester](…) — London · UK sponsor: yes (Bridewell Consulting Limited)
```

Source registers, refreshed weekly by `.github/workflows/registers.yml` into
`data/registers/`:

| Register | What it lists | Rows (2026-09-28) |
|---|---|---|
| UK Home Office register of licensed sponsors | Employers licensed for Skilled Worker, Senior or Specialist Worker, Scale-up | 123,106 |
| Dutch IND public register "Work" | Recognised sponsors for work / highly skilled migrants | 12,984 |

How the employer is matched (tried with your `targets.tsv` name first, then the
name the source reported):

| Result | Meaning |
|---|---|
| `yes (<register name>)` | Exact match after normalizing, a whole-word prefix match to one entity ("Adyen" → "ADYEN N.V. LONDON BRANCH"), or a very close spelling (fuzzy ≥ 94) |
| `unknown (<candidates>)` | Several entities fit ("Barclays Bank PLC / Barclays Execution Services"), a spelling is close but not certain (fuzzy 86–93), or the employer is anonymous |
| `no` | Nothing close in the register |

**The register is only the first step.** On the board it appears as *Licensed*, *Unclear* or
*Unlikely*. The `sponsorship-check` skill turns that into a checked verdict for the specific role
(Confirmed, Likely, Unlikely or No; the board's Sponsor field also holds the register-only *Licensed* and *Unclear*) from the ad's own words, the destination country's rules and the
company's pages, with evidence and links on the card ([4](04-Claude-session.md)).

**Always read the register name in brackets.** The signal is about legal
entities, and a group can sponsor through a subsidiary with a different name
(that shows as `no`). A short, generic brand can hit an unrelated company.

**Fix a wrong match** in `profile/sponsor_overrides.csv`:

```csv
company,uk,nl
Wise,Wise Payments Limited,
ING,ING Services Limited,ING Bank N.V.
Some Firm,no,
```

Tune the fuzzy thresholds in `config.json` → `sponsorship`.

Only the relevant register is shown on the card (UK for GB roles, NL for NL
roles); `data/matches.csv` records both for every role.

A sponsor licence means the employer *can* sponsor, not that this role will.
Check the ad.

## Fit tiers

The digest has **Tier 1 — strongest fit** and **Tier 2** sections. Within each,
companies with the best-scoring role come first.

Score (rules in `config.json` → `tiering`):

| Part | Default |
|---|---|
| Best title keyword | Defaults from `examples/config.json` (the user's `profile/config.json` may differ, and `calibrate.py` retunes it): AppSec / product security / pentest / threat modeling = 4; software security, secure code, offensive security, ethical hacker, VAPT = 3; security consultant, security tester = 2; security engineer / architect / lead, DevSecOps = 1; `vulnerabilit*` = 0 (the user's own file may raise or lower any of these) |
| Seniority words (all that match) | senior, sr, lead +1; associate −1; junior −2; graduate, entry level −3 |
| Best country | GB, NL, IE +2; CH, DE, SE, remote-Europe +1 |
| Employer on your list | +1 |
| Licensed sponsor in the role's country (UK/NL) | +1 |
| Employer's `Fit` column in `targets.tsv` is High | +`target_fit_high` (1): a generic title such as "Security Engineer" at a company you rate highly (Meta, 2026-10-02) should not rank below a specialist title elsewhere |
| Posted within `fresh_days` (3) | +`fresh_bonus` (1): applying early matters |

Tier 1 when the score ≥ `tier1_min_score` (6). Examples:

| Role | Score | Tier |
|---|---|---|
| Senior Application Security Engineer, London, on list, UK sponsor | 4+1+2+1+1 = 9 | 1 |
| Penetration Tester, Amsterdam, on list | 4+2+1 = 7 | 1 |
| Security Engineer, Berlin, on list | 1+1+1 = 3 | 2 |
| Junior Pentester, Stockholm, not on list | 4−2+1 = 3 | 2 |

**Automatic tuning.** Once 30 roles are scored, `tools/calibrate.py` (run weekly by the session
brief) lowers a title keyword's weight by one when roles matching it keep scoring Skip, or raises
it when they keep scoring Apply (at least 5 such roles; weights stay 0–5; one change per keyword
per week). Each change is logged and reported with an undo command.

`data/matches.csv` has `tier`, `score` and `score_reasons` columns, so you can
see why a role landed where it did and adjust the weights.
