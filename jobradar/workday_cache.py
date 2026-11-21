"""Workday jobs fetched by the user's PC, read by the Action (the user, 2026-11-22, "ok": GitHub's runner address is blocked by Cloudflare, a home address is served).

`tools/workday_pc.py` (a scheduled task on the PC) fetches the Workday boards at a polite pace and pushes `state/workday_jobs.json` to the repo through the
GitHub contents API (one file, no git on the PC). `AtsSource` uses a board's copy when the runner itself could not fetch it and the copy is at most
`workday_cache_days` (default 3) old; an older copy is an error on the board's unit, so a PC that is off shows up as a failing source, not as silence.
File shape: {url: {"fetched_at": iso, "jobs": [Job dumps]}}. Only jobs whose title passes the radar's title filter are kept (a few per board).
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

PATH = Path(__file__).resolve().parent.parent / "state" / "workday_jobs.json"


def load(path: Path = PATH) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def dumps(cache: dict) -> str:
    return json.dumps(cache, indent=1, sort_keys=True, ensure_ascii=False) + "\n"


def entry(jobs: list, now: datetime | None = None) -> dict:
    when = (now or datetime.now(timezone.utc)).isoformat(timespec="seconds")
    return {"fetched_at": when, "jobs": [j.model_dump(mode="json") for j in jobs]}


def age_days(item: dict, now: datetime | None = None) -> float | None:
    try:
        then = datetime.fromisoformat(item["fetched_at"])
    except (KeyError, ValueError, TypeError):
        return None
    return ((now or datetime.now(timezone.utc)) - then).total_seconds() / 86400


def jobs_of(item: dict) -> list:
    from ats_scrapers.models import Job
    out = []
    for d in item.get("jobs", []):
        try:
            out.append(Job.model_validate(d))
        except Exception:
            continue   # one bad row must not lose the board
    return out
