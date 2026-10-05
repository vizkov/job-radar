"""Cadence ledger: when each recurring job last ran, and what is due now.

STANDARD LIBRARY ONLY (the session brief imports it before any virtualenv is active).

The session brief prints a CADENCE block with one line per recurring job, always, so a job that is
overdue can't go silent. Jobs that Claude runs (they need Gmail or Chrome, which a hook cannot drive)
stamp themselves when they finish:

    python tools/cadence.py done inbox_check      # after the inbox-check skill
    python tools/cadence.py done post_discovery   # after a LinkedIn post sweep
    python tools/cadence.py done auto_score       # after the session's automatic scoring
    python tools/cadence.py done health           # after the health skill has dealt with the source problems
    python tools/cadence.py done cv_review        # after the cv-review skill
    python tools/cadence.py done views_check      # after updating VIEWS to match the live board views
    python tools/cadence.py done jd_cleanup       # stamped by tools/jd_cleanup.py itself (the hook runs it daily)
    python tools/cadence.py show                  # the ledger

Stamps live in work/.cadence.json (private, local). The radar search and the new-role additions are
read from what the GitHub Action already writes (digests/status.md, matches.csv, the issue map, the board).
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
JOBS = {"inbox_check": 20, "post_discovery": 20, "auto_score": 4, "views_check": 24,
        "health": 24, "cv_review": 168, "jd_cleanup": 48}   # name -> hours before it is due again


def _file(root: Path) -> Path:
    return root / "work" / ".cadence.json"


def load(root: Path = ROOT) -> dict:
    try:
        return json.loads(_file(root).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _naive(text: str) -> datetime | None:
    try:
        at = datetime.fromisoformat(text)
    except (TypeError, ValueError):
        return None
    return at.astimezone(timezone.utc).replace(tzinfo=None) if at.tzinfo else at


def last(name: str, root: Path = ROOT) -> datetime | None:
    return _naive(load(root).get(name, ""))


def done(name: str, root: Path = ROOT, now: datetime | None = None) -> str:
    if name not in JOBS:
        raise ValueError(f"unknown cadence job {name!r}; one of {sorted(JOBS)}")
    now = now or datetime.now(timezone.utc).replace(tzinfo=None)
    data = load(root)
    data[name] = now.isoformat(timespec="seconds")
    _file(root).parent.mkdir(parents=True, exist_ok=True)
    _file(root).write_text(json.dumps(data, indent=1, sort_keys=True), encoding="utf-8")
    return f"{name}: stamped {data[name]} UTC"


def is_due(name: str, now: datetime, root: Path = ROOT) -> bool:
    at = last(name, root)
    return at is None or now - at >= timedelta(hours=JOBS[name])


def when(name: str, now: datetime, root: Path = ROOT, fallback: datetime | None = None) -> str:
    at = last(name, root) or fallback
    if at is None:
        return "never run"
    hours = int((now - at).total_seconds() // 3600)
    ago = f"{hours}h ago" if hours < 48 else f"{hours // 24}d ago"
    return f"last ran {at:%Y-%m-%d %H:%M} UTC ({ago})"


def block(now: datetime, root: Path, *, radar_last: str, new_total: int, new_on_board: int, new_skip: int,
          new_waiting: int, queued: int, unscored_cards: int, auto_picks: int, awaiting: int,
          posts_enabled: bool, posts_fallback: datetime | None = None, views_drift: str | None = None,
          docs_review: str | None = None, cv_gaps: str | None = None, source_problems: int = 0,
          docs_review_job: bool = True,
          mail_scan: tuple[str, bool] | None = None) -> tuple[list[str], list[str]]:
    """(lines for the brief, names of the jobs that are due). Every job gets a line, due or not."""
    lines = ["- CADENCE (each recurring job and when it last ran). Run every one marked DUE, or tell the user in one "
             "line which you skipped and why; never skip one silently:"]
    due: list[str] = []
    # radar search: the GitHub Action runs it daily; the brief starts one when GitHub skips a slot
    stale = True
    try:
        stale = (now.date() - datetime.fromisoformat(radar_last[:10]).date()).days > 1
    except ValueError:
        pass
    lines.append(f"  - Radar search (GitHub Action, daily): last run {radar_last or 'unknown'} · "
                 + ("OVERDUE: check `health`" if stale else "ok"))
    # new roles -> board
    detail = f"{new_total} new since last session: {new_on_board} on the board, {new_skip} scored Skip (no card by design)"
    if new_waiting or queued:
        detail += f", {new_waiting} without a card yet (queue holds {queued}): run `board_sync.py roles`"
        lines.append(f"  - New roles to the board: {detail} · DUE")
        due.append("board_roles")
    else:
        lines.append(f"  - New roles to the board: {detail} · ok")
    # scoring
    if auto_picks or unscored_cards:
        lines.append(f"  - Scoring: {unscored_cards} board card(s) with no score, {auto_picks} picked for automatic scoring; "
                     f"{when('auto_score', now, root)} · DUE: score-roles on the AUTO-SCORE refs, then "
                     "`cadence.py done auto_score`")
        due.append("auto_score")
    else:
        lines.append(f"  - Scoring: every board card is scored; {when('auto_score', now, root)} · ok")
    # inbox
    if awaiting:
        state = "DUE: run `inbox-check`, then `cadence.py done inbox_check`" if is_due("inbox_check", now, root) else "ok"
        if state != "ok":
            due.append("inbox_check")
        lines.append(f"  - Inbox check (Gmail): {awaiting} application(s) await an answer; {when('inbox_check', now, root)} · {state}")
    else:
        lines.append("  - Inbox check (Gmail): no application awaits an answer · ok")
    # application mail: the Action's daily scan fills the ledger (tools/app_mail.py); a silent scan hides replies
    if mail_scan:
        lines.append(mail_scan[0])
        if mail_scan[1]:
            due.append("app_mail_scan")
    # LinkedIn post sweep
    if posts_enabled:
        if is_due("post_discovery", now, root):
            due.append("post_discovery")
            lines.append(f"  - LinkedIn post sweep: {when('post_discovery', now, root, posts_fallback)} · DUE: after "
                         "answering the first message (if they opened with a task, offer it in one line), run "
                         "`post-discovery`, then `cadence.py done post_discovery`")
        else:
            lines.append(f"  - LinkedIn post sweep: {when('post_discovery', now, root)} · ok")
    else:
        lines.append("  - LinkedIn post sweep: off (discovery.linkedin_posts.enabled is false)")
    # board views: the user edits filters in GitHub's UI; the code (VIEWS) must follow
    if views_drift:
        due.append("views_check")
        lines.append(f"  - Board views vs code: {views_drift} · DUE: run `board_sync.py design-diff`, then edit `VIEWS` in "
                     "tools/board_sync.py to match the live views (the user edits them in GitHub on purpose; restore with "
                     "`board_sync.py views` only if they say a change was a mistake), commit, "
                     "`cadence.py done views_check`")
    else:
        lines.append(f"  - Board views vs code: no drift; {when('views_check', now, root)} · ok")
    # health: failing or silent sources. The details are in the brief's Health list; this makes the check a job that
    # is run (or offered) every day until it has been dealt with, instead of a line that is easy to read past
    if source_problems:
        if is_due("health", now, root):
            due.append("health")
            lines.append(f"  - Health: {source_problems} source problem(s) in the last run; {when('health', now, root)} · DUE: "
                         "after answering the first message (if they opened with a task, offer it in one line), run `health`, "
                         "then `cadence.py done health`")
        else:
            lines.append(f"  - Health: {source_problems} source problem(s) in the last run; {when('health', now, root)} · ok")
    else:
        lines.append("  - Health: no source problems in the last run · ok")
    # CV review: recurring gaps across scored roles, at most once a week
    if cv_gaps:
        if is_due("cv_review", now, root):
            due.append("cv_review")
            lines.append(f"  - CV review: {cv_gaps}; {when('cv_review', now, root)} · DUE: offer the `cv-review` skill in one "
                         "line after the first message, then `cadence.py done cv_review`")
        else:
            lines.append(f"  - CV review: gaps listed; {when('cv_review', now, root)} · ok")
    else:
        lines.append("  - CV review: no recurring CV gaps · ok")
    # JD packet cleanup: the SessionStart hook runs tools/jd_cleanup.py daily; this line makes a silent failure visible
    if is_due("jd_cleanup", now, root):
        due.append("jd_cleanup")
        lines.append(f"  - JD packet cleanup: {when('jd_cleanup', now, root)} · DUE: run `python tools/jd_cleanup.py run` (it stamps itself)")
    else:
        lines.append(f"  - JD packet cleanup: {when('jd_cleanup', now, root)} · ok")
    # docs review: due once enough code changed since the last one. Part of the block (not a health note) so it does
    # not wait for the user to say "close the session"
    if not docs_review_job:
        pass   # the docs-review skill is maintainer-only: a copy without it has no such job
    elif docs_review:
        due.append("docs_review")
        lines.append(f"  - Docs review: {docs_review} · DUE: after answering the first message (if they opened with a task, "
                     "offer it in one line), run `docs-review`; it stamps itself (`work/.last_docs_review`)")
    else:
        lines.append("  - Docs review: not due (few code files changed since the last one) · ok")
    return lines, due


def main(argv=None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if args[:1] == ["done"] and len(args) == 2:
        try:
            print(done(args[1]))
        except ValueError as e:
            print(e)
            return 2
        return 0
    if args[:1] == ["show"]:
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        for name in JOBS:
            print(f"{name}: {when(name, now)}" + (" · DUE" if is_due(name, now) else ""))
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main())
