"""Which applications no longer match the master career documents?

    python tools/master_drift.py            # every application folder with a tailored.json; submitted ones are listed, not checked
    python tools/master_drift.py --all      # also check the submitted ones (STALE / DIFFERS as for any other)
    python tools/master_drift.py status     # are the masters cleared by the master-update check?
    python tools/master_drift.py clear      # record the masters as cleared (only after the check found nothing left to fix)
    python tools/master_drift.py general    # what changed in the master CV since the general resume (profile/general-resume/) was last reviewed
    python tools/master_drift.py general-done   # record the general resume as reviewed against the master CV as it is now

Tailored lines are copies of master lines (P/B/K/E in the CV, C/S in the letter). When the user
changes the master CV, cover blocks or stories, an application built earlier may be stale. Per
application this prints:

  * STALE: the master files changed after resume.pdf was rendered
  * MISSING: a cited ID no longer exists in the master
  * DIFFERS: the tailored text is under 90% similar to the master line (a deliberate condensation
    or relabel is normal; a master edit is what the reviewer should look for)

An application whose role has been applied to (board stage Applied, Interview, Offer or Rejected, from data/pipeline_log.jsonl)
is not refreshed: its PDFs are the record of what was sent, and rebuilding them would overwrite that record while changing
nothing the employer has. Those are printed as SUBMITTED, with only a MISSING note (a master line the sent version cites no
longer exists) and no STALE / DIFFERS, unless --all is given.

Output is candidates for judgement (the `master-update` skill), not verdicts. Read-only.
"""
from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from jobradar.career import career_dir, clear_masters, cover_blocks_stale, cover_sync_message, load_career, masters_cleared  # noqa: E402

APPS = ROOT / "profile" / "applications"
GENERAL = ROOT / "profile" / "general-resume"   # the untargeted CV: not an application, so not in APPS
SNAPSHOT = "master_lines.json"                  # in GENERAL: the master CV lines as they were when it was last reviewed
CV_KINDS = ("P", "B", "K", "E")
MASTER_FILES = ("master_resume.md", "cover_blocks.md", "stories.md")
SIMILAR = 0.90
LOG = ROOT / "data" / "pipeline_log.jsonl"
SUBMITTED = {"Applied", "Interview", "Offer", "Rejected"}   # stages that mean the application was sent


def stages(log: Path | None = None) -> dict[str, str]:
    """ref -> latest board stage, from the stage-change log (the last Stage entry per role wins)."""
    log = log or LOG
    out: dict[str, str] = {}
    if log.exists():
        for line in log.read_text(encoding="utf-8").splitlines():
            try:
                r = json.loads(line)
            except ValueError:
                continue
            if r.get("field") == "Stage" and r.get("ref") and r.get("value"):
                out[r["ref"]] = r["value"]
    return out


def check_app(app: Path, career, master_mtime: float) -> dict:
    data = json.loads((app / "tailored.json").read_text(encoding="utf-8"))
    lines = [b for s in data.get("sections", []) for b in s.get("bullets", [])] + data.get("cover_letter", [])
    missing = sorted({b["source_id"] for b in lines if not career.has(b["source_id"])})
    differs = []
    for b in lines:
        if career.has(b["source_id"]):
            src = career.items[b["source_id"]].text
            ratio = difflib.SequenceMatcher(None, src.lower(), b["text"].lower()).ratio()
            if ratio < SIMILAR:
                differs.append((b["source_id"], round(ratio * 100)))
    pdf = app / "resume.pdf"
    stale = pdf.exists() and master_mtime > pdf.stat().st_mtime
    return {"folder": app.name, "key": data.get("key", ""), "stale": stale, "missing": missing, "differs": differs}


def cv_fingerprints(career) -> dict[str, str]:
    """id -> hash of each master CV line (cover blocks and stories are not part of a general resume)."""
    return {i: hashlib.sha256(" ".join(item.text.split()).encode("utf-8")).hexdigest()[:16]
            for i, item in career.items.items() if i.startswith(CV_KINDS)}


def general_report(career, folder: Path) -> list[str]:
    """Lines describing how the master CV moved since the general resume was reviewed. Judging what matters is Claude's job."""
    src = folder / "tailored.json"
    if not src.exists():
        return ["no general resume (profile/general-resume/tailored.json)"]
    data = json.loads(src.read_text(encoding="utf-8"))
    used = {b["source_id"] for s in data.get("sections", []) for b in s.get("bullets", [])}
    now = cv_fingerprints(career)
    try:
        then = json.loads((folder / SNAPSHOT).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return ["general resume: never reviewed against the master CV (run general-done after reviewing it)",
                "  master lines it leaves out: " + (", ".join(sorted(set(now) - used)) or "none")]
    new = sorted(set(now) - set(then))
    changed = sorted(i for i in set(now) & set(then) if now[i] != then[i])
    removed = sorted(set(then) - set(now))
    if not (new or changed or removed):
        return ["general resume: no master CV change since its last review"]
    out = ["general resume: the master CV changed since its last review"]
    if new:
        out.append("  NEW master lines: " + ", ".join(new))
    if changed:
        out.append("  CHANGED: " + ", ".join(f"{i} ({'on it' if i in used else 'not on it'})" for i in changed))
    if removed:
        out.append("  REMOVED: " + ", ".join(f"{i} ({'STILL ON IT' if i in used else 'not on it'})" for i in removed))
    return out


def general_done(career, folder: Path) -> str:
    if not (folder / "tailored.json").exists():
        return "no general resume (profile/general-resume/tailored.json)"
    (folder / SNAPSHOT).write_text(json.dumps(cv_fingerprints(career), indent=1, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    return "general resume recorded as reviewed against the master CV"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("action", nargs="?", choices=["list", "status", "clear", "general", "general-done"], default="list")
    ap.add_argument("--all", action="store_true", help="also check applications that were already submitted")
    args = ap.parse_args()
    if args.action == "status":
        ok, why = masters_cleared()
        print("masters cleared: applications may be built or refreshed" if ok else f"masters NOT cleared: {why}")
        return 0 if ok else 1
    if args.action == "clear":
        if stale := cover_blocks_stale():
            print(cover_sync_message(stale))
            return 1
        print(f"masters recorded as cleared ({clear_masters()[:12]}): run this only after the master-update check found nothing left to fix")
        return 0
    if args.action in ("general", "general-done"):
        career = load_career()
        print("\n".join(general_report(career, GENERAL)) if args.action == "general" else general_done(career, GENERAL))
        return 0
    career = load_career()
    master_mtime = max((career_dir() / f).stat().st_mtime for f in MASTER_FILES if (career_dir() / f).exists())
    apps = sorted(p for p in APPS.glob("*/") if (p / "tailored.json").exists()) if APPS.exists() else []
    if not apps:
        print("no tailored applications")
        return 0
    stage_of, sent = stages(), 0
    for app in apps:
        r = check_app(app, career, master_mtime)
        stage = stage_of.get(r["key"], "")
        if stage in SUBMITTED and not args.all:
            sent += 1
            print(f"{r['folder']}: SUBMITTED ({stage}): the PDFs are the record of what was sent; not refreshed")
            if r["missing"]:
                print(f"  note: the master no longer has {', '.join(r['missing'])}, which the sent version cites")
            continue
        flags = ("STALE " if r["stale"] else "") + ("MISSING " if r["missing"] else "")
        print(f"{r['folder']}: {flags or 'ok '}".rstrip())
        if r["missing"]:
            print(f"  MISSING ids: {', '.join(r['missing'])}")
        if r["differs"]:
            print("  DIFFERS from master (id, % similar): " + ", ".join(f"{i} {p}" for i, p in r["differs"]))
    if sent:
        print(f"({sent} submitted application(s) listed, not checked; --all checks them too)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
