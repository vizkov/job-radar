# job-radar design reference

For Claude (which operates the system) and for maintainers. The user-facing guide is
[docs/wiki](../wiki/Home.md); the operating rules are in `CLAUDE.md` and `.claude/skills/`.

| Page | What it covers |
|---|---|
| [Board internals](Board-internals.md) | Issues → cards, labels vs fields, fill, stale, board template sync |
| [Setup](Setup.md) | Public template vs private copy, first-time setup commands, template publishing, workflows |
| [Sources](Sources.md) | Each source adapter: cost, failure modes, how to test one |
| [Job-alert emails](Job-alert-emails.md) | Alert-email pipeline, secret isolation, main vs dedicated mailbox |
| [Tiers and sponsorship](Tiers-and-sponsorship.md) | Tier rules, freshness, UK/NL sponsor-register matching |
| [Configuration](Configuration.md) | The files in `profile/` |
| [Troubleshooting](Troubleshooting.md) | Health signals and what to check |
| [Security model](Security-model.md) | Secrets, untrusted job ads, privacy split, what it never does |
