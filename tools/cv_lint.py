"""Mechanical form checks for CV and cover-letter text. No LLM here.

    python tools/cv_lint.py master              # the master CV + cover blocks: register problems in the lines
    python tools/cv_lint.py <application folder> # a tailored.json: register + section rules

The rules are in .claude/skills/tailor-application/writing-rules.md. This finds what a pattern can find (meta-commentary,
hedges, dangling hyphens, stacked hedges, repeated phrases, capitalisation, missing static sections or skills rows, a role cut
too thin, an achievement that restates an experience bullet, a Profile that is mostly the master's text). Tone, tense and whether a section does its job are the copy-editor
reviewer's (application-review). Returns (errors, warnings) of plain strings; jd_check.py tailor fails on the errors.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from jobradar.career import Career, load_career  # noqa: E402

# (pattern, message): a CV or letter line must not contain these.
BANNED = [
    (r"\([^)]*\b(too|not yet|yet to|unmeasured|no measured|early days)\b[^)]*\)", "a parenthetical that admits a limit: the stories carry limits, the CV does not"),
    (r"\b(afterwards|came (later|first|before|after)|followed later)\b", "chronology aside: belongs in a story"),
    (r"\((?:from|of|in|at) other [^)]*\)|,\s*from other \w+\b", "a parenthetical about where people came from: usually implied, cut it"),
    (r"\bfrom (?:about|around|roughly|approximately) .{3,40} to (?:about|around|roughly|approximately)\b", "informal \"from about X to about Y\": state the result once"),
    (r"\b\w+-\s+and\s+\w+-\w+", "dangling hyphen (\"passenger- and customer-data\"): drop the hyphens"),
    # Casual talk (the user's rule, 2026-10-01): a draft is written prose, not speech.
    (r"\b(I|we) (?:do not|don't|won't|will not|can't|cannot) (?:have|know|make|claim)\b", "spoken disclaimer (\"I don't have ...\"): state what was done; limits belong in the stories"),
    (r"\byet\s*[.;,)]|\b(?:a lot|kind of|sort of|pretty (?:much|good)|really|basically)\b|\bmuch (?:less|more|faster|better)\b", "casual phrasing (\"yet\", \"a lot\", \"much less\", \"really\"): write it as plain, specific prose"),
]
# Decided wording (\"expedited\", \"go-live fast approaching\" ...) is data, not code: writing-rules.md section 7, read by the reviewers.
# Only in prose lines (P, B, C, S): the acronym belongs in Skills.
RAG_PROSE = re.compile(r"\(RAG\)|\bRAG\b")
STACKED_HEDGE = re.compile(r"\b(about|around|approximately|roughly)\b", re.I)
LABEL_ONLY = re.compile(r"^\s*(?:\w+\s+){0,2}briefed\b", re.I)
MEDIUM = re.compile(r"medium\.com", re.I)
# Soft-skill filler (the user's rule, 2026-10-01): every CV says it, a filter matches nothing on it, and only evidence counts.
FILLER = re.compile(r"\b(team player|strong (?:communication|interpersonal)|excellent (?:communication|interpersonal)|hard-?working|detail-oriented|self-motivated|results-driven|go-getter|fast learner|passionate about)\b", re.I)
# Category words instead of names (rule 14): an exact-phrase screen matches the tool, standard or language, not "scripting ability".
VAGUE = re.compile(r"\b(familiar(?:ity)? with|knowledge of|exposure to|(?:scripting|networking|coding|programming) (?:skills|ability)|(?:security|industry) certifications?|(?:various|multiple|several) (?:tools|frameworks|platforms|languages)|experience (?:with|in) (?:various|multiple|several))\b", re.I)
STOP = set("a an the of and or to in on for with by as at from that which this it its their our my into over across is are was were be been being have has had".split())


def _content_words(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z][a-z0-9+/'-]{3,}", text.lower()) if w not in STOP}


def line_issues(sid: str, text: str) -> tuple[list[str], list[str]]:
    """(errors, warnings) for one CV/letter line."""
    errs, warns = [], []
    for rx, msg in BANNED:
        if re.search(rx, text, re.I):
            errs.append(f"[{sid}] {msg}")
    if sid[0] in "PBCS" and RAG_PROSE.search(text) and sid[0] != "S":
        errs.append(f"[{sid}] \"RAG\" belongs in Skills only, not in a sentence")
    if re.search(r"\b(my|our) own\b", text, re.I):
        warns.append(f"[{sid}] \"my own ...\": cut it if the ownership is implied; keep it only as a contrast")
    if sid[0] in "PB" and re.search(r"\b(I|me|my|we|our)\b", text):
        warns.append(f"[{sid}] first person in a CV line (I/me/my/we/our): the fact belongs in the letter or the stories")
    if sid[0] in "PBK" and FILLER.search(text):
        warns.append(f"[{sid}] soft-skill filler (team player, strong communication ...): say what the person did, or cut it")
    if sid[0] in "PBK" and (m := VAGUE.search(text)):
        warns.append(f"[{sid}] vague category (\"{m.group(0)}\"): name the tool, standard, language or certificate, if the stories back it")
    if len(STACKED_HEDGE.findall(text)) >= 2:
        warns.append(f"[{sid}] two hedges (about/around) in one line: state the figure once")
    if sid[0] in "PB" and LABEL_ONLY.match(re.sub(r"^\w+:\s*", "", text)):
        warns.append(f"[{sid}] \"Briefed ...\" shows attendance, not impact: add what the audience did or decided")
    words = re.findall(r"[a-z']+", re.sub(r"https?://\S+", " ", text.lower()))
    seen: dict[tuple, int] = {}
    for i in range(len(words) - 2):
        tri = tuple(words[i:i + 3])
        if not set(tri) <= STOP:
            seen[tri] = seen.get(tri, 0) + 1
    if rep := [" ".join(t) for t, n in seen.items() if n > 1 and not set(t) & {"and"}][:2]:
        warns.append(f"[{sid}] repeats a phrase inside the line: {rep}")
    return errs, warns


def skill_items(text: str) -> list[str]:
    body = text.split(":", 1)[1] if ":" in text else text
    # split on commas outside parentheses
    out, depth, cur = [], 0, ""
    for ch in body:
        depth += ch == "("
        depth -= ch == ")"
        if ch == "," and depth == 0:
            out.append(cur.strip())
            cur = ""
        else:
            cur += ch
    return [x for x in out + [cur.strip()] if x]


def skill_issues(sid: str, text: str, label: str) -> list[str]:
    bad = []
    for item in skill_items(text):
        # every item starts with a capital letter (the user's rule, 2026-10-01, replacing the lowercase rule): "Secure code review", "AWS"
        if item[:1].islower():
            bad.append(f"[{sid}] skill \"{item}\" starts with a lowercase letter: capitalise it (every item, including the first)")
        if "/" in item and re.search(r"JavaScript/TypeScript", item):
            bad.append(f"[{sid}] list languages separately (\"JavaScript, TypeScript (Node.js)\"), not \"{item}\"")
    return bad


def is_company_level(ctx: str, contexts: list[str]) -> bool:
    name = re.sub(r"\s*\(.*?\)", "", ctx.split(" — ")[0]).strip()
    return any(c != ctx and len(c.split(" — ")) >= 3 and name and name in c.split(" — ")[1] for c in contexts)


def master_issues(career: Career) -> tuple[list[str], list[str]]:
    errs, warns = [], []
    for sid, it in career.items.items():
        if sid[0] in "PBC":   # stories are raw logs: not linted
            e, w = line_issues(sid, it.text)
            errs += e
            warns += w
        if sid[0] == "K":
            label = it.text.split(":", 1)[0]
            errs += skill_issues(sid, it.text, label)
    loc = career.contact.get("location", "")
    if re.search(r"relocation to\b", loc, re.I):
        errs.append(f"header location \"{loc}\": write \"Open to relocation\" with no destination")
    if MEDIUM.search(career.contact.get("links", "")):
        errs.append("header links carry a Medium link: blog links live in the Projects entry only")
    for sid, it in career.items.items():
        if sid[0] == "B" and re.search(r"\bWebRTC\b", it.text) and not re.search(r"\[[^\]]*WebRTC[^\]]*\]\(https?://", it.text):
            warns.append(f"[{sid}] the WebRTC article needs its own clickable link")
    return errs, warns


def taper_warnings(roles: list[tuple[str, int, int]]) -> list[str]:
    """roles: (name, bullets kept, bullets the master has), most recent first. A more recent role should not
    carry fewer bullets than an older one when it has more to give (the user, 2026-10-02: recency tapers)."""
    out = []
    for (new, kept_new, avail_new), (old, kept_old, _) in zip(roles, roles[1:]):
        if kept_old > kept_new and avail_new > kept_new:
            out.append(f"role \"{new}\" has {kept_new} bullets but the older role \"{old}\" has {kept_old}: taper with recency (the most recent role gets the most, 4-5; the next 3-4; older roles 2-3)")
    return out


BANK_TERM = "a Fortune 100 global financial and banking institution"
DEFINED_BANK = r"fortune 100 global financial and banking institution"


def tailored_issues(data: dict, career: Career) -> tuple[list[str], list[str]]:
    errs, warns = [], []
    chosen: dict[str, str] = {}
    for sec in data.get("sections", []):
        for b in sec.get("bullets", []) if isinstance(sec, dict) else []:
            if isinstance(b, dict) and "source_id" in b:
                chosen[str(b["source_id"])] = str(b.get("text", ""))
    for sid, text in chosen.items():
        if sid not in career.items:
            continue
        if sid[0] in "PB":
            e, w = line_issues(sid, text)
            errs += e
            warns += w
        if sid[0] == "K":
            errs += skill_issues(sid, text, text.split(":", 1)[0])
    for c in data.get("cover_letter", []):
        if isinstance(c, dict) and "source_id" in c:
            e, w = line_issues(str(c["source_id"]), str(c.get("text", "")))
            errs += e
            warns += w
    # "the bank" must come after the defined term in the same document (the user, 2026-10-02: B05, B06 and B10 say "the bank")
    cv_lines = [str(b.get("text", "")) for sec in data.get("sections", []) if isinstance(sec, dict)
                for b in sec.get("bullets", []) if isinstance(b, dict)]
    letter_lines = [str(c.get("text", "")) for c in data.get("cover_letter", []) if isinstance(c, dict)]
    for doc, lines in (("CV", cv_lines), ("cover letter", letter_lines)):
        for t in lines:
            if re.search(DEFINED_BANK, t, re.I):
                break
            if re.search(r"\bthe bank\b", t, re.I):
                errs.append(f"{doc}: \"the bank\" appears before \"{BANK_TERM}\" introduces it: keep an earlier line with "
                            "the defined term (Key achievements P05, P10, P08 or P12), or spell the term out")
                break
    loc = data.get("location", "")
    if isinstance(loc, str) and re.search(r"relocation to\b", loc, re.I):
        errs.append("location: write \"Open to relocation\" with no destination")

    def norm(s: str) -> str:
        return " ".join(s.split()).lower()

    # static sections: present and verbatim
    for sid, it in career.items.items():
        static = (sid[0] == "E") or (sid[0] == "B" and it.context.startswith(("Projects", "Volunteering")))
        if static:
            if sid not in chosen:
                errs.append(f"[{sid}] is a static section line (projects, volunteering, education): it is never cut")
            elif norm(chosen[sid]) != norm(it.text):
                errs.append(f"[{sid}] is a static section line: copy it from the master unchanged")
    # skills: every row present
    rows = [sid for sid, it in career.items.items() if sid[0] == "K"]
    if missing := [r for r in rows if r not in chosen]:
        errs.append(f"skills rows missing {missing}: keep every row, reorder or trim the items inside instead")
    # depth floor per role
    contexts = [it.context for it in career.items.values() if sid_is_role(it)]
    by_ctx: dict[str, list[str]] = {}
    for sid, it in career.items.items():
        if sid_is_role(it):
            by_ctx.setdefault(it.context, []).append(sid)
    for ctx, ids in by_ctx.items():
        if is_company_level(ctx, contexts):
            continue
        floor = min(3, len(ids))
        kept = [i for i in ids if i in chosen]
        if len(kept) > 5:
            warns.append(f"role \"{ctx.split(' — ')[0]}\" has {len(kept)} bullets; 3-5 reads best")
        if len(kept) < floor:
            errs.append(f"role \"{ctx.split(' — ')[0]}\" has {len(kept)} bullets; keep at least {floor} (master has {len(ids)}); dropped: {[i for i in ids if i not in chosen]}")
    roles = [(ctx.split(' — ')[0], len([i for i in ids if i in chosen]), len(ids))
             for ctx, ids in by_ctx.items() if not is_company_level(ctx, contexts)]
    warns += taper_warnings(roles)
    # Key achievements are headlines: about 35 words at most; a second proof point, a recognition or a follow-on belongs elsewhere (the user, 2026-10-02)
    for a in (s for s in chosen if s[0] == "P" and career.items.get(s) and career.items[s].section == "Key achievements"):
        n = len(chosen[a].split())
        if n > 35:
            warns.append(f"Key achievement [{a}] is {n} words; keep to 35 or fewer (one or two lines): state the outcome only, drop the secondary clause (a second proof point, a recognition, a follow-on, or how it landed, which the matching experience bullet carries) in this copy")
    # key achievement restates an experience bullet
    ach = [s for s in chosen if s[0] == "P" and career.items.get(s) and career.items[s].section == "Key achievements"]
    for a in ach:
        wa = _content_words(re.sub(r"^\w[\w ]*:\s*", "", chosen[a]))
        for b in (s for s in chosen if s[0] == "B"):
            wb = _content_words(chosen[b])
            if wa and wb and len(wa & wb) / min(len(wa), len(wb)) >= 0.6:
                warns.append(f"Key achievement [{a}] restates experience bullet [{b}] ({len(wa & wb)} shared words): tell the event once, the bullet carries the method")
    # Profile is the main place to converge with the JD: a Summary that is mostly the master's text was not tailored
    summ = [s for s in chosen if s in career.items and career.items[s].section == "Summary" and s != "P00"]
    changed = [s for s in summ if norm(chosen[s]) != norm(career.items[s].text)]
    n_prof = sum(len(chosen[s].split()) for s in summ)
    if n_prof > 65:
        warns.append(f"Profile is {n_prof} words; keep it to about 40-60 (2-3 sentences, three lines): keep who the person is and the one or two strengths the JD asks for, and leave the proof to Key achievements")
    if len(summ) >= 3 and len(changed) < 3:
        warns.append(f"Profile: only {len(changed)} of {len(summ)} Summary lines differ from the master; rewrite it for this role in the JD's vocabulary (writing-rules.md section 2) and list the converged terms")
    return errs, warns


def sid_is_role(it) -> bool:
    return it.id[0] == "B" and not it.context.startswith(("Projects", "Volunteering")) and bool(it.context)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("target", help="'master' or an application folder")
    args = ap.parse_args(argv)
    career = load_career()
    if args.target == "master":
        errs, warns = master_issues(career)
    else:
        import json
        folder = Path(args.target)
        if not folder.is_absolute() and not folder.exists():
            folder = ROOT / "profile" / "applications" / args.target
        errs, warns = tailored_issues(json.loads((folder / "tailored.json").read_text(encoding="utf-8")), career)
    for e in errs:
        print(f"ERROR: {e}")
    for w in warns:
        print(f"WARNING: {w}")
    print(f"{len(errs)} errors, {len(warns)} warnings")
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(main())
