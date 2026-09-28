"""Record one live ATS board response as a test fixture (tests/fixtures/ats/<name>.json).

    python tools/record_fixture.py greenhouse <slug> <board_url> <name> [--max 60]

Only title/location/url/ids are kept (no descriptions), trimmed to --max jobs.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from jobradar.common import ROOT, fetch_many  # noqa: E402

KEEP = ["url", "title", "company", "ats_type", "ats_id", "location", "country_iso", "posted_at"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("ats"); ap.add_argument("slug"); ap.add_argument("url"); ap.add_argument("name")
    ap.add_argument("--max", type=int, default=60)
    a = ap.parse_args()
    res = asyncio.run(fetch_many([(a.ats, a.slug, a.url)], progress=False))[a.url]
    if not res.ok:
        raise SystemExit(f"fetch failed: {res.error}")
    jobs = [j.model_dump(mode="json", include=set(KEEP)) for j in res.jobs[: a.max]]
    out = ROOT / "tests" / "fixtures" / "ats" / f"{a.name}.json"
    out.write_text(json.dumps({"board": {"ats": a.ats, "slug": a.slug, "url": a.url}, "jobs": jobs},
                              indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"{len(jobs)} of {len(res.jobs)} jobs -> {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
