"""Escaping for third-party text that goes into GitHub markdown (digests, issues)."""
from __future__ import annotations

import re

_MD_SPECIAL = re.compile(r"([\\`*_\[\]<>|#!~])")


def md(text: str) -> str:
    """Escape third-party text for the digest, so a job title can't inject links,
    images or formatting into the GitHub issue."""
    return _MD_SPECIAL.sub(r"\\\1", " ".join((text or "").split()))


def md_url(url: str) -> str:
    """Only http(s) links, with characters that could end the markdown link encoded."""
    if not re.match(r"^https?://", url or "", re.I):
        return "#"
    return url.replace(" ", "%20").replace("(", "%28").replace(")", "%29").replace("<", "%3C").replace(">", "%3E")
