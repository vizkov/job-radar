"""Role cards for the GitHub Projects board.

Each new role becomes one GitHub issue in the private repo; the Project's built-in
"Auto-add to project" workflow (filter `is:issue label:role`) puts it on the board.
The daily workflow only has GITHUB_TOKEN, which can create issues but not edit a
user-owned Project, so board *fields* (Status, Fit, …) are set later by Claude via
the user's local `gh` login (tools/board_sync.py).

A role's `ref` (16 hex chars) is the stable ID that links its issue, its row in
data/matches.csv, and its score / tailored résumé. It is a hash of the dedupe key,
so the same role seen on several sources has one ref.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from jobradar.dedupe import Group, primary_country as _primary
from jobradar.mdsafe import md, md_url

MARKER = "<!-- job-radar:ref={ref} -->"
MARKER_RE = re.compile(r"<!-- job-radar:ref=([0-9a-f]{16}) -->")
_CONTROL = re.compile(r"[\x00-\x1f\x7f]")


def role_ref(key: str) -> str:
    return hashlib.sha1(key.encode()).hexdigest()[:16]


def _plain(text: str, limit: int) -> str:
    """Issue titles aren't markdown, but must be one line and bounded."""
    t = " ".join(_CONTROL.sub(" ", text or "").split())
    return t if len(t) <= limit else t[: limit - 1] + "…"


def primary_country(g: Group) -> str:
    return _primary(g.best.countries)


def sponsor_status(g: Group) -> str | None:
    sp = g.tags.get("sponsor") or {}
    cc = primary_country(g)
    tag = sp.get("uk") if cc == "GB" else sp.get("nl") if cc == "NL" else None
    return getattr(tag, "status", None)


def payload(g: Group) -> dict:
    p, tier, score = g.best, g.tags.get("tier", 2), g.tags.get("score", "")
    ref, cc = role_ref(g.key), primary_country(g)
    company = p.company_canonical or p.company or "(employer not disclosed)"
    title = _plain(f"{company} — {p.title} ({cc})", 200)  # tier is a board field and a label, not title text
    lines = [f"**{md(company)}** — {md(p.location) or cc}", "",
             f"[Open the job posting]({md_url(p.url)})", "",
             f"- **Tier {tier}** (score {score}: {md(' '.join(g.tags.get('reasons', [])))})"]
    sp = g.tags.get("sponsor") or {}
    for code, key, label in (("GB", "uk", "UK sponsor"), ("NL", "nl", "NL sponsor")):
        if code in p.countries and key in sp:
            lines.append(f"- {label}: {md(str(sp[key]))}")
    if p.posted_at:
        lines.append(f"- Posted: {p.posted_at.date().isoformat()}")
    lines.append(f"- Found on: {p.source}")
    if g.also:
        lines.append("- Also on: " + ", ".join(f"[{md(a.source)}]({md_url(a.url)})" for a in g.also[:5]))
    lines += ["", f"Role ID: `{ref}`", MARKER.format(ref=ref)]
    labels = ["role", f"tier-{tier}"]
    if cc:
        labels.append(f"country-{cc}")
    if (s := sponsor_status(g)):
        labels.append(f"sponsor-{s}")
    return {"ref": ref, "title": title, "body": "\n".join(lines), "labels": labels}


def select_for_board(new: list[Group], cfg: dict, baseline: bool) -> list[Group]:
    if not cfg.get("enabled", False):
        return []
    tiers = set(cfg.get("baseline_tiers", [1]) if baseline else cfg.get("tiers", [1, 2]))
    return [g for g in new if g.tags.get("tier") in tiers
            and (g.best.company_canonical or cfg.get("include_outside", False))]


def ref_last_seen(seen: dict) -> dict[str, str]:
    """ref -> last date the role was seen on any source (from seen.json's content keys)."""
    out: dict[str, str] = {}
    for key, day in seen.items():
        if key.startswith("c:"):
            ref = role_ref(key)
            if day > out.get(ref, ""):
                out[ref] = day
    return out


def stale_refs(board_refs, seen: dict, today: str, days: int) -> tuple[list[str], list[str]]:
    """(refs not seen for `days`+ days, refs seen again today). Roles pruned from
    seen.json (unseen for 120 days) count as stale."""
    from datetime import date, timedelta
    cutoff = (date.fromisoformat(today) - timedelta(days=days)).isoformat()
    last = ref_last_seen(seen)
    stale = sorted(r for r in board_refs if last.get(r, "") < cutoff)
    alive = sorted(r for r in board_refs if last.get(r) == today)
    return stale, alive


def load_queue(path: Path) -> list[dict]:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else []


def save_queue(path: Path, queue: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(queue, indent=1, ensure_ascii=False), encoding="utf-8")


def enqueue(queue: list[dict], payloads: list[dict]) -> list[dict]:
    have = {q["ref"] for q in queue}
    return queue + [p for p in payloads if p["ref"] not in have]
