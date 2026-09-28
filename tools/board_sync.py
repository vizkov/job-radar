"""Sync job-radar with GitHub issues / the Projects board, via the `gh` CLI.

    python tools/board_sync.py roles  [--dry-run] [--max N]   # queued new roles -> one issue each
    python tools/board_sync.py status [--dry-run]             # create/update the pinned "Radar status" issue

Local only (your `gh` login needs the project scope: gh auth refresh -s project):
    python tools/board_sync.py setup-project --repo OWNER/REPO   # create the Project + fields, link the repo
    python tools/board_sync.py fill                              # set Stage/Tier/Sponsor on new cards from labels
    python tools/board_sync.py set <ref> Stage=Applied [Fit=72 …] [--close]

In GitHub Actions `gh` uses GITHUB_TOKEN (issues: write). Issues labelled `role`
are pulled onto the Project board by its built-in "Auto-add to project" workflow.
Every gh call passes arguments as a list (no shell), and all text goes in via
--body-file, so nothing from a job ad is ever interpreted by a shell.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from jobradar.paths import profile_path  # noqa: E402

QUEUE = ROOT / "state" / "board_queue.json"
STATUS_MD = ROOT / "digests" / "status.md"
STATUS_LABEL = "radar-status"
BOARD_FILE = ROOT / "profile" / "board.json"   # project coordinates, written by setup-project
FIELDS = {  # name -> single-select options, or None for a number field
    "Stage": ["New", "Shortlisted", "Applied", "Interview", "Offer", "Rejected", "Skipped"],
    "Tier": ["T1", "T2"],
    "Fit": None,
    "Recommendation": ["Apply", "Maybe", "Skip"],
    "Sponsor": ["Yes", "Unknown", "No"],
}
FINAL_STAGES = {"Offer", "Rejected", "Skipped"}
LABEL_COLORS = {"role": "0E8A16", "tier-1": "B60205", "tier-2": "FBCA04", "sponsor-yes": "0E8A16",
                "sponsor-unknown": "C5DEF5", "sponsor-no": "D93F0B", STATUS_LABEL: "5319E7"}
SPACING_SECONDS = 2.0  # GitHub throttles bursts of issue creation


class Gh:
    """Thin wrapper so tests can swap in a fake."""

    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run

    def __call__(self, *args: str) -> str:
        if self.dry_run:
            print("gh " + " ".join(args))
            return ""
        return subprocess.run(["gh", *args], check=True, capture_output=True, text=True).stdout.strip()


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
            gh(*args)
        finally:
            Path(path).unlink(missing_ok=True)
        created += 1
        if not gh.dry_run:  # persist after each success so a crash never duplicates cards
            QUEUE.write_text(json.dumps(queue[created:], indent=1, ensure_ascii=False), encoding="utf-8")
        sleep(SPACING_SECONDS)
    return created, len(queue) - created


def sync_status(gh: Gh) -> str:
    """Edit the open "Radar status" issue, or create and pin it."""
    if not STATUS_MD.exists():
        return "no digests/status.md (run radar.py first)"
    path = _body_file(STATUS_MD.read_text(encoding="utf-8"))
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
    same title is reused instead of creating a duplicate."""
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
        args += ["--data-type", "NUMBER"] if options is None else \
                ["--data-type", "SINGLE_SELECT", "--single-select-options", ",".join(options)]
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
    else:
        args += ["--number", str(float(value))]
    gh(*args)


def set_role_fields(gh: Gh, ref: str, values: dict, close: bool = False) -> str:
    board = load_board()
    if board is None:
        return "board not set up yet (python tools/board_sync.py setup-project --repo OWNER/REPO)"
    item = find_item(gh, board, ref)
    if item is None:
        return f"no board card for {ref} yet (it's created by the daily run; see state/board_queue.json)"
    for name, value in values.items():
        _edit(gh, board, item["id"], name, value)
    if close or values.get("Stage") in FINAL_STAGES:
        url = (item.get("content") or {}).get("url")
        if url:
            gh("issue", "close", url)
    return f"{ref}: " + ", ".join(f"{k}={v}" for k, v in values.items()) + (" (closed)" if close else "")


def fill_new(gh: Gh) -> str:
    """Cards the daily run added have labels but no field values (it can't edit Projects)."""
    board = load_board()
    if board is None:
        return "board not set up yet"
    done = 0
    for item in _items(gh, board):
        labels = set(item.get("labels") or [])
        if "role" not in labels or item.get("stage"):
            continue
        tier = next((l.split("-")[1] for l in labels if l.startswith("tier-")), None)
        sponsor = next((l.split("-")[1].capitalize() for l in labels if l.startswith("sponsor-")), None)
        _edit(gh, board, item["id"], "Stage", "New")
        if tier:
            _edit(gh, board, item["id"], "Tier", f"T{tier}")
        if sponsor:
            _edit(gh, board, item["id"], "Sponsor", sponsor)
        done += 1
    return f"filled {done} new cards"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("what", choices=["roles", "status", "setup-project", "fill", "set"])
    ap.add_argument("args", nargs="*", help="set: <ref> Field=Value …")
    ap.add_argument("--repo", help="setup-project: OWNER/REPO of your private copy")
    ap.add_argument("--close", action="store_true", help="set: also close the role's issue")
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
    elif args.what == "fill":
        print(fill_new(gh))
    else:
        if len(args.args) < 2 or not all("=" in a for a in args.args[1:]):
            ap.error("usage: set <ref> Field=Value [Field=Value …]")
        values = dict(a.split("=", 1) for a in args.args[1:])
        print(set_role_fields(gh, args.args[0], values, close=args.close))
    return 0


if __name__ == "__main__":
    sys.exit(main())
