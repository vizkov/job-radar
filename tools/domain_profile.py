"""Which domains does the user's record back, and with which CV lines and stories?

    python tools/domain_profile.py validate   # check profile/domains.json against the masters (exit 1 on problems); stamps it on success
    python tools/domain_profile.py status     # is domains.json missing, or older than the masters? (exit 1 if so)
    python tools/domain_profile.py lead <domain|sector>   # the IDs a tailored CV and letter lead with for that domain or sector

`profile/domains.json` is written by the `domain-profile` skill from a quiz with the user plus the masters. This tool is the
deterministic half: every ID the file cites must exist in the masters, a `strong` domain needs at least two pieces of evidence, and
lead IDs must be evidence. It never edits a master. Consumers (score-roles, tailor-application, tiering by sector) read the small
JSON, not the masters, so they pay for the extraction only when the masters change.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from jobradar.career import load_career, masters_digest  # noqa: E402
from jobradar.paths import profile_path  # noqa: E402

STRENGTHS = ("strong", "moderate", "thin")
ANSWERS = ("yes", "no", "unsure")


def domains_path() -> Path:
    return profile_path("domains.json")


def problems(data: dict, career) -> list[str]:
    out: list[str] = []
    for area, q in (data.get("quiz") or {}).items():
        if q.get("answer") not in ANSWERS:
            out.append(f"quiz '{area}': answer must be one of {ANSWERS}")
    domains = data.get("domains") or {}
    if not domains:
        out.append("no domains listed")
    for name, d in domains.items():
        evidence, lead = d.get("evidence") or [], d.get("lead_ids") or []
        if d.get("strength") not in STRENGTHS:
            out.append(f"{name}: strength must be one of {STRENGTHS}")
        for i in evidence:
            if not career.has(i):
                out.append(f"{name}: evidence [{i}] is not in the masters")
        for i in lead:
            if i not in evidence:
                out.append(f"{name}: lead ID [{i}] is not in its evidence list")
        if d.get("strength") == "strong" and len(set(evidence)) < 2:
            out.append(f"{name}: 'strong' needs at least two pieces of evidence")
        if not d.get("not_claimed") and d.get("strength") != "thin":
            out.append(f"{name}: list what is NOT claimed (even if 'nothing beyond the evidence')")
    return out


def load() -> dict | None:
    p = domains_path()
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def stale() -> str:
    data = load()
    if data is None:
        return "profile/domains.json is missing: run the domain-profile skill"
    if data.get("masters_digest") != masters_digest():
        return "the masters changed since domains.json was built: re-run the domain-profile skill (it only re-asks what is unanswered)"
    return ""


def lead_ids(data: dict, key: str) -> list[str]:
    """Lead IDs for a domain name or a sector tag, strongest domain first, no repeats."""
    key = key.lower()
    rank = {s: i for i, s in enumerate(STRENGTHS)}
    hits = [d for n, d in (data.get("domains") or {}).items() if n.lower() == key or key in [s.lower() for s in d.get("sectors") or []]]
    out: list[str] = []
    for d in sorted(hits, key=lambda d: rank.get(d.get("strength"), 9)):
        out += [i for i in d.get("lead_ids") or [] if i not in out]
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("action", choices=["validate", "status", "lead"])
    ap.add_argument("key", nargs="?")
    args = ap.parse_args(argv)
    if args.action == "status":
        msg = stale()
        print(msg or "domains.json is current with the masters")
        return 1 if msg else 0
    data = load()
    if data is None:
        print("profile/domains.json is missing: run the domain-profile skill")
        return 1
    if args.action == "lead":
        if not args.key:
            ap.error("lead needs a domain or sector name")
        ids = lead_ids(data, args.key)
        print(" ".join(ids) if ids else f"no domain or sector '{args.key}' in domains.json")
        return 0 if ids else 1
    found = problems(data, load_career())
    if found:
        print("domains.json has problems:\n- " + "\n- ".join(found))
        return 1
    data["masters_digest"], data["built"] = masters_digest(), date.today().isoformat()
    domains_path().write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"domains.json is valid against the masters ({len(data['domains'])} domains) and stamped")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
