"""Where personal settings live.

The public template ships generic samples in examples/. Your private copy adds
profile/ with your real settings (targets, filters, careers pages, …). Each file
is read from profile/ when it exists there, otherwise from examples/, so pulling
template updates into your private repo never conflicts with your settings.

JOBRADAR_PROFILE=<dir> points at another settings folder (the tests use this to
always run against examples/).
"""
from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EXAMPLES = ROOT / "examples"
PROFILE = ROOT / "profile"

PROFILE_FILES = ("config.json", "sources.yaml", "targets.tsv", "aliases.csv", "overrides.csv",
                 "careers_pages.yaml", "sponsor_overrides.csv")


def profile_dir() -> Path:
    override = os.environ.get("JOBRADAR_PROFILE")
    if override:
        p = Path(override)
        return p if p.is_absolute() else ROOT / p
    return PROFILE


def profile_path(name: str) -> Path:
    """profile/<name> if present, else examples/<name>."""
    p = profile_dir() / name
    return p if p.exists() else EXAMPLES / name
