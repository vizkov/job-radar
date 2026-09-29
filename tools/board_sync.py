"""Sync job-radar with GitHub issues / the Projects board, via the `gh` CLI.

    python tools/board_sync.py roles  [--dry-run] [--max N]   # queued new roles -> one issue each
    python tools/board_sync.py status [--dry-run]             # create/update the pinned "Radar status" issue
    python tools/board_sync.py stale  [--dry-run]             # label roles no longer listed as possibly-closed
    python tools/board_sync.py backfill-map                   # rebuild role -> issue number map

Local only (your `gh` login needs the project scope: gh auth refresh -s project):
    python tools/board_sync.py setup-project --repo OWNER/REPO   # create the Project + fields, link the repo
    python tools/board_sync.py fill                              # set Stage/Tier/Sponsor on new cards from labels
    python tools/board_sync.py set <ref> Stage=Applied [Fit=72 …] [--close] [--note "why"]
    python tools/board_sync.py views                             # create/update the board's views (VIEWS)
    python tools/board_sync.py design-diff                       # how the board's views differ from VIEWS
    python tools/board_sync.py refresh-bodies                    # tidy role cards; add fit breakdowns from scores
    python tools/board_sync.py archive                           # archive cards in Stage=Skipped (max 40 a run; the
                                                                 #   session-start hook runs it once a day)

In GitHub Actions `gh` uses GITHUB_TOKEN (issues: write). Issues labelled `role`
are pulled onto the Project board by its built-in "Auto-add to project" workflow.
Every gh call passes arguments as a list (no shell), and all text goes in via
--body-file, so nothing from a job ad is ever interpreted by a shell.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from jobradar.mdsafe import md  # noqa: E402  (stdlib-only)
from jobradar.paths import profile_path  # noqa: E402

QUEUE = ROOT / "state" / "board_queue.json"
ISSUE_MAP = ROOT / "state" / "issue_map.json"        # role ref -> issue number
STALE = ROOT / "state" / "stale_roles.json"          # written by radar.py
FLAGGED = ROOT / "state" / "stale_flagged.json"      # refs currently labelled possibly-closed
PIPELINE_LOG = ROOT / "data" / "pipeline_log.jsonl"  # every stage change, with a date
STATUS_MD = ROOT / "digests" / "status.md"
STATUS_LABEL = "radar-status"
MATCHES = ROOT / "data" / "matches.csv"
BOARD_FILE = ROOT / "profile" / "board.json"   # project coordinates, written by setup-project
DATE = "DATE"
FIELDS = {  # name -> single-select options, None for a number field, or DATE
    "Stage": ["New", "Shortlisted", "Applied", "Interview", "Offer", "Rejected", "Skipped"],
    "Tier": ["T1", "T2"],
    "Fit": None,
    "Recommendation": ["Apply", "Maybe", "Skip"],
    # Register match gives Licensed / Unclear / Unlikely automatically; Confirmed / Likely / No need the
    # sponsorship-check skill (tools/sponsorship.py), which looks at the ad, the country and the company.
    "Sponsor": ["Confirmed", "Likely", "Licensed", "Unclear", "Unlikely", "No"],
    "Posted": DATE,  # when the employer posted it (else when the radar first saw it): sort for freshness
    "Referral": ["Finding contact", "Asked", "Referred", "No route", "Not needed"],  # tools/referrals.py
}
REGISTER_TO_SPONSOR = {"yes": "Licensed", "unknown": "Unclear", "no": "Unlikely"}  # label -> Sponsor field
FINAL_STAGES = {"Offer", "Rejected", "Skipped"}
LABEL_COLORS = {"role": "0E8A16", "tier-1": "B60205", "tier-2": "FBCA04", "sponsor-yes": "0E8A16",
                "sponsor-unknown": "C5DEF5", "sponsor-no": "D93F0B", STATUS_LABEL: "5319E7",
                "possibly-closed": "BFD4F2"}
SPACING_SECONDS = 2.0  # GitHub throttles bursts of issue creation


class Gh:
    """Thin wrapper so tests can swap in a fake."""

    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run

    def __call__(self, *args: str) -> str:
        if self.dry_run:
            print("gh " + " ".join(args))
            return ""
        # encoding: gh speaks UTF-8; Windows' default (cp1252) would garble text read back from GitHub
        return subprocess.run(["gh", *args], check=True, capture_output=True, text=True,
                              encoding="utf-8", errors="replace").stdout.strip()


def _body_file(text: str) -> str:
    f = tempfile.NamedTemporaryFile("w", suffix=".md", delete=False, encoding="utf-8")
    f.write(text)
    f.close()
    return f.name


def ensure_labels(gh: Gh, labels: set[str]) -> None:
    for name in sorted(labels):
        color = LABEL_COLORS.get(name, "1D76DB")  # country-* and anything else: blue
        gh("label", "create", name, "--color", color, "--force")


def sync_roles(gh: Gh, max_per_run: int, sleep=time.sleep) -> tuple[int, int]:
    """Open issues for queued roles, oldest first. Returns (created, still queued)."""
    queue = json.loads(QUEUE.read_text(encoding="utf-8")) if QUEUE.exists() else []
    batch = queue[:max_per_run]
    if not batch:
        return 0, 0
    ensure_labels(gh, {label for p in batch for label in p["labels"]})
    created = 0
    for p in batch:
        path = _body_file(p["body"])
        try:
            args = ["issue", "create", "--title", p["title"], "--body-file", path]
            for label in p["labels"]:
                args += ["--label", label]
            url = gh(*args)
            if url and not gh.dry_run:
                _remember_issue(p["ref"], url)
        finally:
            Path(path).unlink(missing_ok=True)
        created += 1
        if not gh.dry_run:  # persist after each success so a crash never duplicates cards
            QUEUE.write_text(json.dumps(queue[created:], indent=1, ensure_ascii=False), encoding="utf-8")
        sleep(SPACING_SECONDS)
    return created, len(queue) - created


def promote(refs: list[str], dry_run: bool = False) -> str:
    """Queue cards for roles that are in matches.csv but not on the board; `roles` then opens them.
    dry_run: report what would be queued, write nothing."""
    import csv
    from jobradar.board import row_payload
    on_board = set(_load(ISSUE_MAP, {}))
    queue = _load(QUEUE, [])
    queued = {p["ref"] for p in queue}
    rows = {r["ref"]: r for r in csv.DictReader(MATCHES.open(encoding="utf-8"))}
    added, skipped = [], []
    for ref in refs:
        if ref in on_board or ref in queued or ref not in rows:
            skipped.append(ref)
            continue
        queue.append(row_payload(rows[ref]))
        queued.add(ref)
        added.append(ref)
    if not dry_run:
        QUEUE.write_text(json.dumps(queue, indent=1, ensure_ascii=False), encoding="utf-8")
    return f"{'would queue' if dry_run else 'queued'} {len(added)} card(s)" + (f"; skipped (on the board, queued or unknown): {', '.join(skipped)}"
                                            if skipped else "")


def _load(path: Path, default):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default


def _remember_issue(ref: str, url: str) -> None:
    m = _load(ISSUE_MAP, {})
    m[ref] = int(url.rstrip("/").rsplit("/", 1)[-1])
    ISSUE_MAP.write_text(json.dumps(m, indent=1, sort_keys=True), encoding="utf-8")


def backfill_map(gh: Gh) -> str:
    """Rebuild state/issue_map.json from the role issues' hidden markers."""
    issues = json.loads(gh("issue", "list", "--label", "role", "--state", "all", "--limit", "2000",
                           "--json", "number,body") or "[]")
    m = _load(ISSUE_MAP, {})
    for i in issues:
        if (hit := re.search(r"job-radar:ref=([0-9a-f]{16})", i.get("body") or "")):
            m[hit.group(1)] = i["number"]
    if not gh.dry_run:
        ISSUE_MAP.parent.mkdir(parents=True, exist_ok=True)
        ISSUE_MAP.write_text(json.dumps(m, indent=1, sort_keys=True), encoding="utf-8")
    return f"issue map: {len(m)} roles"


def sync_stale(gh: Gh) -> str:
    """Label board roles no source has listed recently as possibly-closed; unlabel if they return."""
    report = _load(STALE, {})
    m, flagged = _load(ISSUE_MAP, {}), set(_load(FLAGGED, []))
    added = removed = 0
    to_flag = [r for r in report.get("stale", []) if r in m and r not in flagged]
    if to_flag:
        ensure_labels(gh, {"possibly-closed"})
    for ref in to_flag:
        gh("issue", "edit", str(m[ref]), "--add-label", "possibly-closed")
        flagged.add(ref)
        added += 1
    for ref in report.get("alive", []):
        if ref in flagged and ref in m:
            gh("issue", "edit", str(m[ref]), "--remove-label", "possibly-closed")
            flagged.discard(ref)
            removed += 1
    if not gh.dry_run:
        FLAGGED.write_text(json.dumps(sorted(flagged), indent=1), encoding="utf-8")
    return f"possibly-closed: +{added} / -{removed} (now {len(flagged)})"


def log_stage(ref: str, field: str, value: str, by: str, note: str = "") -> None:
    from datetime import datetime, timezone
    PIPELINE_LOG.parent.mkdir(parents=True, exist_ok=True)
    rec = {"ref": ref, "field": field, "value": value, "by": by,
           "at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    if note:
        rec["note"] = note
    with open(PIPELINE_LOG, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, ensure_ascii=False) + "\n")


def sync_status(gh: Gh) -> str:
    """Edit the open "Radar status" issue, or create and pin it."""
    if not STATUS_MD.exists():
        return "no digests/status.md (run radar.py first)"
    text = STATUS_MD.read_text(encoding="utf-8")
    # radar.py writes the status before `roles` opens the cards; report what's actually left
    left = len(json.loads(QUEUE.read_text(encoding="utf-8"))) if QUEUE.exists() else 0
    text = re.sub(r"(\*\*Waiting to be added to the board:\*\*) \d+", rf"\g<1> {left}", text)
    path = _body_file(text)
    try:
        number = gh("issue", "list", "--label", STATUS_LABEL, "--state", "open", "--limit", "1",
                    "--json", "number", "--jq", ".[0].number")
        if number:
            gh("issue", "edit", number, "--body-file", path)
            return f"updated #{number}"
        ensure_labels(gh, {STATUS_LABEL})
        url = gh("issue", "create", "--title", "Radar status", "--label", STATUS_LABEL, "--body-file", path)
        if url:
            gh("issue", "pin", url.rstrip("/").rsplit("/", 1)[-1])
        return f"created {url or '(dry run)'}"
    finally:
        Path(path).unlink(missing_ok=True)


def gh_json(gh: Gh, *args: str):
    out = gh(*args)
    return json.loads(out) if out else {}


def load_board() -> dict | None:
    return json.loads(BOARD_FILE.read_text(encoding="utf-8")) if BOARD_FILE.exists() else None


def _read_fields(gh: Gh, owner: str, number: str) -> dict:
    fields = {}
    for f in gh_json(gh, "project", "field-list", number, "--owner", owner, "--format", "json").get("fields", []):
        fields[f["name"]] = {"id": f["id"], "options": {o["name"].lower(): o["id"] for o in f.get("options", [])}}
    return fields


def _save_board(gh: Gh, board: dict) -> None:
    if not gh.dry_run:
        BOARD_FILE.parent.mkdir(parents=True, exist_ok=True)
        BOARD_FILE.write_text(json.dumps(board, indent=1), encoding="utf-8")


def setup_project(gh: Gh, repo: str, title: str = "Job search", owner: str = "@me") -> str:
    """Create (or adopt) the Project, add job-radar's fields, link the repo. Safe to re-run:
    board.json is saved as soon as the Project exists, and an existing Project with the
    same title is reused instead of creating a duplicate. Views come from VIEWS (apply_views)."""
    board = load_board()
    if board is None:
        if owner == "@me":  # `gh project link` compares owner names literally, so resolve @me
            owner = gh("api", "user", "--jq", ".login") or owner
        existing_projects = gh_json(gh, "project", "list", "--owner", owner, "--format", "json").get("projects", [])
        proj = next((p for p in existing_projects if p.get("title") == title and not p.get("closed")), None)
        if proj is None:
            proj = gh_json(gh, "project", "create", "--owner", owner, "--title", title, "--format", "json")
        board = {"owner": owner, "number": str(proj["number"]), "id": proj["id"], "url": proj.get("url", "")}
        _save_board(gh, board)
    existing = _read_fields(gh, board["owner"], board["number"])
    for name, options in FIELDS.items():
        if name in existing:
            continue
        args = ["project", "field-create", board["number"], "--owner", board["owner"], "--name", name]
        if options is None or options == DATE:
            args += ["--data-type", "NUMBER" if options is None else "DATE"]
        else:
            args += ["--data-type", "SINGLE_SELECT", "--single-select-options", ",".join(options)]
        gh(*args)
    repo_owner, _, repo_name = repo.partition("/")
    if repo_owner and repo_name and repo_owner.lower() != board["owner"].lower():
        raise ValueError(f"repo {repo} isn't owned by the project owner {board['owner']}")
    gh("project", "link", board["number"], "--owner", board["owner"], "--repo", repo_name or repo)
    board["fields"] = _read_fields(gh, board["owner"], board["number"])
    board["repo"] = repo
    _save_board(gh, board)
    return (f"project {board.get('url') or board['number']} ready. One manual step (GitHub has no CLI for it): "
            "open the project -> ... -> Workflows -> 'Auto-add to project' -> filter  is:issue label:role  -> On.")


def _items(gh: Gh, board: dict) -> list[dict]:
    return gh_json(gh, "project", "item-list", board["number"], "--owner", board["owner"],
                   "--format", "json", "--limit", "2000").get("items", [])


def find_item(gh: Gh, board: dict, ref: str) -> dict | None:
    marker = f"job-radar:ref={ref}"
    return next((i for i in _items(gh, board) if marker in ((i.get("content") or {}).get("body") or "")), None)


def _edit(gh: Gh, board: dict, item_id: str, name: str, value) -> None:
    field = board["fields"].get(name)
    if field is None:
        raise KeyError(f"board has no field {name!r} (run setup-project)")
    args = ["project", "item-edit", "--id", item_id, "--project-id", board["id"], "--field-id", field["id"]]
    if field["options"]:
        option = field["options"].get(str(value).lower())
        if option is None:
            raise ValueError(f"{name} must be one of: {', '.join(FIELDS.get(name) or field['options'])}")
        args += ["--single-select-option-id", option]
    elif FIELDS.get(name) == DATE:
        args += ["--date", str(value)[:10]]
    else:
        args += ["--number", str(float(value))]
    gh(*args)


def set_role_fields(gh: Gh, ref: str, values: dict, close: bool = False, note: str = "") -> str:
    """Set fields on a role's card. `note` (the user's reason, e.g. why they skipped it) is logged
    with the stage change and posted as a comment on the issue, so the card shows it later."""
    board = load_board()
    if board is None:
        return "board not set up yet (python tools/board_sync.py setup-project --repo OWNER/REPO)"
    item = find_item(gh, board, ref)
    if item is None:
        return f"no board card for {ref} yet (it's created by the daily run; see state/board_queue.json)"
    for name, value in values.items():
        _edit(gh, board, item["id"], name, value)
        if not gh.dry_run and name in ("Stage", "Recommendation"):
            log_stage(ref, name, str(value), "claude", note)
    url = (item.get("content") or {}).get("url")
    if note and url:
        path = _body_file(f"**{', '.join(f'{k}: {v}' for k, v in values.items())}**. {note}")
        try:
            gh("issue", "comment", url, "--body-file", path)
        finally:
            Path(path).unlink(missing_ok=True)
    if (close or values.get("Stage") in FINAL_STAGES) and url:
        gh("issue", "close", url)
    closed = close or values.get("Stage") in FINAL_STAGES
    return f"{ref}: " + ", ".join(f"{k}={v}" for k, v in values.items()) + (" (closed)" if closed else "")


ARCHIVE_MAX = 40  # per run: each archive is a GraphQL call, and a big first backlog can trip GitHub's rate limit


def archive_skipped(gh: Gh, max_n: int = ARCHIVE_MAX, sleep=time.sleep) -> str:
    """Archive cards whose Stage is Skipped: they leave the board's views but aren't deleted (the Project's
    Archive keeps them, and they can be restored there). `item-list` never returns archived items, so
    running this daily is idempotent; what's over the cap waits for the next run."""
    board = load_board()
    if board is None:
        return "board not set up yet (python tools/board_sync.py setup-project --repo OWNER/REPO)"
    todo = [i for i in _items(gh, board) if i.get("stage") == "Skipped"]
    for i in todo[:max_n]:
        gh("project", "item-archive", board["number"], "--owner", board["owner"], "--id", i["id"])
        sleep(0.5)
    n = min(len(todo), max_n)
    return f"archived {n} Skipped card(s)" + (f", {len(todo) - n} left for the next run" if len(todo) > n else "")


FIT_START, FIT_END = "<!-- job-radar:fit -->", "<!-- /job-radar:fit -->"
TIER_LINE = re.compile(r"^- \*\*Tier \d\*\* \(score [^\n]*\)\n?", re.M)  # older cards carried the tier arithmetic
BLOCKER_NAMES = {"clearance": "Security clearance", "right_to_work": "Right to work", "language": "Language",
                 "location": "Location", "seniority": "Seniority", "other": "Other"}
WORK_JD = ROOT / "work" / "jd"


def fit_section(score: dict, scored_on: str = "") -> str:
    """The card's fit breakdown from a validated score.json: Matches / Partly / Doesn't match, with
    blockers (quoted from the ad) under Doesn't match. Fit and Recommendation are already board fields,
    so they aren't repeated. Requirement texts derive from a third-party JD and are escaped."""
    def group(met):
        return [f"- {md(m['requirement'])}" for m in score.get("must_haves", []) if m.get("met") == met]
    blockers = [f"- {BLOCKER_NAMES.get(b['type'], b['type'])}: \"{md(b['quote'])}\"" for b in score.get("blockers", [])]
    lines = [FIT_START]
    for heading, items in (("Matches", group("yes")), ("Partly", group("partial")),
                           ("Doesn't match", blockers + group("no"))):
        if items:
            lines += [f"**{heading}**", *items, ""]
    if score.get("injection_suspected"):
        lines += ["**Note:** this ad contains text aimed at AI tools; it was scored on its real content.", ""]
    lines.append(FIT_END)
    return "\n".join(lines)


def with_fit(body: str, section: str) -> str:
    """Replace the card's fit block, or insert it before the Role ID line; drop the old tier line."""
    body = TIER_LINE.sub("", body)
    if FIT_START in body and FIT_END in body:
        a, b = body.index(FIT_START), body.index(FIT_END) + len(FIT_END)
        return body[:a] + section + body[b:]
    at = body.find("Role ID:")
    return (body[:at] + section + "\n\n" + body[at:]) if at >= 0 else body.rstrip("\n") + "\n\n" + section + "\n"


def _set_body(gh: Gh, url: str, body: str) -> None:
    path = _body_file(body)
    try:
        gh("issue", "edit", url, "--body-file", path)
    finally:
        Path(path).unlink(missing_ok=True)


def set_fit_section(gh: Gh, ref: str, score: dict, scored_on: str = "") -> str:
    board = load_board()
    item = find_item(gh, board, ref) if board else None
    url = ((item or {}).get("content") or {}).get("url")
    if not url:
        return f"{ref}: no board card yet; fit breakdown not added"
    body = gh("issue", "view", url, "--json", "body", "--jq", ".body")
    _set_body(gh, url, with_fit(body, fit_section(score, scored_on)))
    return f"{ref}: fit breakdown on the card"


def refresh_bodies(gh: Gh) -> str:
    """Bring every role card up to date: drop the old tier line, add or refresh the fit breakdown
    from work/jd/<ref>/score.json where one exists (only validated scores are in scores.jsonl)."""
    scored = set()
    if (scores_file := ROOT / "data" / "scores.jsonl").exists():
        scored = {json.loads(l)["key"] for l in scores_file.read_text(encoding="utf-8").splitlines() if l.strip()}
    issues = json.loads(gh("issue", "list", "--label", "role", "--state", "all", "--limit", "2000",
                           "--json", "url,body") or "[]")
    changed = with_breakdown = 0
    for i in issues:
        body = i.get("body") or ""
        hit = re.search(r"job-radar:ref=([0-9a-f]{16})", body)
        new = TIER_LINE.sub("", body)
        score_file = WORK_JD / hit.group(1) / "score.json" if hit else None
        if hit and hit.group(1) in scored and score_file.exists():
            new = with_fit(new, fit_section(json.loads(score_file.read_text(encoding="utf-8"))))
            with_breakdown += 1
        if new != body:
            _set_body(gh, i["url"], new)
            changed += 1
    return f"updated {changed} cards ({with_breakdown} with a fit breakdown)"


# The board's views, as code: setup builds them and the session brief checks them, so every copy
# gets the same board. GitHub's API sets name, layout, filter and columns; it can't set sort or
# board grouping, so those are reported as one-time clicks (`sort`, `group`).
VIEWS = [
    {"name": "All Roles", "layout": "TABLE_LAYOUT", "filter": "",
     "fields": ["Title", "Stage", "Tier", "Fit", "Recommendation", "Sponsor", "Posted", "Referral"],
     "sort": [("Fit", "DESC")], "group": []},
    {"name": "Act now", "layout": "TABLE_LAYOUT", "filter": "is:open tier:T1 stage:New,Shortlisted -label:possibly-closed -recommendation:Skip posted:>=@today-14d",
     "fields": ["Title", "Stage", "Fit", "Recommendation", "Sponsor", "Posted", "Referral"],
     "sort": [("Posted", "DESC")], "group": []},
    {"name": "Pipeline", "layout": "BOARD_LAYOUT", "filter": "",
     "fields": ["Title", "Tier", "Fit", "Recommendation", "Sponsor", "Posted", "Referral"],
     "sort": [], "group": ["Stage"]},
]
API_KEYS = ("layout", "filter", "fields")   # what apply_views can set
CLICK_KEYS = ("sort", "group")             # what only the Project UI can set

DESIGN_QUERY = """query($login:String!,$n:Int!){user(login:$login){projectV2(number:$n){id
 views(first:20){nodes{id name layout filter fields(first:40){nodes{... on ProjectV2FieldCommon{name}}}
  verticalGroupByFields(first:3){nodes{... on ProjectV2FieldCommon{name}}}
  sortByFields(first:3){nodes{direction field{... on ProjectV2FieldCommon{name}}}}}}}}}"""


def views(gh: Gh, owner: str, number: str) -> list[dict]:
    """The board's views in VIEWS' shape, plus each view's node id."""
    data = gh_json(gh, "api", "graphql", "-f", f"query={DESIGN_QUERY}", "-f", f"login={owner}", "-F", f"n={number}")
    return [{"id": v["id"], "name": v["name"], "layout": v["layout"], "filter": v["filter"] or "",
             "fields": [f.get("name") for f in v["fields"]["nodes"]],
             "group": [f.get("name") for f in v["verticalGroupByFields"]["nodes"]],
             "sort": [(s["field"].get("name"), s["direction"]) for s in v["sortByFields"]["nodes"]]}
            for v in data["data"]["user"]["projectV2"]["views"]["nodes"]]


def _click_steps(spec: dict, have: dict) -> list[str]:
    steps = []
    if spec["sort"] and have.get("sort") != spec["sort"]:
        field, direction = spec["sort"][0]
        steps.append(f"'{spec['name']}': View menu -> Sort by -> {field} ({'descending' if direction == 'DESC' else 'ascending'}) -> Save view")
    if spec["group"] and have.get("group") != spec["group"]:
        steps.append(f"'{spec['name']}': View menu -> Column by -> {spec['group'][0]} -> Save view")
    return steps


def _same(key: str, have, want) -> bool:
    """Columns compare as a set: GitHub keeps existing columns in place and appends new ones, whatever
    order the API is given, so order differences are cosmetic and not drift."""
    return set(have or []) == set(want) if key == "fields" else have == want


def design_diff(gh: Gh) -> list[str]:
    """How your board's views differ from VIEWS ([] = in sync). Extra views of your own are fine."""
    board = load_board()
    if not board:
        return []
    have = {v["name"]: v for v in views(gh, board["owner"], board["number"])}
    diffs = []
    for spec in VIEWS:
        v = have.get(spec["name"])
        if v is None:
            diffs.append(f"view '{spec['name']}' is missing")
            continue
        changed = [k for k in API_KEYS if not _same(k, v[k], spec[k])] +                   [k for k in CLICK_KEYS if spec[k] and v[k] != spec[k]]
        if changed:
            diffs.append(f"view '{spec['name']}' differs ({', '.join(changed)})")
    return diffs


def apply_views(gh: Gh) -> str:
    """Create or update the board's views to match VIEWS; returns what's left to click."""
    board = load_board()
    if not board:
        return "board not set up yet"
    fields = _read_fields(gh, board["owner"], board["number"])
    have = {v["name"]: v for v in views(gh, board["owner"], board["number"])}
    changed, clicks = [], []
    for spec in VIEWS:
        ids = [fields[n]["id"] for n in spec["fields"] if n in fields]
        cfg = "configuration:{visibleFieldIds:[" + ",".join(json.dumps(i) for i in ids) + "]}"
        v = have.get(spec["name"])
        if v is None:
            out = gh_json(gh, "api", "graphql", "-f", "query=mutation{createProjectV2View(input:{projectId:"
                          f"{json.dumps(board['id'])},name:{json.dumps(spec['name'])},layout:{spec['layout']},{cfg}}})"
                          "{projectV2View{id}}}")
            v = {"id": out["data"]["createProjectV2View"]["projectV2View"]["id"], "filter": "", "fields": [],
                 "layout": spec["layout"]}
            changed.append(f"created '{spec['name']}'")
        if any(not _same(k, v.get(k), spec[k]) for k in API_KEYS):
            gh("api", "graphql", "-f", "query=mutation{updateProjectV2View(input:{viewId:"
               f"{json.dumps(v['id'])},layout:{spec['layout']},filter:{json.dumps(spec['filter'])},{cfg}}})"
               "{projectV2View{id}}}")
            changed.append(f"updated '{spec['name']}'")
        clicks += _click_steps(spec, v)
    msg = "; ".join(changed) or "views already match"
    if clicks:
        msg += "\nOne-time clicks GitHub's API can't do:\n  " + "\n  ".join(clicks)
    return msg


POSTED_RE = re.compile(r"^- Posted: (\d{4}-\d{2}-\d{2})$", re.M)
REF_RE = re.compile(r"job-radar:ref=([0-9a-f]{16})")


def posted_date(body: str, first_seen: dict[str, str]) -> str | None:
    """The posting date from the issue body, else the day the radar first saw the role."""
    if m := POSTED_RE.search(body or ""):
        return m.group(1)
    ref = REF_RE.search(body or "")
    return (first_seen.get(ref.group(1)) or None) if ref else None


def _first_seen() -> dict[str, str]:
    if not MATCHES.exists():
        return {}
    with open(MATCHES, encoding="utf-8") as fh:
        return {r["ref"]: (r.get("posted") or r.get("date") or "")[:10] for r in csv.DictReader(fh) if r.get("ref")}


def fill_new(gh: Gh) -> str:
    """Cards the scheduled run added have labels but no field values (it can't edit Projects)."""
    board = load_board()
    if board is None:
        return "board not set up yet"
    done = dated = 0
    seen = None
    for item in _items(gh, board):
        labels = set(item.get("labels") or [])
        if "role" not in labels:
            continue
        if "Posted" in board["fields"] and not item.get("posted"):
            seen = _first_seen() if seen is None else seen
            if (day := posted_date((item.get("content") or {}).get("body") or "", seen)):
                _edit(gh, board, item["id"], "Posted", day)
                dated += 1
        if item.get("stage"):
            continue
        tier = next((l.split("-")[1] for l in labels if l.startswith("tier-")), None)
        sponsor = next((REGISTER_TO_SPONSOR.get(l.split("-", 1)[1]) for l in labels if l.startswith("sponsor-")), None)
        _edit(gh, board, item["id"], "Stage", "New")
        if tier:
            _edit(gh, board, item["id"], "Tier", f"T{tier}")
        if sponsor:
            _edit(gh, board, item["id"], "Sponsor", sponsor)
        done += 1
    return f"filled {done} new cards, dated {dated}"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("what", choices=["roles", "status", "setup-project", "fill", "set", "stale", "backfill-map",
                                     "design-diff", "views", "refresh-bodies", "promote", "archive"])
    ap.add_argument("args", nargs="*", help="set: <ref> Field=Value …; promote: <ref> … (then run roles)")
    ap.add_argument("--repo", help="setup-project: OWNER/REPO of your private copy")
    ap.add_argument("--close", action="store_true", help="set: also close the role's issue")
    ap.add_argument("--note", default="", help="set: the reason, logged and posted as a comment on the issue")
    ap.add_argument("--dry-run", action="store_true", help="print the gh commands instead of running them")
    ap.add_argument("--max", type=int, help="max issues to create (default: board.max_per_run in config.json)")
    args = ap.parse_args(argv)
    gh = Gh(dry_run=args.dry_run)
    if args.what == "roles":
        cfg = json.loads(profile_path("config.json").read_text(encoding="utf-8")).get("board", {})
        created, left = sync_roles(gh, args.max or int(cfg.get("max_per_run", 40)),
                                   sleep=(lambda s: None) if args.dry_run else time.sleep)
        verb = "would create" if args.dry_run else "created"
        print(f"board: {verb} {created} role issues, {left} {'queued' if args.dry_run else 'still queued'}")
    elif args.what == "status":
        print(f"status: {sync_status(gh)}")
    elif args.what == "setup-project":
        if not args.repo:
            ap.error("setup-project needs --repo OWNER/REPO")
        print(setup_project(gh, args.repo))
        print(apply_views(gh))
    elif args.what == "fill":
        print(fill_new(gh))
    elif args.what == "stale":
        print(sync_stale(gh))
    elif args.what == "backfill-map":
        print(backfill_map(gh))
    elif args.what == "design-diff":
        print("\n".join(design_diff(gh)) or "board views match VIEWS")
    elif args.what == "views":
        print(apply_views(gh))
    elif args.what == "promote":
        print(promote(args.args, dry_run=args.dry_run))
    elif args.what == "refresh-bodies":
        print(refresh_bodies(gh))
    elif args.what == "archive":
        print(archive_skipped(gh, sleep=(lambda s: None) if args.dry_run else time.sleep))
    else:
        if len(args.args) < 2 or not all("=" in a for a in args.args[1:]):
            ap.error("usage: set <ref> Field=Value [Field=Value …]")
        values = dict(a.split("=", 1) for a in args.args[1:])
        print(set_role_fields(gh, args.args[0], values, close=args.close, note=args.note))
    return 0


if __name__ == "__main__":
    sys.exit(main())
