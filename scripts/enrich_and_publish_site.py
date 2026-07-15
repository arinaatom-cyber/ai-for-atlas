#!/usr/bin/env python3
"""Обогатить latest.json (finding_note, data guidance) и опубликовать на docs/site/."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from atlas_agent.config import load_config
from atlas_agent.discovery.data_availability import (
    annotate_data_availability,
    data_guidance,
    literature_data_hint,
    partition_phospho_only_candidates,
    partition_table_only_candidates,
)
from atlas_agent.viz.portal_index import format_finding_note, pubmed_url, repository_url, resolve_publication_links
from atlas_agent.viz.publish_site import publish_discovery_site
from atlas_agent.viz.site_sanitize import sanitize_report_for_site


def enrich_report(report: dict, cfg: dict) -> dict:
    tmt_root = (cfg.get("paths") or {}).get("tmt_projects_dir") or ""
    disc = cfg.get("discovery") or {}
    da_cfg = disc.get("data_availability") or {}

    for key in ("candidates", "new_projects", "manual_check", "rejected_material"):
        items = report.get(key) or []
        if not items:
            continue
        if da_cfg.get("enabled", True):
            annotate_data_availability(
                items,
                tmt_root=tmt_root,
                fetch_remote=da_cfg.get("fetch_remote", True),
                delay_s=float(da_cfg.get("delay_s", 0.12)),
            )
        for item in items:
            resolve_publication_links(item, fetch_pride_pmid=da_cfg.get("fetch_pride_pmid", True))
            if not str(item.get("year") or "").strip():
                for key in ("publication_date", "submission_date"):
                    m = re.search(r"(19|20)\d{2}", str(item.get(key) or ""))
                    if m:
                        item["year"] = m.group(0)
                        break
            if not str(item.get("year") or "").strip() and item.get("pmid"):
                try:
                    from atlas_agent.sources.literature import fetch_abstract

                    meta = fetch_abstract(str(item["pmid"]))
                    if meta.get("year"):
                        item["year"] = meta["year"]
                except Exception:
                    pass
            item["finding_note"] = format_finding_note(item)
            da = item.get("data_availability") or {}
            if da:
                da["guidance"] = data_guidance(da)

    if da_cfg.get("reject_phospho_only_files", True):
        for key in ("candidates", "new_projects"):
            items = report.get(key) or []
            if not items:
                continue
            kept, moved = partition_phospho_only_candidates(items)
            if moved:
                report[key] = kept
                fo = list(report.get("filtered_out") or [])
                fo.extend(moved)
                report["filtered_out"] = fo

    if da_cfg.get("require_protein_table", True):
        for key in ("candidates", "new_projects"):
            items = report.get(key) or []
            if not items:
                continue
            kept, moved = partition_table_only_candidates(
                items,
                pdc_requires_table=da_cfg.get("pdc_requires_table", True),
                reject_raw_no_files=da_cfg.get("reject_raw_no_files", True),
            )
            if moved:
                report[key] = kept
                fo = list(report.get("filtered_out") or [])
                fo.extend(moved)
                report["filtered_out"] = fo
                s = report.setdefault("summary", {})
                s["candidates"] = len(kept)
                s["new_projects"] = len(kept)
                s["filtered_out"] = len(fo)

    pubs = report.get("publications_analyzed") or []
    for p in pubs:
        p["data_hint"] = literature_data_hint(p)

    return report


def main() -> int:
    latest = ROOT / "data" / "discovery_history" / "latest.json"
    if not latest.is_file():
        print("Нет latest.json — сначала: python run_discovery.py scan")
        return 1

    cfg = load_config()
    report = json.loads(latest.read_text(encoding="utf-8"))
    print("Обогащение finding_note + data availability…")
    report = enrich_report(report, cfg)
    report = sanitize_report_for_site(report)
    latest.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    site = publish_discovery_site(report, ROOT)
    print(f"Сайт: {site}/discovery.html")
    print("Далее: powershell -File scripts\\push_site_github.ps1")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
