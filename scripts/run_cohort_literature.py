#!/usr/bin/env python3
"""Обновить cohort_literature в latest.json и пересобрать сайт (без полного scan)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from atlas_agent.config import load_config
from atlas_agent.discovery.cohort_literature import search_cohort_literature
from atlas_agent.discovery.history import save_scan
from atlas_agent.discovery.agent import load_catalog_readonly
from atlas_agent.revisor.literature_watch import build_known_sets
from atlas_agent.viz.publish_site import publish_discovery_site


def main() -> int:
    cfg = load_config()
    latest = ROOT / "data" / "discovery_history" / "latest.json"
    if latest.is_file():
        report = json.loads(latest.read_text(encoding="utf-8"))
    else:
        report = {"generated_at": "", "summary": {}}

    scan_cfg = (cfg.get("discovery") or {}).get("cohort_literature") or {}
    df = load_catalog_readonly(cfg)
    known_pmids, _ = build_known_sets(df)

    items, stats = search_cohort_literature(
        year_from=int(scan_cfg.get("year_from") or 2023),
        year_to=int((cfg.get("discovery") or {}).get("year_to") or 2026),
        page_size=int(scan_cfg.get("max_results") or 30),
        min_patients=int(scan_cfg.get("min_patients") or 50),
        min_score=int(scan_cfg.get("min_score") or 25),
        known_pmids=known_pmids,
    )
    report["cohort_literature"] = items
    report.setdefault("summary", {})["cohort_literature"] = stats

    save_scan(report, ROOT)
    publish_discovery_site(report, ROOT)
    print(f"Cohort papers: {len(items)} (scanned {stats.get('scanned')})")
    print(f"Site: {ROOT / 'docs' / 'site' / 'cohorts.html'}")
    for it in items[:5]:
        print(f"  PMID {it.get('pmid')} N={it.get('patient_n')} — {(it.get('title') or '')[:60]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
