"""Профессиональный поиск: репозитории первично, литература — для резолва accession."""
from __future__ import annotations

from typing import Any

from atlas_agent.discovery.abstract_reader import enrich_publications_with_ai
from atlas_agent.revisor.literature_watch import search_new_publications
from atlas_agent.sources.dataset_resolve import (
    literature_semantic_candidates,
    publications_to_projects,
    resolve_semantic_publications,
)
from atlas_agent.sources.iprox import search_iprox_tmt
from atlas_agent.sources.massive import search_massive_tmt
from atlas_agent.sources.pdc import search_pdc_tmt_studies
from atlas_agent.sources.pride import search_pride_json


def _professional_pub_queries(year_from: int, year_to: int) -> list[str]:
    """Статьи по смыслу (TMT + пациенты) — без PXD/PDC в запросе."""
    base = f"PUB_YEAR:[{year_from} TO {year_to}]"
    return [
        f"(TMT OR isobaric OR tandem mass tag) AND proteomics AND (patient OR clinical OR cohort) AND HUMAN AND {base}",
        f"(TMT OR isobaric) AND (tumor OR cancer OR plasma OR biopsy) AND proteomics AND HUMAN AND {base}",
        f"(TMT OR isobaric) AND quantitative proteomics AND HUMAN AND {base}",
    ]


def search_publications_professional(
    *,
    year_from: int,
    year_to: int,
    page_size: int = 25,
    cfg: dict | None = None,
    atlas_context: dict[str, Any] | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    seen_pmids: set[str] = set()
    out: list[dict[str, Any]] = []
    per_query = max(10, page_size // len(_professional_pub_queries(year_from, year_to)))
    for q in _professional_pub_queries(year_from, year_to):
        batch = search_new_publications(query=q, year_from=year_from, year_to=year_to, page_size=per_query)
        for p in batch:
            pmid = str(p.get("pmid") or "")
            if pmid and pmid in seen_pmids:
                continue
            if pmid:
                seen_pmids.add(pmid)
            out.append(p)
    trimmed = out[:page_size]
    enriched, ai_stats = enrich_publications_with_ai(
        trimmed, cfg=cfg, atlas_context=atlas_context
    )
    return enriched, ai_stats


def discover_projects_professional(
    *,
    year_from: int = 2024,
    year_to: int = 2026,
    pride_max: int = 50,
    pub_max: int = 30,
    massive_max: int = 25,
    iprox_max: int = 25,
    pride_keywords: list[str] | None = None,
    profile_keywords: list[str] | None = None,
    known_accessions: set[str] | None = None,
    min_tmt_channels: int = 7,
    max_tmt_channels: int = 16,
    cfg: dict | None = None,
    atlas_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    1. PRIDE v3 JSON /search/projects + /projects/{PXD}
    2. PDC GraphQL uiStudySummary
    3. MassIVE JSON datasets_json.jsp
    4. iProX JSON search
    5. Europe PMC — статьи/абстракты → PXD/PDC/MSV/IPX
    """
    known = {a.upper() for a in (known_accessions or set())}
    disc = (cfg or {}).get("discovery") or {}

    pride_raw = search_pride_json(
        keywords=pride_keywords,
        profile_keywords=profile_keywords,
        year_from=year_from,
        year_to=year_to,
        page_size=pride_max,
        max_pages=8,
        exclude_accessions=known,
    )

    from atlas_agent.discovery.filters import ATLAS_TMT_PLEXES

    pdc_cfg = disc.get("pdc") or {}
    pdc_raw = search_pdc_tmt_studies(
        known_accessions=known,
        allowed_plexes=set(pdc_cfg.get("allowed_plexes") or ATLAS_TMT_PLEXES),
        reject_plexes=set(pdc_cfg.get("reject_plexes") or [6, 7, 8, 9, 18]),
        min_channels=int(pdc_cfg.get("min_plex_channels") or 10),
        exclude_programs=pdc_cfg.get("exclude_programs") or [],
    )

    massive_raw = search_massive_tmt(
        pride_keywords,
        max_results=massive_max,
        exclude_accessions=known,
    )

    iprox_raw = search_iprox_tmt(
        pride_keywords,
        max_results=iprox_max,
        exclude_accessions=known,
    )

    pubs_raw, abstract_ai_stats = search_publications_professional(
        year_from=year_from,
        year_to=year_to,
        page_size=pub_max,
        cfg=cfg,
        atlas_context=atlas_context,
    )
    pride_from_pubs: list[dict] = []
    semantic_from_pubs: list[dict] = []
    literature_candidates: list[dict] = []
    if disc.get("abstract_resolve_accessions", False):
        pride_from_pubs = publications_to_projects(
            pubs_raw, known_accessions=known, max_resolve=pub_max
        )
    if disc.get("abstract_semantic_resolve", False):
        semantic_from_pubs = resolve_semantic_publications(
            pubs_raw,
            known_accessions=known,
            year_from=year_from,
            year_to=year_to,
            max_resolve=int(disc.get("abstract_semantic_max") or 12),
        )
    if disc.get("abstract_llm", True):
        literature_candidates = literature_semantic_candidates(pubs_raw, known_accessions=known)

    merged: dict[str, dict] = {}
    for item in pride_raw + pdc_raw + massive_raw + iprox_raw + pride_from_pubs + semantic_from_pubs:
        acc = (item.get("accession") or "").upper()
        if acc and acc not in known:
            merged[acc] = item

    return {
        "repository_projects": list(merged.values()),
        "pride_count": len(pride_raw),
        "pdc_count": len(pdc_raw),
        "pub_resolved_count": len(pride_from_pubs),
        "semantic_resolved_count": len(semantic_from_pubs),
        "literature_semantic_candidates": literature_candidates,
        "publications": pubs_raw,
        "abstract_ai_stats": abstract_ai_stats,
        "massive_count": len(massive_raw),
        "iprox_count": len(iprox_raw),
        "sources": {
            "pride_v3_search": len(pride_raw),
            "pdc_uiStudySummary": len(pdc_raw),
            "massive_json": len(massive_raw),
            "iprox_json": len(iprox_raw),
            "literature_resolved": len(pride_from_pubs),
            "semantic_from_abstract": len(semantic_from_pubs),
            "literature_semantic_manual": len(literature_candidates),
            "publications_scanned": len(pubs_raw),
            "abstract_llm_read": abstract_ai_stats.get("llm_read", 0),
            "abstract_regex_only": abstract_ai_stats.get("regex_only", 0),
            "abstract_atlas_fit_yes": abstract_ai_stats.get("atlas_fit_yes", 0),
            "abstract_atlas_fit_maybe": abstract_ai_stats.get("atlas_fit_maybe", 0),
        },
    }
