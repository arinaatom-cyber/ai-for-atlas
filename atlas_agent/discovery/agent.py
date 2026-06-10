"""
Discovery Agent — ищет похожие проекты и статьи в интернете.
Никогда не удаляет и не перезаписывает data/projects.csv.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from atlas_agent.discovery.catalog_profile import build_catalog_profile
from atlas_agent.discovery.history import save_scan
from atlas_agent.discovery.policy import assert_catalog_read_only, policy_summary
from atlas_agent.discovery.sources.consortia import scan_all_consortia
from atlas_agent.discovery.sources.pro_search import discover_projects_professional
from atlas_agent.revisor.literature_watch import build_known_sets, filter_novel_items
from atlas_agent.discovery.filters import apply_filters, default_filter_config
from atlas_agent.discovery.qc_outputs import build_qc_outputs
from atlas_agent.viz.discovery_qc_html import generate_qc_html, qc_markdown_summary
from atlas_agent.revisor.similarity import annotate_candidates
from atlas_agent.sources.projects_table import load_projects_table, primary_project_id


def _known_accessions(df: pd.DataFrame) -> set[str]:
    known_pmids, known_pxds = build_known_sets(df)
    return known_pmids | known_pxds | {
        primary_project_id(str(x)).upper()
        for x in df["Project ID"].dropna()
        if str(x).strip()
    }


def _flatten_consortia(consortia: dict) -> list[dict]:
    items = []
    for group, rows in consortia.items():
        for r in rows:
            if r.get("error"):
                continue
            acc = r.get("accession") or ""
            if not acc and r.get("accessions_mentioned"):
                for a in r["accessions_mentioned"]:
                    items.append({**r, "accession": a, "consortium_group": group})
                continue
            r = dict(r)
            r["consortium_group"] = group
            if acc:
                r["accession"] = acc.upper()
            items.append(r)
    return items


def _is_novel(item: dict, known: set[str]) -> bool:
    acc = (item.get("accession") or "").upper()
    if acc and acc in known:
        return False
    pmid = str(item.get("pmid") or "").strip()
    if pmid and pmid in known:
        return False
    for a in item.get("accessions_mentioned") or []:
        if a.upper() in known:
            return False
    return True


def _suggest_processing(item: dict, profile: dict) -> list[str]:
    """Подсказки по обработке для новых находок."""
    tips = []
    src = item.get("source", "")
    if "pdc" in src.lower() or item.get("consortium") == "PDC":
        tips.append("PDC: сверить с CPTAC pipeline; проверить PSM vs protein matrix")
    if item.get("consortium") == "CCLE":
        tips.append("CCLE: часто cell-line TMT — учесть batch по плексам")
    if item.get("consortium") == "GTEx":
        tips.append("GTEx: tissue reference — сопоставить с organ-level atlas")
    sim = item.get("similar_in_catalog") or []
    if sim:
        tips.append(f"Похож на ваш {sim[0]['project_id']} (score {sim[0]['score']})")
    if profile.get("tmt_plexes"):
        tips.append(f"Ваши plex: {', '.join(profile['tmt_plexes'][:3])}")
    tips.append("Добавить в CSV только после ручной проверки (projects.csv не меняется автоматически)")
    return tips


def run_discovery_scan(
    df: pd.DataFrame,
    cfg: dict,
    *,
    root: Path,
) -> dict[str, Any]:
    assert_catalog_read_only("read")  # явно: только чтение каталога

    scan_cfg = cfg.get("discovery") or cfg.get("scan") or {}
    year = int(scan_cfg.get("year_from") or 2024)
    profile = build_catalog_profile(df)
    known = _known_accessions(df)

    filter_cfg = {**default_filter_config(), **(scan_cfg.get("filters") or {})}

    pro = discover_projects_professional(
        year_from=year,
        year_to=int(scan_cfg.get("year_to") or 2026),
        pride_max=int(scan_cfg.get("pride_max") or 50),
        pub_max=int(scan_cfg.get("publications_max") or 30),
        pride_keywords=scan_cfg.get("pride_keywords") or ["TMT", "tandem mass tag", "isobaric"],
        profile_keywords=profile.get("search_keywords"),
        known_accessions=known,
        min_tmt_channels=int(filter_cfg.get("min_tmt_channels") or 7),
        max_tmt_channels=int(filter_cfg.get("max_tmt_channels") or 16),
    )
    pride_raw = [p for p in pro["repository_projects"] if p.get("source", "").startswith("pride")]
    pdc_raw = [p for p in pro["repository_projects"] if p.get("source") == "pdc_api" or p.get("consortium") == "PDC"]
    pubs_raw = pro["publications"]
    source_stats = pro.get("sources") or {}

    # Консорциумы (литература CPTAC/CCLE/GTEx — дополнительно)
    consortia = scan_all_consortia(profile.get("search_keywords"), year_from=year)
    cons_flat = _flatten_consortia(consortia)

    all_raw = pro["repository_projects"] + cons_flat
    all_raw = annotate_candidates(all_raw, df, threshold=0.15)

    for item in all_raw:
        item["processing_tips"] = _suggest_processing(item, profile)
        item["is_novel"] = _is_novel(item, known)

    buckets = apply_filters(all_raw, df, cfg=filter_cfg)

    pride_novel = [p for p in pride_raw if _is_novel(p, known)]
    pdc_novel = [p for p in pdc_raw if _is_novel(p, known)]
    pub_novel = [p for p in pubs_raw if _is_novel(p, known)]
    cons_novel = [c for c in cons_flat if _is_novel(c, known)]

    for item in buckets.get("recommended", []):
        item["recommendation"] = "review_for_catalog"
    for item in buckets.get("already_in_catalog", []):
        item["recommendation"] = "already_have"
    for item in buckets.get("filtered_out", []):
        item["recommendation"] = "filtered_out"
    for item in buckets.get("duplicate_similar", []):
        item["recommendation"] = "duplicate_similar"
    for item in buckets.get("requires_manual_check", []):
        item["recommendation"] = "requires_manual_check"
    for item in buckets.get("rejected", []):
        item["recommendation"] = "rejected"

    known_acc = {
        primary_project_id(str(x)).upper()
        for x in df["Project ID"].dropna()
        if str(x).strip()
    }
    qc_out = build_qc_outputs(buckets, known_acc)
    new_projects = qc_out["candidates"]

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "policy": policy_summary(),
        "catalog_profile": profile,
        "summary": {
            "catalog_rows": len(df),
            "catalog_unique_ids": profile["n_unique_ids"],
            "novel_pride": len(pride_novel),
            "novel_pdc": len(pdc_novel),
            "novel_publications": len(pub_novel),
            "novel_consortia": len(cons_novel),
            "novel_total": len(pro["repository_projects"]),
            "new_projects": len(new_projects),
            "candidates": len(new_projects),
            "manual_check": len(qc_out["manual_check"]),
            "rejected_material": len(qc_out["rejected_material"]),
            "review_recommended": len(new_projects),
            "already_in_catalog": len(buckets.get("already_in_catalog", [])),
            "filtered_out": len(buckets.get("filtered_out", [])),
            "requires_manual_check": len(buckets.get("requires_manual_check", [])),
            "rejected": len(buckets.get("rejected", [])),
            "human_filtered": sum(
                1 for x in buckets.get("filtered_out", [])
                if any("Human only" in r or "Не human" in r for r in (x.get("filter_reasons") or []))
            ),
            "duplicate_similar": len(buckets.get("duplicate_similar", [])),
            "articles_skipped": max(0, len(buckets.get("recommended", [])) - len(new_projects)),
            "source_stats": source_stats,
        },
        "filters_applied": filter_cfg,
        "new_projects": new_projects,
        "candidates": new_projects,
        "recommended": new_projects,
        "manual_check": qc_out["manual_check"],
        "rejected_material": qc_out["rejected_material"],
        "already_in_catalog": buckets.get("already_in_catalog", [])[:20],
        "filtered_out": buckets.get("filtered_out", [])[:50],
        "requires_manual_check_raw": buckets.get("requires_manual_check", [])[:50],
        "rejected_raw": buckets.get("rejected", [])[:50],
        "duplicate_similar": buckets.get("duplicate_similar", [])[:15],
        "novel_pride": pride_novel[:30],
        "novel_publications": [],
        "novel_consortia": [],
        "consortia_raw_counts": {k: len(v) for k, v in consortia.items()},
        "processing_notes": [
            "Каталог projects.csv только читается — удаление запрещено",
            "Новые PXD/PDC добавляются вручную или через run_revisor.py add --apply",
            "Запускайте scan еженедельно: python run_discovery.py scan",
        ],
    }

    reports_dir = Path((cfg.get("paths") or {}).get("reports_dir") or root / "reports")
    reports_dir.mkdir(parents=True, exist_ok=True)
    md_path = reports_dir / f"discovery_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    md_path.write_text(_to_markdown(report), encoding="utf-8")
    json_path = reports_dir / f"discovery_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    report["report_md"] = str(md_path)
    report["report_json"] = str(json_path)

    from atlas_agent.viz.discovery_html import generate_discovery_html

    html_path = generate_discovery_html(report, reports_dir / "discovery_index.html")
    report["report_html"] = str(html_path)
    qc_html = generate_qc_html(report, reports_dir / "discovery_qc_report.html")
    report["report_qc_html"] = str(qc_html)

    from atlas_agent.viz.publish_site import publish_discovery_site

    site_dir = publish_discovery_site(report, root)
    report["report_site_dir"] = str(site_dir)

    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    hist_path = save_scan(report, root)
    report["history_file"] = str(hist_path)

    return report


def _to_markdown(report: dict) -> str:
    s = report.get("summary") or {}
    lines = [
        "# Discovery Agent — отчёт",
        "",
        f"Сгенерировано: {report.get('generated_at', '')}",
        "",
        "## Политика",
        "",
        "- **projects.csv: только чтение, удаление запрещено**",
        "- Агент только предлагает новые проекты и статьи",
        "",
        "## Сводка",
        "",
        f"- Строк в каталоге: **{s.get('catalog_rows', 0)}**",
        f"- Уникальных ID: **{s.get('catalog_unique_ids', 0)}**",
        f"- **Новых проектов (PXD/PDC/MSV/IPX): {s.get('new_projects', 0)}**",
        f"- PRIDE (v3 search): {s.get('source_stats', {}).get('pride_v3_search', 0)}",
        f"- PDC (uiStudySummary): {s.get('source_stats', {}).get('pdc_uiStudySummary', 0)}",
        f"- Из публикаций (resolved): {s.get('source_stats', {}).get('literature_resolved', 0)}",
        f"- Пропущено статей без номера проекта: {s.get('articles_skipped', 0)}",
        f"- Уже в каталоге: {s.get('already_in_catalog', 0)}",
        f"- Отфильтровано (technical): {s.get('filtered_out', 0)}",
        f"- **QC candidate:** {s.get('candidates', 0)}",
        f"- **QC manual check:** {s.get('manual_check', 0)}",
        f"- **QC rejected (material):** {s.get('rejected_material', 0)}",
        "",
    ]
    lines.extend(qc_markdown_summary(report).splitlines())
    lines.append("")

    prof = report.get("catalog_profile") or {}
    if prof.get("top_organs"):
        lines.append("## Ваш атлас (профиль поиска)")
        lines.append("")
        lines.append(f"- Органы: {', '.join(prof['top_organs'][:8])}")
        lines.append(f"- Базы: {prof.get('databases', {})}")
        lines.append("")

    items = report.get("new_projects") or []
    lines.append("## Новые проекты")
    lines.append("")
    if not items:
        lines.append("_Новых проектов с номером PXD/PDC/MSV/IPX не найдено._")
    for it in items[:25]:
        acc = it.get("project_accession") or it.get("accession") or "?"
        title = (it.get("title") or "")[:100]
        sim = it.get("similar_in_catalog") or []
        sim_s = f" → похож на {sim[0]['project_id']}" if sim else ""
        lines.append(f"- **{acc}** {title}{sim_s}")
    lines.append("")

    return "\n".join(lines)


def load_catalog_readonly(csv_path: str) -> pd.DataFrame:
    assert_catalog_read_only("read")
    return load_projects_table(csv_path)
