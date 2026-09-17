from __future__ import annotations

import json
import shutil
from pathlib import Path

from atlas_agent.viz.site_sanitize import sanitize_report_for_site
from atlas_agent.viz.discovery_html import generate_discovery_html, generate_guide_html, generate_methods_html
from atlas_agent.viz.discovery_qc_html import generate_qc_html
from atlas_agent.viz.portal_html import generate_portal_html
from atlas_agent.viz.i18n_loader import hydrate_site_html
from atlas_agent.viz.site_theme import (
    DEPLOY_DOCS_PORTAL,
    DEPLOY_DOCS_SITE,
    DEPLOY_TMT,
    write_site_assets,
)


def _site_report(report: dict) -> tuple[dict, list]:
    candidates = report.get("candidates") or report.get("new_projects") or []
    site_report = {
        "generated_at": report.get("generated_at"),
        "summary": report.get("summary") or {},
        "catalog_profile": report.get("catalog_profile") or {},
        "new_projects": candidates,
        "candidates": candidates,
        "manual_check": report.get("manual_check") or [],
        "repository_manual": report.get("repository_manual") or [],
        "rejected_material": report.get("rejected_material") or [],
        "filtered_out": report.get("filtered_out") or [],
        "publications_analyzed": report.get("publications_analyzed") or [],
        "literature_semantic": report.get("literature_semantic") or [],
        "cohort_literature": report.get("cohort_literature") or [],
        "methods_manifest": report.get("methods_manifest") or {},
        "quality_metrics": report.get("quality_metrics") or (report.get("summary") or {}).get("quality_metrics") or {},
        "filters_applied": report.get("filters_applied") or {},
    }
    return site_report, candidates


def _build_meta(report: dict, candidates: list, profile: dict) -> dict:
    stats = (report.get("summary") or {}).get("source_stats") or {}
    return {
        "generated_at": report.get("generated_at"),
        "new_projects_count": len(candidates),
        "publications_analyzed": len(report.get("publications_analyzed") or []),
        "literature_semantic": len(report.get("literature_semantic") or []),
        "cohort_literature_count": len(report.get("cohort_literature") or []),
        "abstract_llm_read": stats.get("abstract_llm_read", 0),
        "abstract_atlas_fit_yes": stats.get("abstract_atlas_fit_yes", 0),
        "semantic_from_abstract": stats.get("semantic_from_abstract", 0),
        "catalog_unique_ids": (report.get("summary") or {}).get("catalog_unique_ids"),
        "catalog_rows": profile.get("n_rows"),
        "policy": "New projects + abstract AI analysis. Catalog rows are never published.",
        "languages": ["en"],
    }


def _write_json_bundle(site: Path, report: dict, site_report: dict, meta: dict, profile: dict, candidates: list) -> None:
    (site / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    atlas_public = {
        "n_rows": profile.get("n_rows"),
        "n_unique_ids": profile.get("n_unique_ids"),
        "databases": profile.get("databases"),
        "top_organs": profile.get("top_organs"),
        "top_diseases": profile.get("top_diseases"),
        "tmt_plexes": profile.get("tmt_plexes"),
        "search_keywords": profile.get("search_keywords"),
    }
    (site / "atlas_profile.json").write_text(
        json.dumps(atlas_public, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    slim = {
        "generated_at": report.get("generated_at"),
        "summary": report.get("summary"),
        "catalog_profile": atlas_public,
        "new_projects": candidates,
        "candidates": candidates,
        "manual_check": site_report["manual_check"],
        "rejected_material": site_report["rejected_material"],
        "publications_analyzed": site_report["publications_analyzed"],
        "literature_semantic": site_report["literature_semantic"],
        "cohort_literature": site_report["cohort_literature"],
    }
    (site / "latest.json").write_text(json.dumps(slim, ensure_ascii=False, indent=2), encoding="utf-8")
    manifest = report.get("methods_manifest")
    if manifest:
        (site / "methods_manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
        )


def _write_html_redirect(path: Path, target: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <meta http-equiv="refresh" content="0;url={target}"/>
  <title>Redirect</title>
  <script>location.replace("{target}");</script>
</head>
<body><p><a href="{target}">Open projects table</a></p></body>
</html>""",
        encoding="utf-8",
    )


def _render_site_pages(site: Path, site_report: dict, *, deploy: str) -> None:
    generate_discovery_html(site_report, site / "discovery.html", deploy=deploy)
    generate_guide_html(site / "guide.html", deploy=deploy)
    generate_methods_html(site_report, site / "methods.html", deploy=deploy)
    generate_qc_html(site_report, site / "qc.html", deploy=deploy)
    _write_html_redirect(site / "cohorts.html", "discovery.html#cohorts")
    for legacy in ("atlas.html", "ai_search.html", "map.html"):
        _write_html_redirect(site / legacy, "discovery.html")


def publish_discovery_site(report: dict, root: Path, *, tmt_discovery_dir: Path | None = None) -> Path:
    report = sanitize_report_for_site(dict(report))
    site = root / "docs" / "site"
    site.mkdir(parents=True, exist_ok=True)
    write_site_assets(site)

    site_report, candidates = _site_report(report)
    profile = report.get("catalog_profile") or {}
    meta = _build_meta(report, candidates, profile)

    _render_site_pages(site, site_report, deploy=DEPLOY_DOCS_SITE)
    _write_json_bundle(site, report, site_report, meta, profile, candidates)
    generate_portal_html(root / "docs" / "index.html", meta=meta, deploy=DEPLOY_DOCS_PORTAL)
    hydrate_site_html(root / "docs")

    if tmt_discovery_dir is not None:
        publish_tmt_discovery_site(report, tmt_discovery_dir)

    return site


def publish_tmt_discovery_site(report: dict, discovery_dir: Path) -> Path:
    discovery_dir = Path(discovery_dir)
    if discovery_dir.exists():
        shutil.rmtree(discovery_dir)
    discovery_dir.mkdir(parents=True, exist_ok=True)
    write_site_assets(discovery_dir)

    site_report, candidates = _site_report(report)
    profile = report.get("catalog_profile") or {}
    meta = _build_meta(report, candidates, profile)

    _render_site_pages(discovery_dir, site_report, deploy=DEPLOY_TMT)
    _write_json_bundle(discovery_dir, report, site_report, meta, profile, candidates)
    generate_discovery_html(site_report, discovery_dir / "index.html", deploy=DEPLOY_TMT)
    hydrate_site_html(discovery_dir)
    return discovery_dir
