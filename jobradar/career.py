"""Read the user's career documents (profile/career/, else examples/career/).

  master_resume.md   front matter (name, email, phone, location, links) + ID'd lines:
                     [P..] summary, [B..] experience bullets, [K..] skills, [E..] education
  stories.md         "## [S01] title" + STAR text
  cover_blocks.md    "## [C01] title" + paragraph

These are the user's own words and the only material a tailored résumé or cover
letter may draw from; tools/jd_check.py enforces that by ID.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from jobradar.paths import profile_path

ID_RE = re.compile(r"\[([A-Z]\d{2,3})\]")
_LINE_ID = re.compile(r"^\s*-\s*\[([A-Z]\d{2,3})\]\s*(.+?)\s*$")
_HEADING_ID = re.compile(r"^##\s*\[([A-Z]\d{2,3})\]\s*(.+?)\s*$")
_COMMENT = re.compile(r"<!--.*?-->", re.S)
EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
URL_RE = re.compile(r"https?://[^\s)>\]]+", re.I)
PHONE_RE = re.compile(r"\+?\d[\d ()-]{7,}\d")


@dataclass
class Item:
    id: str
    text: str
    section: str        # "# Experience", "## [S01] …" title for stories/blocks
    context: str = ""   # role line for experience bullets ("Senior Security Consultant — ExampleSec …")


@dataclass
class Career:
    contact: dict[str, str] = field(default_factory=dict)
    items: dict[str, Item] = field(default_factory=dict)
    raw_text: str = ""  # all documents, comments removed; used for "is this skill mine?" checks

    def has(self, item_id: str) -> bool:
        return item_id in self.items

    def contact_tokens(self) -> set[str]:
        """Emails, URLs and phone numbers the user wrote themselves (anything else in output is planted)."""
        text = self.raw_text + "\n" + "\n".join(self.contact.values())
        return {m.lower().rstrip(".,") for rx in (EMAIL_RE, URL_RE) for m in rx.findall(text)} | \
               {re.sub(r"\D", "", m) for m in PHONE_RE.findall(text)}


def career_dir() -> Path:
    return profile_path("career")


# The masters are the source every application is built from. The master-update check (deterministic pass plus
# two fresh reviewers) must come first, and only clean masters may be used for drafts, so a clean check is
# recorded as a stamp (the SHA-256 of the three masters) that tools/jd_check.py tailor requires.
MASTER_FILES = ("master_resume.md", "cover_blocks.md", "stories.md")
CLEARED_FILE = ".master_cleared"


def masters_digest(directory: Path | None = None) -> str:
    d = directory or career_dir()
    h = hashlib.sha256()
    for name in MASTER_FILES:
        h.update(name.encode() + b"\x00")
        f = d / name
        if f.exists():
            h.update(f.read_bytes().replace(b"\r\n", b"\n"))
    return h.hexdigest()


def masters_cleared(directory: Path | None = None) -> tuple[bool, str]:
    """(True, "") when the masters are exactly as they were at the last clean master-update check."""
    d = directory or career_dir()
    stamp = d / CLEARED_FILE
    if not stamp.exists():
        return False, "the master documents have not been cleared by the master-update check"
    if stamp.read_text(encoding="utf-8").strip() != masters_digest(d):
        return False, "the master documents changed after the last clean master-update check"
    return True, ""


def clear_masters(directory: Path | None = None) -> str:
    """Record that the masters passed the master-update check as they are now; returns the digest."""
    d = directory or career_dir()
    digest = masters_digest(d)
    (d / CLEARED_FILE).write_text(digest + "\n", encoding="utf-8")
    return digest


def _front_matter(text: str) -> tuple[dict[str, str], str]:
    if not text.startswith("---"):
        return {}, text
    end = text.find("\n---", 3)
    if end < 0:
        return {}, text
    meta = {}
    for line in text[3:end].splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            meta[k.strip().lower()] = v.strip()
    return meta, text[end + 4:]


def _add(career: Career, item: Item, where: str) -> None:
    if item.id in career.items:
        raise ValueError(f"duplicate ID [{item.id}] in {where}")
    career.items[item.id] = item


def load_career(folder: Path | None = None) -> Career:
    folder = folder or career_dir()
    career = Career()
    resume = folder / "master_resume.md"
    if not resume.exists():
        raise FileNotFoundError(f"{resume} missing — copy examples/career/ to profile/career/ and fill it in")
    meta, body = _front_matter(resume.read_text(encoding="utf-8"))
    career.contact = meta
    body = _COMMENT.sub("", body)
    texts = [body]
    section = context = ""
    for line in body.splitlines():
        if line.startswith("# "):
            section, context = line[2:].strip(), ""
        elif line.startswith("## "):
            context = line[3:].strip()
        elif m := _LINE_ID.match(line):
            _add(career, Item(m.group(1), m.group(2), section, context), resume.name)
    for name in ("stories.md", "cover_blocks.md"):
        path = folder / name
        if not path.exists():
            continue
        text = _COMMENT.sub("", path.read_text(encoding="utf-8"))
        texts.append(text)
        current, buf = None, []
        for line in text.splitlines() + ["## [Z999] end"]:
            if m := _HEADING_ID.match(line):
                if current:
                    _add(career, Item(current[0], " ".join(" ".join(buf).split()), current[1]), name)
                current, buf = (m.group(1), m.group(2)), []
            elif current:
                buf.append(line)
    career.items.pop("Z999", None)
    career.raw_text = "\n".join(texts)
    return career


# --- cover blocks follow the stories and the CV (the user, 2026-10-05) -----------------------------------------------------
# Every cover block that carries a metadata comment (rank | anchor B06 | ... | sources S01) is tied to the CV lines and stories it
# expands. When one of those changes, the block is out of date until someone reviews it and records the sync.
COVER_SYNC_FILE = ".cover_sync.json"
_SOURCE_ID = re.compile(r"\b([SBPKE]\d{2})\b")


def _cover_block_sources(directory: Path) -> dict[str, list[str]]:
    path = directory / "cover_blocks.md"
    if not path.exists():
        return {}
    out: dict[str, list[str]] = {}
    lines = path.read_text(encoding="utf-8").splitlines()
    for n, line in enumerate(lines):
        m = _HEADING_ID.match(line)
        if not m or n + 1 >= len(lines):
            continue
        meta = lines[n + 1].strip()
        if meta.startswith("<!--") and meta.endswith("-->"):
            ids = sorted(set(_SOURCE_ID.findall(meta)))
            if ids:
                out[m.group(1)] = ids
    return out


def _source_hashes(career: "Career", ids: list[str]) -> dict[str, str]:
    return {i: (hashlib.sha256(" ".join(career.items[i].text.split()).encode()).hexdigest()[:16] if i in career.items else "missing")
            for i in ids}


def cover_blocks_stale(directory: Path | None = None) -> list[tuple[str, list[str]]]:
    """[(block id, changed source ids)] for cover blocks whose CV lines or stories changed since the last recorded sync."""
    d = directory or career_dir()
    blocks = _cover_block_sources(d)
    if not blocks:
        return []
    career = load_career(d)
    snap_path = d / COVER_SYNC_FILE
    snap = json.loads(snap_path.read_text(encoding="utf-8")) if snap_path.exists() else {}
    stale = []
    for bid, ids in sorted(blocks.items()):
        cur, old = _source_hashes(career, ids), snap.get(bid)
        if old is None:
            stale.append((bid, ["not recorded yet"]))
        elif changed := sorted(i for i in set(cur) | set(old) if cur.get(i) != old.get(i)):
            stale.append((bid, changed))
    return stale


def record_cover_sync(directory: Path | None = None) -> int:
    """Record that every cover block matches the CV lines and stories it expands as they are now; returns the block count."""
    d = directory or career_dir()
    blocks = _cover_block_sources(d)
    career = load_career(d)
    snap = {bid: _source_hashes(career, ids) for bid, ids in blocks.items()}
    (d / COVER_SYNC_FILE).write_text(json.dumps(snap, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    return len(snap)


def cover_sync_message(stale: list[tuple[str, list[str]]]) -> str:
    rows = "; ".join(f"[{b}] <- {', '.join(ids)}" for b, ids in stale)
    return (f"COVER BLOCKS OUT OF SYNC: {rows}. The CV lines or stories these cover blocks expand changed. Review each block against them "
            "(challenge, what you did, impact, and its rank and 'CV leaves out' note), update it, then  python tools/cover_sync.py done")

