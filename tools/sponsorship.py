"""Visa sponsorship: record Claude's checked verdict for a role, with evidence. Standard library only.

    python tools/sponsorship.py record <ref> [--board]   # validate work/jd/<ref>/sponsorship.json, log it,
                                                        #   set the card's Sponsor field and evidence block
    python tools/sponsorship.py company "<company>"     # earlier verdicts for this employer (reuse research)

The register tag (data/registers) only says an employer holds a licence. Whether it will sponsor THIS
role for someone relocating is a judgement from the ad, the country's rules, the register and the
company's own pages; the `sponsorship-check` skill makes it, and this tool refuses what it can't back:

    {"key": "<ref>", "country": "GB", "verdict": "confirmed|likely|licensed|unclear|unlikely|no",
     "summary": "one or two sentences",
     "evidence": [{"kind": "ad|register|company_page|news|other", "text": "what it shows",
                   "quote": "verbatim from the ad (kind ad only)", "url": "https://… (web kinds)",
                   "date": "YYYY-MM-DD (when seen)"}]}

Rules: verdict in VERDICTS; 1-6 evidence items; an `ad` quote must appear verbatim in jd.txt;
`company_page`/`news`/`other` need an http(s) URL that is not LinkedIn, Indeed or Glassdoor;
`confirmed` needs an ad or company_page item; `no` needs an ad quote. Web text is third-party data.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))
from jobradar.matching import normalize_words  # noqa: E402  (stdlib-only)
from jobradar.mdsafe import md, md_url  # noqa: E402  (stdlib-only)

WORK = ROOT / "work" / "jd"
LOG = ROOT / "data" / "sponsorship.jsonl"
VERDICTS = {"confirmed": "Confirmed", "likely": "Likely", "licensed": "Licensed", "unclear": "Unclear",
            "unlikely": "Unlikely", "no": "No"}                       # verdict -> board Sponsor option
KINDS = {"ad", "register", "company_page", "news", "other"}
WEB_KINDS = {"company_page", "news", "other"}
BANNED = ("linkedin.com", "indeed.", "glassdoor.")
VISA_START, VISA_END = "<!-- job-radar:visa -->", "<!-- /job-radar:visa -->"


def _norm(s: str) -> str:
    return " ".join((s or "").lower().split())


def check(data: dict, ref: str, jd_text: str) -> list[str]:
    errs = []
    allowed = {"key", "country", "verdict", "summary", "evidence"}
    if extra := set(data) - allowed:
        errs.append(f"unexpected fields: {sorted(extra)}")
    if missing := allowed - set(data):
        return errs + [f"missing fields: {sorted(missing)}"]
    if data["key"] != ref:
        errs.append(f"key {data['key']!r} is not this role ({ref})")
    if data["verdict"] not in VERDICTS:
        errs.append(f"verdict must be one of {sorted(VERDICTS)}")
    if not re.fullmatch(r"[A-Z]{2}|REMOTE-EU", str(data["country"])):
        errs.append("country must be a 2-letter code (the country you'd move to)")
    if not isinstance(data["summary"], str) or not 0 < len(data["summary"]) <= 300:
        errs.append("summary must be 1-300 characters")
    ev = data["evidence"] if isinstance(data["evidence"], list) else []
    if not 1 <= len(ev) <= 6:
        errs.append("evidence must be a list of 1-6 items")
    jd = _norm(jd_text)
    for i, e in enumerate(ev):
        if not isinstance(e, dict) or e.get("kind") not in KINDS or not str(e.get("text", "")).strip():
            errs.append(f"evidence[{i}] needs a kind ({'/'.join(sorted(KINDS))}) and text")
            continue
        if e["kind"] == "ad":
            q = _norm(str(e.get("quote", "")))
            if len(q) < 8 or q not in jd:
                errs.append(f"evidence[{i}]: an ad quote must be copied verbatim from the job description")
        if e["kind"] in WEB_KINDS:
            url = str(e.get("url", ""))
            host = urlsplit(url).netloc.lower()
            if not re.match(r"^https?://", url) or not host:
                errs.append(f"evidence[{i}]: web evidence needs an http(s) URL")
            elif any(b in host for b in BANNED):
                errs.append(f"evidence[{i}]: LinkedIn, Indeed and Glassdoor are never used as sources")
    kinds = {e.get("kind") for e in ev if isinstance(e, dict)}
    if data["verdict"] == "confirmed" and not kinds & {"ad", "company_page"}:
        errs.append("'confirmed' needs the ad or the company's own page saying it sponsors")
    if data["verdict"] == "no" and "ad" not in kinds:
        errs.append("'no' needs a quote from the ad (otherwise use 'unlikely')")
    return errs


def visa_section(data: dict) -> str:
    """The card's short sponsorship block: verdict, one-line summary, evidence with links."""
    lines = [VISA_START, f"**Visa sponsorship: {VERDICTS[data['verdict']]}** ({md(data['country'])}). "
             f"{md(data['summary'])}"]
    for e in data["evidence"][:4]:
        src = f" ([source]({md_url(e['url'])}))" if e.get("url") else ""
        quote = f": \"{md(e['quote'])}\"" if e.get("quote") else ""
        lines.append(f"- {md(e['text'])}{quote}{src}")
    lines.append(VISA_END)
    return "\n".join(lines)


def with_visa(body: str, section: str) -> str:
    if VISA_START in body and VISA_END in body:
        a, b = body.index(VISA_START), body.index(VISA_END) + len(VISA_END)
        return body[:a] + section + body[b:]
    at = body.find("Role ID:")
    return (body[:at] + section + "\n\n" + body[at:]) if at >= 0 else body.rstrip("\n") + "\n\n" + section + "\n"


def upsert(record: dict, log: Path | None = None) -> None:
    log = log or LOG
    lines = log.read_text(encoding="utf-8").splitlines() if log.exists() else []
    kept = [ln for ln in lines if ln.strip() and json.loads(ln).get("key") != record["key"]]
    log.parent.mkdir(parents=True, exist_ok=True)
    log.write_text("\n".join(kept + [json.dumps(record, ensure_ascii=False)]) + "\n", encoding="utf-8")


def company_records(company: str, log: Path | None = None) -> list[dict]:
    log = log or LOG
    key = normalize_words(company)
    if not log.exists() or not key:
        return []
    out = []
    for line in log.read_text(encoding="utf-8").splitlines():
        if line.strip():
            r = json.loads(line)
            other = normalize_words(r.get("company", ""))
            if other == key or other.startswith(key + " ") or key.startswith(other + " "):
                out.append(r)
    return out


def record(ref: str, board: bool, gh=None) -> int:
    folder = WORK / ref
    src = folder / "sponsorship.json"
    if not src.exists():
        print(f"missing {src}")
        return 1
    try:
        data = json.loads(src.read_text(encoding="utf-8"))
    except ValueError as e:
        print(f"sponsorship.json is not valid JSON: {e}")
        return 1
    jd = (folder / "jd.txt").read_text(encoding="utf-8") if (folder / "jd.txt").exists() else ""
    meta = json.loads((folder / "meta.json").read_text(encoding="utf-8")) if (folder / "meta.json").exists() else {}
    errs = check(data, ref, jd) if isinstance(data, dict) else ["sponsorship.json must be an object"]
    if errs:
        print("INVALID sponsorship.json:\n" + "\n".join(f"  - {e}" for e in errs))
        return 1
    upsert({**data, "company": meta.get("company", ""), "title": meta.get("title", ""),
            "checked_at": datetime.now(timezone.utc).isoformat(timespec="seconds")})
    print(f"ok: {ref} sponsorship {data['verdict']} ({data['country']})")
    if board:
        import board_sync
        gh = gh or board_sync.Gh()
        print(board_sync.set_role_fields(gh, ref, {"Sponsor": VERDICTS[data["verdict"]]}))
        b = board_sync.load_board()
        item = board_sync.find_item(gh, b, ref) if b else None
        url = ((item or {}).get("content") or {}).get("url")
        if url:
            body = gh("issue", "view", url, "--json", "body", "--jq", ".body")
            board_sync._set_body(gh, url, with_visa(body, visa_section(data)))
            print(f"{ref}: sponsorship evidence on the card")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("record"); r.add_argument("ref"); r.add_argument("--board", action="store_true")
    c = sub.add_parser("company"); c.add_argument("company")
    args = ap.parse_args(argv)
    if args.cmd == "record":
        return record(args.ref, args.board)
    rows = company_records(args.company)
    for r in rows:
        print(f"{r['checked_at'][:10]}  {r['verdict']:9} {r.get('country', '')}  {r.get('title', '')[:50]}  {r['summary'][:90]}")
        for e in r["evidence"]:
            print(f"      - {e['kind']}: {e['text'][:90]} {e.get('url', '')}")
    if not rows:
        print(f"no earlier sponsorship checks for {args.company}")
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
