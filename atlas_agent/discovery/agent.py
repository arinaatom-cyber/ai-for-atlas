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

from atlas_agent.discovery.catalog_profile import build_atlas_semantic_context, build_catalog_profile
from atlas_agent.discovery.history import save_scan
from atlas_agent.discovery.policy import assert_catalog_read_only, policy_summary
from atlas_agent.discovery.sources.consortia import scan_all_consortia
from atlas_agent.discovery.sources.pro_search import discover_projects_professional
from atlas_agent.revisor.literature_watch import build_known_sets, filter_novel_items
from atlas_agent.discovery.filters import apply_filters, default_filter_config
from atlas_agent.discovery.qc_outputs import build_qc_outputs
from atlas_agent.viz.discovery_qc_html import generate_qc_html, qc_markdown_summary
from atlas_agent.revisor.similarity import annotate_candidates
from atlas_agent.sources.projects_table import load_catalog, primary_project_id
from atlas_agent.sources.proteomics_workbook import (
    atlas_project_count,
    ids_from_discovery_item,
    known_accessions_from_workbook,
    known_rejected_from_workbook,
    load_deleted_catalog,
)


def _known_accessions(df: pd.DataFrame, cfg: dict | None = None) -> set[str]:
    known_pmids, known_pxds = build_known_sets(df)
    known = known_pmids | known_pxds | {
        primary_project_id(str(x)).upper()
        for x in df["Project ID"].dropna()
        if str(x).strip()
    }
    # TMT ATLAS + CPTAC из project of Proteomics.xlsx (read-only)
    wb = (cfg or {}).get("sheet", {}).get("proteomics_workbook")
    if wb:
        path = Path(wb)
        if not path.is_absolute():
            path = Path(__file__).resolve().parents[2] / wb
        if path.is_file():
            known |= known_accessions_from_workbook(path)
    return known


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
    wb_cfg = (cfg.get("sheet") or {}).get("proteomics_workbook")
    rejected_titles: list[str] = []
    wb_path: Path | None = None
    if wb_cfg:
        wb_path = Path(wb_cfg)
        if not wb_path.is_absolute():
            wb_path = root / wb_cfg
        if wb_path.is_file():
            profile["n_atlas_projects"] = atlas_project_count(wb_path)
            profile["n_unique_ids"] = profile["n_atlas_projects"]
            try:
                rej_df = load_deleted_catalog(wb_path)
                rejected_titles = [
                    str(t) for t in rej_df.get("Title", pd.Series(dtype=str)).dropna().tolist()
                ]
            except Exception:
                rejected_titles = []
    atlas_context = build_atlas_semantic_context(df, rejected_titles=rejected_titles)
    profile["semantic"] = atlas_context
    known = _known_accessions(df, cfg)

    filter_cfg = {**default_filter_config(), **(scan_cfg.get("filters") or {})}

    pro = discover_projects_professional(
        year_from=year,
        year_to=int(scan_cfg.get("year_to") or 2026),
        pride_max=int(scan_cfg.get("pride_max") or 50),
        pub_max=int(scan_cfg.get("publications_max") or 30),
        massive_max=int(scan_cfg.get("massive_max") or 25),
        iprox_max=int(scan_cfg.get("iprox_max") or 25),
        pride_keywords=scan_cfg.get("pride_keywords") or ["TMT", "tandem mass tag", "isobaric"],
        profile_keywords=profile.get("search_keywords"),
        known_accessions=known,
        min_tmt_channels=int(filter_cfg.get("min_tmt_channels") or 7),
        max_tmt_channels=int(filter_cfg.get("max_tmt_channels") or 16),
        cfg=cfg,
        atlas_context=atlas_context,
    )
    literature_semantic = pro.get("literature_semantic_candidates") or []
    pride_raw = [p for p in pro["repository_projects"] if p.get("source", "").startswith("pride")]
    pdc_raw = [p for p in pro["repository_projects"] if p.get("source") == "pdc_api" or p.get("consortium") == "PDC"]
    pubs_raw = pro["publications"]
    source_stats = pro.get("sources") or {}

    cohort_literature: list[dict] = []
    cohort_stats: dict[str, Any] = {}
    cohort_cfg = scan_cfg.get("cohort_literature") or {}
    if cohort_cfg.get("enabled", True):
        from atlas_agent.discovery.cohort_literature import search_cohort_literature

        known_pmids, _ = build_known_sets(df)
        cohort_literature, cohort_stats = search_cohort_literature(
            year_from=int(cohort_cfg.get("year_from") or year),
            year_to=int(scan_cfg.get("year_to") or 2026),
            page_size=int(cohort_cfg.get("max_results") or 30),
            min_patients=int(cohort_cfg.get("min_patients") or 50),
            min_score=int(cohort_cfg.get("min_score") or 25),
            known_pmids=known_pmids,
        )

    # Консорциумы (литература CPTAC/CCLE/GTEx — дополнительно)
    consortia = scan_all_consortia(profile.get("search_keywords"), year_from=year)
    cons_flat = _flatten_consortia(consortia)

    all_raw = pro["repository_projects"] + cons_flat
    all_raw = annotate_candidates(all_raw, df, threshold=0.15)

    for item in all_raw:
        item["processing_tips"] = _suggest_processing(item, profile)
        item["is_novel"] = _is_novel(item, known)

    buckets = apply_filters(all_raw, df, cfg=filter_cfg)

    if literature_semantic:
        buckets.setdefault("requires_manual_check", []).extend(literature_semantic)

    rejected_known: set[str] = set()
    wb = (cfg.get("sheet") or {}).get("proteomics_workbook")
    if wb:
        wb_path = Path(wb)
        if not wb_path.is_absolute():
            wb_path = root / wb
        if wb_path.is_file():
            rejected_known = known_rejected_from_workbook(wb_path)

    if rejected_known:
        for key in list(buckets.keys()):
            kept = []
            for item in buckets.get(key, []):
                if ids_from_discovery_item(item) & rejected_known:
                    item = dict(item)
                    item["verdict"] = "rejected"
                    item["filter_reasons"] = (item.get("filter_reasons") or []) + [
                        "удалено из general (лист отклонённых)"
                    ]
                    item["recommendation"] = "rejected_previously_removed"
                    buckets.setdefault("rejected", []).append(item)
                else:
                    kept.append(item)
            buckets[key] = kept

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

    from atlas_agent.discovery.data_availability import annotate_data_availability, literature_data_hint, summarize_availability

    tmt_root = (cfg.get("paths") or {}).get("tmt_projects_dir") or ""
    scan_cfg_da = scan_cfg.get("data_availability") or {}
    if scan_cfg_da.get("enabled", True):
        for key in ("candidates", "manual_check", "rejected_material"):
            items = qc_out.get(key) or []
            if items:
                annotate_data_availability(
                    items,
                    tmt_root=tmt_root,
                    fetch_remote=scan_cfg_da.get("fetch_remote", True),
                    delay_s=float(scan_cfg_da.get("delay_s", 0.12)),
                )
        new_projects = qc_out["candidates"]

    from atlas_agent.viz.portal_index import format_finding_note

    for bucket_key in ("candidates", "manual_check", "rejected_material"):
        for item in qc_out.get(bucket_key) or []:
            if not item.get("finding_note"):
                item["finding_note"] = format_finding_note(item)

    data_avail_summary = summarize_availability(
        (qc_out.get("candidates") or [])
        + (qc_out.get("manual_check") or [])
    )

    pubs_for_site: list[dict] = []
    for p in pubs_raw[:50]:
        ai = p.get("abstract_ai") or {}
        pubs_for_site.append(
            {
                "pmid": p.get("pmid", ""),
                "title": (p.get("title") or "")[:400],
                "doi": p.get("doi", ""),
                "journal": p.get("journal", ""),
                "year": p.get("year", ""),
                "abstract_snippet": (p.get("abstract") or "")[:500],
                "abstract_reader": p.get("abstract_reader", ""),
                "atlas_fit": ai.get("atlas_fit") or p.get("atlas_fit"),
                "atlas_fit_score": ai.get("atlas_fit_score") or p.get("atlas_fit_score"),
                "semantic_evidence": (ai.get("semantic_evidence") or [])[:6],
                "similar_atlas_theme": ai.get("similar_atlas_theme", ""),
                "summary_ru": ai.get("summary_ru", ""),
                "organism": ai.get("organism", ""),
                "tmt": ai.get("tmt", ""),
                "material": ai.get("material", ""),
                "data_availability": (p.get("data_availability") or "")[:800],
                "data_hint": literature_data_hint(p),
            }
        )

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "policy": policy_summary(),
        "catalog_profile": profile,
        "summary": {
            "catalog_rows": len(df),
            "catalog_unique_ids": profile.get("n_atlas_projects") or profile["n_unique_ids"],
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
            "data_availability": data_avail_summary,
            "cohort_literature": cohort_stats,
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
        "publications_analyzed": pubs_for_site,
        "literature_semantic": literature_semantic[:40],
        "cohort_literature": cohort_literature,
        "novel_publications": pub_novel[:30],
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
    da = s.get("data_availability") or {}
    if da:
        lines.append("## Data availability (Result Files)")
        lines.append("")
        for st, n in sorted(da.items(), key=lambda x: -x[1]):
            lines.append(f"- **{st}:** {n}")
        lines.append("")
    cl = s.get("cohort_literature") or {}
    if cl:
        lines.append("## Cohort literature (text mining)")
        lines.append("")
        lines.append(f"- Scanned: **{cl.get('scanned', 0)}** · kept: **{cl.get('kept', 0)}**")
        lines.append("")
    cohort_items = report.get("cohort_literature") or []
    if cohort_items:
        lines.append("### Top cohort papers")
        lines.append("")
        for it in cohort_items[:10]:
            n = it.get("patient_n") or "?"
            lines.append(
                f"- PMID **{it.get('pmid', '?')}** N≈{n} — {(it.get('title') or '')[:70]}"
            )
        lines.append("")
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


def load_catalog_readonly(cfg: dict) -> pd.DataFrame:
    assert_catalog_read_only("read")
    return load_catalog(cfg)
