"""Post-scan enrichment: file audit + AI evaluation before site publish."""
from __future__ import annotations

from typing import Any

from atlas_agent.discovery.evaluation.report import evaluate_discovery_report_from_config
from atlas_agent.viz.portal_index import format_finding_note, resolve_publication_links


def finalize_discovery_report(report: dict[str, Any], cfg: dict[str, Any]) -> dict[str, Any]:
    """Annotate data availability and attach typed evaluation to every bucket."""
    from atlas_agent.discovery.data_availability import annotate_data_availability

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
            item["finding_note"] = format_finding_note(item)

    evaluate_discovery_report_from_config(report, cfg)
    return report
