# Setup

job-radar is meant to run as **two repos**:

| Repo | Visibility | Contains |
|---|---|---|
| **Template** | public | Code, docs, tests, generic `examples/`, public sponsor registers |
| **Your copy** | **private** | The same code **plus** `profile/` (your settings), `state/`, `digests/`, `data/matches.csv`, `boards.json` and the role issues |

Why: GitHub keeps secrets out of forks and copies, but everything else in a
public repo is public, including the issues, committed digests and Actions logs.
Your job search must only live in the private copy. (A fork of a public repo
can't be made private, so don't fork: clone and push to a new private repo.)

Every workflow starts with a **privacy guard**: it asks the GitHub API whether the
repo is private and skips the real job if it isn't, with a warning. So the public
template never runs, and nor does an accidental public copy. To deliberately
run in a public repo, set the repository variable `JOB_RADAR_ALLOW_PUBLIC=true`.

## A. Your private copy

```bash
git clone https://github.com/<you>/job-radar.git my-job-radar   # the public template
cd my-job-radar
git remote rename origin template          # future code updates come from here
# create an EMPTY private repo on GitHub (no README), then:
git remote add origin https://github.com/<you>/my-job-radar.git
git push -u origin main
```

Then open **Claude Code** in that folder and say **"set this up for me"**.
Claude follows the `setup` skill: it builds your profile from your CV and
preferences, maps your target companies to job boards, fetches the sponsor
registers, creates your Project board, optionally walks you through alert emails,
and switches on the scheduled runs. It asks you only for what it can't do itself:

| You do | Why |
|---|---|
| Give it your CV, preferences and target companies | It converts them into `profile/` |
| Run `gh auth refresh -s project` once (a browser login) | Lets Claude create and update your Project board |
| Turn on the Project's **Auto-add to project** workflow (filter `is:issue label:role`) | GitHub has no command for this; it's two clicks |
| Add the two alert-email secrets in GitHub's settings page (optional) | Secrets never pass through chat or files |
| Set the repo's watch level to **Participating and @mentions** | Role cards then don't email you |

### What Claude runs, for reference

```bash
python -m venv .venv && source .venv/bin/activate    # Windows: .venv\Scripts\activate
pip install --require-hashes -r requirements.txt -r requirements-career.txt
mkdir profile && cp -r examples/* profile/            # then fills them in with you
python tools/refresh_registers.py                     # sponsor registers, ~1 min
git clone https://github.com/kalil0321/ats-scrapers atss
git clone https://github.com/Feashliaa/job-board-aggregator agg
python tools/build_candidates.py                      # targets -> candidate job boards
python verify_boards.py --quiet                       # 15-40 min; writes boards.json
python radar.py --dry-run --quiet                     # full run, nothing written
python tools/board_sync.py setup-project --repo <you>/my-job-radar
git add profile data boards.json && git commit -m "my job-radar profile" && git push
gh workflow enable job-radar && gh workflow run job-radar
```

The first run is a baseline: everything open is recorded, and only Tier 1 roles
become board cards. After that, only new roles appear.

### Getting code updates

```bash
git pull template main
```

The template never contains `profile/` or your run data, so this doesn't conflict
with your settings.

## B. Publishing the template (maintainer)

Build the public tree from a working copy without any private files:

```bash
python tools/public_template.py export ../job-radar-template
cd ../job-radar-template
git init -b main && git add . && git commit -m "job-radar template"
# push to a PUBLIC repo; Settings → tick "Template repository" if you like
```

To keep the template current automatically, point git at the shipped hook and the template clone:

```bash
git config core.hooksPath .githooks
git config jobradar.templateDir ../job-radar-template
```

After each commit, `.githooks/post-commit` publishes any changed public code (only paths on the
allowlist in `tools/public_template.py`, never private ones), runs the tests in the template,
pushes it and merges it back. A failure never blocks your commit; the session brief reports
unpublished code instead.

The hook also mirrors `docs/wiki/` into the template's **Wiki tab** (links rewritten for the
wiki). `docs/wiki/` stays the source of truth: it's versioned with the code, reaches every
copy, and is what Claude reads. GitHub only creates a wiki's git repo when its first page is
saved, so the maintainer clicks **Wiki → Create the first page → Save** once; until then the
mirror does nothing.

Before every manual push to the template, check nothing private is tracked:

```bash
python tools/public_template.py check    # fails if profile/, state/, digests/, boards.json, … are tracked
```

It treats these as private: `profile/`, `state/`, `digests/`, `data/matches.csv`,
`boards.json`, `data/candidates.csv`, `data/coverage_report.csv`,
`data/verified_boards.csv` (those four are derived from your targets), and
`data/registers/` (public data, but refreshed in each copy, so shipping it would
cause merge conflicts).

After the first publish, develop in the private copy: `publish` (or the post-commit hook)
copies changed public files into the template clone as a normal new commit, so the
template's history is never rewritten. Other copies pick changes up with `git pull template main`.

## Workflows

| Workflow | When | What |
|---|---|---|
| `radar.yml` | 3x daily: 02:47, 08:47, 14:47 UTC (08:17, 14:17, 20:17 IST) | fetch alert mail, poll sources, add role cards, update status, commit |
| `verify.yml` | 1st of month | re-verify ATS boards, commit `boards.json` |
| `registers.yml` | Mondays 04:23 UTC | refresh UK/NL sponsor registers, commit if changed |

All three run behind the privacy guard, share one concurrency group (their
commits never race), and run with `--quiet` so the digest and your target list
stay out of the Actions logs.
