"""Fetch the Workday boards from this PC and publish them for the daily run (the user, 2026-11-22: GitHub's runner is blocked by Cloudflare, a home address is served).

    python tools/workday_pc.py [--budget SECONDS] [--dry-run]

Runs the same paced fetch as the Action (`jobradar.workday_paced`: one shared gate, 2 s apart, backs off on 429, gives up after two refusals) on the boards
least recently fetched first, keeps the jobs whose title passes the radar's filter, merges them into the repo's `state/workday_jobs.json` and writes that
ONE file back with the GitHub contents API (`gh api`). No local git, no working-tree change: nothing here can conflict with the user's checkout or with the
Action's own commits. The next daily run reads the copy (`jobradar/workday_cache.py`). Scheduled by `tools/run_workday_pc.ps1`.
"""
from __future__ import annotations

import argparse
import asyncio
import base64
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
REPO_PATH = "state/workday_jobs.json"


def gh(*args: str, input_: str | None = None) -> str:
    r = subprocess.run(["gh", *args], capture_output=True, text=True, input=input_, encoding="utf-8")
    if r.returncode:
        raise RuntimeError(f"gh {' '.join(args[:3])} failed: {(r.stderr or r.stdout).strip()[:300]}")
    return r.stdout


def repo_slug() -> str:
    url = subprocess.run(["git", "-C", str(ROOT), "remote", "get-url", "origin"], capture_output=True, text=True).stdout.strip()
    return url.removesuffix(".git").split("github.com/")[-1].split("github.com:")[-1]


def remote_file(slug: str) -> tuple[dict, str | None]:
    try:
        meta = json.loads(gh("api", f"repos/{slug}/contents/{REPO_PATH}"))
    except RuntimeError as e:
        if "404" in str(e) or "Not Found" in str(e):
            return {}, None
        raise
    raw = gh("api", "-H", "Accept: application/vnd.github.raw", f"repos/{slug}/contents/{REPO_PATH}")
    return (json.loads(raw) if raw.strip() else {}), meta["sha"]


async def fetch(budget: float, cache: dict) -> tuple[dict, dict]:
    from jobradar import common, workday_cache
    boards = [(b["ats"], b["slug"], b["url"]) for b in json.loads((ROOT / "boards.json").read_text()) if b["ats"] == "workday"]
    tried = {u: v.get("fetched_at", "") for u, v in cache.items()}   # least recently fetched first
    res = await common.fetch_workday_boards(boards, tried, budget)
    fresh, stats = {}, {"ok": 0, "failed": 0, "deferred": 0}
    for url, r in res.items():
        if r.error.startswith("deferred"):
            stats["deferred"] += 1
        elif r.ok:
            stats["ok"] += 1
            fresh[url] = workday_cache.entry([j for j in r.jobs if common.title_matches(j.title)])
        else:
            stats["failed"] += 1
    return fresh, stats


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--budget", type=float, default=900.0, help="seconds of Workday requests (default 900)")
    ap.add_argument("--dry-run", action="store_true", help="fetch and report, publish nothing")
    a = ap.parse_args()
    from jobradar import workday_cache
    slug = repo_slug()
    cache, sha = remote_file(slug)
    fresh, stats = asyncio.run(fetch(a.budget, cache))
    jobs = sum(len(v["jobs"]) for v in fresh.values())
    print(f"fetched {stats['ok']} boards ({jobs} matching jobs), {stats['failed']} failed, {stats['deferred']} left for next time")
    if not fresh:
        print("nothing to publish (refused or no board served)")
        return 1
    cache.update(fresh)
    if a.dry_run:
        print("dry run: not published")
        return 0
    body = {"message": f"workday (PC): {stats['ok']} boards, {jobs} jobs",
            "content": base64.b64encode(workday_cache.dumps(cache).encode("utf-8")).decode(), "branch": "main"}
    if sha:
        body["sha"] = sha
    gh("api", "-X", "PUT", f"repos/{slug}/contents/{REPO_PATH}", "--input", "-", input_=json.dumps(body))
    print("published", REPO_PATH)
    return 0


if __name__ == "__main__":
    sys.exit(main())
