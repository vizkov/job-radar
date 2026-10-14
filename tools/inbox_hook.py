"""PostToolUse hook for the Gmail read tools: keeps the inbox-check bookkeeping without the model having to remember it.

Reads the hook JSON on stdin. Standard library only; always exits 0 and prints nothing (a hook must never block a session).

  get_thread / get_message  -> every message and thread id in the result goes into state/inbox_seen.json (opened = read)
  search_threads            -> if the query is `"<Company>" ...` for exactly one company that has an application awaiting
                               an answer, that role is stamped as checked today (state/inbox_checked.json)

Only ids and a date are stored, never mail text. Wired in .claude/settings.json.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import inbox_outcomes as io  # noqa: E402

ID_RE = re.compile(r'\\*"(?:id|threadId)\\*"\s*:\s*\\*"([0-9a-f]{12,32})\\*"')
QUOTED = re.compile(r'"([^"]+)"')


def opened_ids(tool_response) -> set[str]:
    """Message and thread ids in a get_thread/get_message result (whatever shape the connector returns)."""
    try:
        text = tool_response if isinstance(tool_response, str) else json.dumps(tool_response)
    except (TypeError, ValueError):
        return set()
    return set(ID_RE.findall(text))


def looks_failed(tool_response) -> bool:
    if isinstance(tool_response, dict) and (tool_response.get("is_error") or tool_response.get("isError")):
        return True
    return False


def company_of(query: str) -> str:
    """The single quoted company name of a per-role search, or '' (broad or multi-company searches stamp nothing)."""
    quoted = QUOTED.findall(query or "")
    if len(quoted) != 1 or re.search(r"\bOR\b|[{}]", query or ""):
        return ""
    return quoted[0].strip().lower()


def handle(payload: dict, seen_path: Path = io.SEEN, checked_path: Path = io.CHECKED, **pending_kw) -> str:
    name = str(payload.get("tool_name", ""))
    resp = payload.get("tool_response")
    if not name.startswith("mcp__") or "Gmail__" not in name or looks_failed(resp):
        return "ignored"
    if name.endswith(("__get_thread", "__get_message")):
        ids = opened_ids(resp)
        if ids:
            io.add_seen(sorted(ids), seen_path)
        return f"seen {len(ids)}"
    if name.endswith("__search_threads"):
        company = company_of((payload.get("tool_input") or {}).get("query", ""))
        if not company:
            return "broad search: nothing stamped"
        refs = [r["ref"] for r in io.pending(checked_path=checked_path, **pending_kw) if r["company"].lower() == company]
        if refs:
            io.mark_checked(refs, path=checked_path)
        return f"checked {len(refs)}"
    return "ignored"


def main() -> int:
    try:
        handle(json.load(sys.stdin))
    except Exception:  # noqa: BLE001 - a bookkeeping hook must never break the session
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
