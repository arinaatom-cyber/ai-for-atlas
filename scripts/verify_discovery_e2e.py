#!/usr/bin/env python3
"""End-to-end проверка Discovery: каталог → scan → сайт → JSON."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

SITE = ROOT / "docs" / "site"
REQUIRED_PAGES = ("discovery.html", "qc.html", "atlas.html", "cohorts.html")
REQUIRED_ASSETS = ("assets/theme.css", "assets/i18n.js")
REQUIRED_JSON = ("latest.json", "meta.json", "atlas_profile.json")


def ok(msg: str) -> None:
    print(f"  OK  {msg}")


def fail(msg: str) -> None:
    print(f"  FAIL {msg}")
    raise SystemExit(1)


def warn(msg: str) -> None:
    print(f"  WARN {msg}")


def check_catalog() -> None:
    from atlas_agent.config import load_config
    from atlas_agent.discovery.agent import load_catalog_readonly

    cfg = load_config()
    df = load_catalog_readonly(cfg)
    if len(df) < 50:
        fail(f"catalog too small: {len(df)} rows")
    ok(f"catalog read-only: {len(df)} rows")


def check_latest_json() -> dict:
    p = ROOT / "data" / "discovery_history" / "latest.json"
    if not p.is_file():
        fail("missing data/discovery_history/latest.json — run scan")
    data = json.loads(p.read_text(encoding="utf-8"))
    s = data.get("summary") or {}
    for key in ("candidates", "catalog_unique_ids", "source_stats"):
        if key not in s:
            warn(f"summary missing {key}")
    cands = data.get("candidates") or data.get("new_projects") or []
    ok(f"latest.json: {len(cands)} candidates, generated {data.get('generated_at', '?')[:19]}")
    cohort = data.get("cohort_literature") or []
    ok(f"cohort_literature: {len(cohort)} papers")
    da = s.get("data_availability") or {}
    if da:
        ok(f"data_availability: {da}")
    else:
        warn("data_availability summary missing — run scripts/run_data_audit.py")
    return data


def check_site_files() -> None:
    if not SITE.is_dir():
        fail(f"missing {SITE}")
    for name in REQUIRED_PAGES:
        p = SITE / name
        if not p.is_file() or p.stat().st_size < 500:
            fail(f"missing or empty {name}")
        text = p.read_text(encoding="utf-8")
        for needle in ("site-header", "page-hero", "data-i18n", "theme.css"):
            if needle not in text:
                fail(f"{name} missing {needle}")
        ok(f"{name} ({p.stat().st_size // 1024} KB)")
    for rel in REQUIRED_ASSETS:
        p = SITE / rel
        if not p.is_file():
            fail(f"missing {rel}")
        ok(rel)
    for name in REQUIRED_JSON:
        p = SITE / name
        if not p.is_file():
            fail(f"missing {name}")
        json.loads(p.read_text(encoding="utf-8"))
        ok(name)


def check_portal() -> None:
    p = ROOT / "docs" / "index.html"
    if not p.is_file():
        fail("missing docs/index.html")
    t = p.read_text(encoding="utf-8")
    for href in ("site/discovery.html", "site/cohorts.html", "site/qc.html"):
        if href not in t:
            fail(f"portal missing link {href}")
    ok("docs/index.html portal links")


def check_candidates_have_fields(data: dict) -> None:
    cands = data.get("candidates") or []
    if not cands:
        warn("no candidates in latest scan")
        return
    sample = cands[0]
    for field in ("accession", "title", "data_availability"):
        if field not in sample:
            warn(f"candidate missing field {field}")
    with_da = sum(1 for c in cands if (c.get("data_availability") or {}).get("status"))
    ok(f"candidates with data_availability: {with_da}/{len(cands)}")


def main() -> int:
    print("=== E2E Discovery verification ===\n")
    print("1. Catalog")
    check_catalog()
    print("\n2. Latest scan JSON")
    data = check_latest_json()
    print("\n3. Candidate fields")
    check_candidates_have_fields(data)
    print("\n4. Published site")
    check_site_files()
    print("\n5. Portal")
    check_portal()
    print("\n=== All checks passed ===")
    print(f"Open: file://{SITE / 'discovery.html'}")
    print("Live: https://arinaatom-cyber.github.io/TMT/discovery/discovery.html")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
