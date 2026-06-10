"""Публикация Discovery на GitHub Pages (docs/site/) — только новые проекты."""
from __future__ import annotations

import json
from pathlib import Path

from atlas_agent.viz.discovery_html import generate_discovery_html
from atlas_agent.viz.discovery_qc_html import generate_qc_html


def publish_discovery_site(report: dict, root: Path) -> Path:
    site = root / "docs" / "site"
    site.mkdir(parents=True, exist_ok=True)

    candidates = report.get("candidates") or report.get("new_projects") or []
    site_report = {
        "generated_at": report.get("generated_at"),
        "summary": report.get("summary") or {},
        "new_projects": candidates,
        "candidates": candidates,
        "manual_check": report.get("manual_check") or [],
        "rejected_material": report.get("rejected_material") or [],
    }

    generate_discovery_html(site_report, site / "discovery.html")
    generate_qc_html(site_report, site / "qc.html")

    meta = {
        "generated_at": report.get("generated_at"),
        "new_projects_count": len(candidates),
        "catalog_unique_ids": (report.get("summary") or {}).get("catalog_unique_ids"),
        "policy": "Only new PXD/PDC/MSV/IPX. Catalog projects.csv is never published.",
    }
    (site / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    slim = {
        "generated_at": report.get("generated_at"),
        "summary": report.get("summary"),
        "new_projects": candidates,
        "candidates": candidates,
        "manual_check": report.get("manual_check") or [],
        "rejected_material": report.get("rejected_material") or [],
    }
    (site / "latest.json").write_text(json.dumps(slim, ensure_ascii=False, indent=2), encoding="utf-8")
    return site
