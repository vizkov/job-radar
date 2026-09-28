"""Source registry: build enabled adapters from sources.yaml and run them in isolation.

Each adapter module registers a factory with @register("name"). run_sources() runs
every source concurrently under its own timeout; an exception or timeout in one
source becomes a failed SourceResult and never stops the others.
"""
from __future__ import annotations

import asyncio
import importlib
import time
from typing import Callable

import yaml

from jobradar.paths import profile_path
from jobradar.model import Source, SourceResult

_FACTORIES: dict[str, Callable[[dict], Source]] = {}
_MODULES = ["ats", "bundesagentur", "jobtech", "eures", "careers_page", "alert_email"]  # adapter modules under jobradar.sources, imported lazily


def register(name: str):
    def deco(factory):
        _FACTORIES[name] = factory
        return factory
    return deco


def load_sources_config(path=None) -> dict:
    path = path or profile_path("sources.yaml")
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def build_sources(cfg: dict, only: str | None = None) -> list[Source]:
    """Enabled sources, or just `only` (enabled or not — for --source testing)."""
    for m in _MODULES:
        importlib.import_module(f"jobradar.sources.{m}")
    out = []
    for name, scfg in (cfg.get("sources") or {}).items():
        scfg = scfg or {}
        if only and name != only:
            continue
        if not only and not scfg.get("enabled", False):
            continue
        if name not in _FACTORIES:
            raise SystemExit(f"sources.yaml: unknown source {name!r} (known: {', '.join(sorted(_FACTORIES))})")
        out.append(_FACTORIES[name](scfg))
    if only and not out:
        raise SystemExit(f"--source {only}: not configured in sources.yaml")
    return out


async def _run_one(src: Source) -> SourceResult:
    t0 = time.monotonic()
    try:
        res = await asyncio.wait_for(src.fetch(), timeout=src.timeout)
    except asyncio.TimeoutError:
        res = SourceResult(src.name, ok=False, error=f"timeout after {src.timeout:.0f}s")
    except Exception as e:  # isolation: one adapter's bug must not end the run
        res = SourceResult(src.name, ok=False, error=f"{type(e).__name__}: {str(e)[:200]}")
    res.seconds = time.monotonic() - t0
    return res


async def run_sources(sources: list[Source]) -> list[SourceResult]:
    return list(await asyncio.gather(*(_run_one(s) for s in sources)))
