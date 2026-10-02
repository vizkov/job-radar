"""Validate what Claude wrote before anything uses it. No LLM here.

    python tools/jd_check.py score <ref> [--board]    # work/jd/<ref>/score.json -> data/scores.jsonl
    python tools/jd_check.py tailor <folder>          # profile/applications/<folder>/tailored.json

Claude's output is treated as untrusted too: a job description could have steered
it. `score` accepts only evidence IDs that exist in the career docs and blocker
quotes that appear verbatim in the JD. `tailor` accepts only bullets that map to
the user's own lines (by ID) and no URL/email/phone the user didn't write.
Exit code 1 with a list of problems when invalid.
"""
from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from jobradar.career import EMAIL_RE, PHONE_RE, URL_RE, Career, load_career, masters_cleared  # noqa: E402

sys.path.insert(0, str(ROOT / "tools"))
from cv_lint import tailored_issues  # noqa: E402

WORK = ROOT / "work" / "jd"
SCORES = ROOT / "data" / "scores.jsonl"
MET = {"yes", "partial", "no"}
BLOCKER_TYPES = {"clearance", "right_to_work", "language", "location", "seniority", "other"}
RECOMMENDATIONS = {"apply", "maybe", "skip"}
LEVELS = {"below", "at", "above"}  # the role's level against the user's record; optional, "below" lowers the ceiling
# The fit score is a judgement, but it may not float above what the must-have table supports (2026-10-02: a role
# whose table listed only the met requirements scored 85 while an ATS-style count gave 65-75%).
BLOCKER_PENALTY, LEVEL_PENALTY, FIT_SLACK = 15, 10, 8


def _norm(s: str) -> str:
    return " ".join((s or "").lower().split())


def check_score(data: dict, ref: str, jd_text: str, career: Career) -> list[str]:
    errs = []
    required = {"key", "fit_score", "must_haves", "blockers", "summary", "recommendation", "injection_suspected"}
    allowed = required | {"level"}
    if extra := set(data) - allowed:
        errs.append(f"unexpected fields: {sorted(extra)}")
    if missing := required - set(data):
        errs.append(f"missing fields: {sorted(missing)}")
        return errs
    if data["key"] != ref:
        errs.append(f"key {data['key']!r} is not this role ({ref})")
    if not isinstance(data["fit_score"], int) or isinstance(data["fit_score"], bool) or not 0 <= data["fit_score"] <= 100:
        errs.append("fit_score must be an integer 0-100")
    if data["recommendation"] not in RECOMMENDATIONS:
        errs.append(f"recommendation must be one of {sorted(RECOMMENDATIONS)}")
    if not isinstance(data["injection_suspected"], bool):
        errs.append("injection_suspected must be true or false")
    if not isinstance(data["summary"], str) or not data["summary"].strip() or len(data["summary"]) > 1500:
        errs.append("summary must be 1-1500 characters")
    if not jd_text.strip():
        errs.append("no JD text for this role: paste it into jd.txt and re-run jd_prep before scoring")
    mh = data["must_haves"]
    if not isinstance(mh, list) or not 1 <= len(mh) <= 30:
        errs.append("must_haves must be a list of 1-30 items")
        mh = []
    for i, m in enumerate(mh):
        if not isinstance(m, dict) or set(m) != {"requirement", "met", "evidence"}:
            errs.append(f"must_haves[{i}] needs exactly requirement, met, evidence")
            continue
        if not isinstance(m["requirement"], str) or not 0 < len(m["requirement"]) <= 300:
            errs.append(f"must_haves[{i}].requirement must be 1-300 characters")
        if m["met"] not in MET:
            errs.append(f"must_haves[{i}].met must be yes/partial/no")
        ev = m["evidence"] if isinstance(m["evidence"], list) else None
        if ev is None:
            errs.append(f"must_haves[{i}].evidence must be a list of IDs")
            continue
        for e in ev:
            if not career.has(str(e)):
                errs.append(f"must_haves[{i}] cites [{e}], which isn't in your career docs")
        if m["met"] in ("yes", "partial") and not ev:
            errs.append(f"must_haves[{i}] is marked {m['met']!r} but cites no evidence")
    bl = data["blockers"]
    if not isinstance(bl, list):
        errs.append("blockers must be a list")
        bl = []
    if "level" in data and data["level"] not in LEVELS:
        errs.append(f"level must be one of {sorted(LEVELS)}")
    if mh and isinstance(data["fit_score"], int) and not isinstance(data["fit_score"], bool):
        coverage = sum({"yes": 1.0, "partial": 0.5}.get(m.get("met"), 0.0) for m in mh if isinstance(m, dict)) / len(mh) * 100
        ceiling = coverage - BLOCKER_PENALTY * len(bl) - (LEVEL_PENALTY if data.get("level") == "below" else 0)
        if data["fit_score"] > ceiling + FIT_SLACK:
            errs.append(f"fit_score {data['fit_score']} is above what the must-haves support (coverage {coverage:.0f}%, "
                        f"ceiling {max(ceiling, 0):.0f} + {FIT_SLACK}): list every Basic Qualification (unmet ones as "
                        "'no'), or lower the score")
    jd_norm = _norm(jd_text)
    for i, b in enumerate(bl):
        if not isinstance(b, dict) or set(b) != {"type", "quote"}:
            errs.append(f"blockers[{i}] needs exactly type, quote")
            continue
        if b["type"] not in BLOCKER_TYPES:
            errs.append(f"blockers[{i}].type must be one of {sorted(BLOCKER_TYPES)}")
        q = _norm(b["quote"]) if isinstance(b["quote"], str) else ""
        if len(q) < 8 or q not in jd_norm:
            errs.append(f"blockers[{i}].quote must be copied verbatim from the JD (8+ characters)")
    return errs


def score_warnings(data: dict, jd_text: str) -> list[str]:
    """Hints, never errors: a must-have table with no gap on a long ad usually means requirements were left out."""
    warns = []
    mh = data.get("must_haves") or []
    m = re.search(r"basic qualifications(.*?)(preferred qualifications|$)", jd_text, re.I | re.S)
    quals = [ln for ln in (m.group(1).splitlines() if m else []) if ln.strip().startswith(("-", "•", "*"))]
    if len(quals) >= 5 and not any(x.get("met") in ("no", "partial") for x in mh if isinstance(x, dict)):
        warns.append(f"the ad lists {len(quals)} basic qualifications but no must-have is partial or no: "
                     "was every requirement listed, including the ones the user cannot show?")
    if len(quals) >= 6 and len(mh) < len(quals) // 2:
        warns.append(f"{len(mh)} must-haves for {len(quals)} basic qualifications: merging hides gaps; list each one")
    if "level" not in data:
        warns.append("no level (below|at|above): say whether the role's level is above the user's record")
    return warns


def upsert_score(record: dict, path: Path | None = None) -> None:
    path = path or SCORES  # resolved at call time, so tests can redirect it
    lines = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
    kept = [ln for ln in lines if ln.strip() and json.loads(ln).get("key") != record["key"]]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(kept + [json.dumps(record, ensure_ascii=False)]) + "\n", encoding="utf-8")


def cmd_score(ref: str, board: bool, gh=None) -> int:
    folder = WORK / ref
    score_file, jd_file, meta_file = folder / "score.json", folder / "jd.txt", folder / "meta.json"
    if not score_file.exists():
        print(f"missing {score_file.relative_to(ROOT)}")
        return 1
    try:
        data = json.loads(score_file.read_text(encoding="utf-8"))
    except ValueError as e:
        print(f"score.json is not valid JSON: {e}")
        return 1
    meta = json.loads(meta_file.read_text(encoding="utf-8")) if meta_file.exists() else {}
    jd_text = jd_file.read_text(encoding="utf-8") if jd_file.exists() else ""
    errs = check_score(data, ref, jd_text, load_career()) if isinstance(data, dict) else ["score.json must be an object"]
    if errs:
        print("INVALID score.json:\n" + "\n".join(f"  - {e}" for e in errs))
        return 1
    for w in score_warnings(data, jd_text):
        print(f"WARNING: {w}")
    missing = [m["requirement"] for m in data["must_haves"] if m["met"] == "no"]
    record = {"key": ref, "company": meta.get("company", ""), "title": meta.get("title", ""),
              "fit_score": data["fit_score"], "recommendation": data["recommendation"],
              **({"level": data["level"]} if "level" in data else {}),
              "blockers": sorted({b["type"] for b in data["blockers"]}), "missing": missing,
              "injection_suspected": data["injection_suspected"], "summary": data["summary"],
              "scored_at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    upsert_score(record)
    print(f"ok: {ref} fit {data['fit_score']} -> {data['recommendation']}"
          + (" (blockers: " + ", ".join(record["blockers"]) + ")" if record["blockers"] else "")
          + (" [injection suspected]" if data["injection_suspected"] else ""))
    if board:
        from board_sync import Gh, set_fit_section, set_role_fields  # tools/ is on sys.path as a script
        gh = gh or Gh()
        fields = {"Fit": str(data["fit_score"]), "Recommendation": data["recommendation"].capitalize()}
        if data["recommendation"] in TIER_FROM_SCORE:   # a scored Apply/Skip settles the rule-based guess; Maybe keeps it
            fields["Tier"] = TIER_FROM_SCORE[data["recommendation"]]
        print(set_role_fields(gh, ref, fields))
        print(set_fit_section(gh, ref, data, record["scored_at"][:10]))
    return 0


TIER_FROM_SCORE = {"apply": "T1", "skip": "T2"}
APPS = ROOT / "profile" / "applications"
_NUM = re.compile(r"\d+(?:[.,]\d+)?")
# Capitalised words that aren't the first word of a sentence, and acronyms: employer,
# product and tool names. A tailored line may only use names already in the career docs.
_NAME = re.compile(r"(?<![.!?:;]\s)(?<!^)\b([A-Z][A-Za-z0-9+#]*(?:[./-][A-Za-z0-9+#]+)*)")


def _in_text(term: str, text_norm: str) -> bool:
    """Whole-word presence: "Go" must not count as present because the CV says "good"."""
    return re.search(rf"(?<![\w+#]){re.escape(_norm(term))}(?![\w+#])", text_norm) is not None


def new_names(text: str, career_text: str) -> list[str]:
    known = _norm(career_text)
    return sorted({n for n in _NAME.findall(text.strip()) if not _in_text(n, known)})
SECTION_KINDS = {"P", "B", "E", "K"}   # summary, experience, education and skill lines may appear in résumé sections
COVER_KINDS = {"C", "S"}          # cover-letter paragraphs come from cover blocks or STAR stories


def _planted(text: str, allowed: set[str]) -> list[str]:
    """URLs / emails / phone numbers in `text` that the user never wrote."""
    found = [m.lower().rstrip(".,") for rx in (EMAIL_RE, URL_RE) for m in rx.findall(text)]
    found += [re.sub(r"\D", "", m) for m in PHONE_RE.findall(text)]
    return [f for f in found if f not in allowed]


def check_tailor(data: dict, career: Career) -> tuple[list[str], list[str]]:
    """Returns (errors, warnings)."""
    errs, warns = [], []
    allowed = {"key", "headline", "sections", "skills", "cover_letter"}
    optional = {"location"}   # per-copy header location (e.g. names the role's city); the user's decision
    if extra := set(data) - allowed - optional:
        errs.append(f"unexpected fields: {sorted(extra)}")
    if missing := allowed - set(data):
        return errs + [f"missing fields: {sorted(missing)}"], warns
    if not re.fullmatch(r"[0-9a-f]{16}", str(data["key"])):
        errs.append("key must be the role ID (16 hex characters)")
    contact = career.contact_tokens()
    if "location" in data:
        loc, master_loc = data["location"], career.contact.get("location", "")
        if not isinstance(loc, str) or not 0 < len(loc) <= 120:
            errs.append("location must be 1-120 characters")
        elif not loc.startswith(master_loc.split("·")[0].strip()):
            errs.append("location must start with the city and country in your master CV")
        elif _planted(loc, contact):
            errs.append("location contains contact details/links you didn't write")
    head = data["headline"]
    if not isinstance(head, str) or not 0 < len(head) <= 120:
        errs.append("headline must be 1-120 characters")
    elif (bad := _planted(head, contact)):
        errs.append(f"headline contains contact details/links you didn't write: {bad}")
    elif (names := new_names(head, career.raw_text)):
        errs.append(f"headline names things not in your career docs: {names}")

    def check_line(where: str, item, kinds: set[str]) -> None:
        if not isinstance(item, dict) or set(item) != {"source_id", "text"}:
            errs.append(f"{where} needs exactly source_id, text")
            return
        sid, text = str(item["source_id"]), item["text"]
        if not career.has(sid):
            errs.append(f"{where} cites [{sid}], which isn't in your career docs (no invented content)")
            return
        if sid[0] not in kinds:
            errs.append(f"{where} cites [{sid}]; only {'/'.join(sorted(kinds))} items belong here")
        source = career.items[sid].text
        if not isinstance(text, str) or not 0 < len(text) <= max(450, len(source)):   # never longer than its own master line
            errs.append(f"{where} text must be 1-450 characters (or no longer than its master line)")
            return
        if (bad := _planted(text, contact)):
            errs.append(f"{where} adds contact details/links you didn't write: {bad}")
        if (new_nums := sorted(set(_NUM.findall(text)) - set(_NUM.findall(source)))):
            errs.append(f"{where} [{sid}] has numbers not in your original line: {new_nums}")
        if (names := new_names(text, career.raw_text)):
            errs.append(f"{where} [{sid}] names things not in your career docs: {names}")
        ratio = difflib.SequenceMatcher(None, _norm(source), _norm(text)).ratio()
        if ratio < 0.45 and sid[0] != "S":  # condensing a whole STAR story is expected
            warns.append(f"{where} [{sid}] is heavily reworded ({ratio:.0%} similar): check it still says what you did")

    sections = data["sections"] if isinstance(data["sections"], list) else []
    if not sections:
        errs.append("sections must be a non-empty list")
    used = []
    for i, sec in enumerate(sections):
        if not isinstance(sec, dict) or set(sec) != {"heading", "bullets"}:
            errs.append(f"sections[{i}] needs exactly heading, bullets")
            continue
        if not isinstance(sec["heading"], str) or not 0 < len(sec["heading"]) <= 80 or _planted(sec["heading"], contact):
            errs.append(f"sections[{i}].heading must be 1-80 characters with no links/contact details")
        for j, b in enumerate(sec["bullets"] if isinstance(sec["bullets"], list) else []):
            check_line(f"sections[{i}].bullets[{j}]", b, SECTION_KINDS)
            if isinstance(b, dict):
                used.append(str(b.get("source_id")))
    if (dupes := sorted({u for u in used if used.count(u) > 1})):
        errs.append(f"lines used twice: {dupes}")
    for i, sk in enumerate(data["skills"] if isinstance(data["skills"], list) else []):
        if not isinstance(sk, str) or not sk.strip() or not _in_text(sk, _norm(career.raw_text)):
            errs.append(f"skills[{i}] {sk!r} doesn't appear in your career docs")
    cover_used = []
    for i, c in enumerate(data["cover_letter"] if isinstance(data["cover_letter"], list) else []):
        check_line(f"cover_letter[{i}]", c, COVER_KINDS)
        if isinstance(c, dict):
            cover_used.append(str(c.get("source_id")))
    if (dupes := sorted({u for u in cover_used if cover_used.count(u) > 1})):
        errs.append(f"cover-letter paragraphs used twice: {dupes}")
    lint_errs, lint_warns = tailored_issues(data, career)   # form and section rules: writing-rules.md
    return errs + lint_errs, warns + lint_warns


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def cmd_tailor(folder: str) -> int:
    app = Path(folder) if Path(folder).is_absolute() else APPS / folder
    src = app / "tailored.json"
    if not src.exists():
        print(f"missing {src}")
        return 1
    try:
        data = json.loads(src.read_text(encoding="utf-8"))
    except ValueError as e:
        print(f"tailored.json is not valid JSON: {e}")
        return 1
    career = load_career()
    errs, warns = check_tailor(data, career) if isinstance(data, dict) else (["tailored.json must be an object"], [])
    (app / "validated.sha256").unlink(missing_ok=True)
    ok, why = masters_cleared()
    if not ok:
        print(f"MASTERS NOT CLEARED: {why}.\nApplication drafts are only built or refreshed from clean masters. "
              "Run the master-update check (deterministic pass plus two fresh reviewers), fix what they find, "
              "then  python tools/master_drift.py clear")
        return 1
    if errs:
        print("INVALID tailored.json:\n" + "\n".join(f"  - {e}" for e in errs))
        return 1
    print("Changes from your master résumé (review before sending):\n")
    for sec in data["sections"]:
        print(f"## {sec['heading']}")
        for b in sec["bullets"]:
            orig = career.items[b["source_id"]].text
            mark = "  (unchanged)" if _norm(orig) == _norm(b["text"]) else ""
            print(f"  [{b['source_id']}] {b['text']}{mark}")
            if not mark:
                print(f"         was: {orig}")
    for w in warns:
        print(f"WARNING: {w}")
    (app / "validated.sha256").write_text(_digest(src), encoding="utf-8")
    print(f"\nok: validated; render with  python tools/render_resume.py {app.name}")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("score")
    s.add_argument("refs", nargs="+", metavar="ref",
                   help="one or more roles; with --board they share ONE read of the board (GitHub throttles bursts)")
    s.add_argument("--board", action="store_true", help="also set Fit/Recommendation on the board card")
    t = sub.add_parser("tailor")
    t.add_argument("folder")
    args = ap.parse_args(argv)
    if args.cmd == "score":
        gh = None
        if args.board:
            from board_sync import Gh
            gh = Gh()
        return max(cmd_score(ref, args.board, gh) for ref in args.refs)
    return cmd_tailor(args.folder)




if __name__ == "__main__":
    sys.exit(main())
