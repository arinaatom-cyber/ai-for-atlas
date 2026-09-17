"""Профессиональный поиск: репозитории первично, литература — для резолва accession."""
from __future__ import annotations

from typing import Any

from atlas_agent.discovery.abstract_reader import enrich_publications_with_ai
from atlas_agent.discovery.literature_search import search_atlas_literature
from atlas_agent.sources.dataset_resolve import (
    literature_semantic_candidates,
    publications_to_projects,
    resolve_semantic_publications,
)
from atlas_agent.sources.iprox import search_iprox_tmt
from atlas_agent.sources.massive import search_massive_tmt
from atlas_agent.sources.pdc import search_pdc_tmt_studies
from atlas_agent.sources.pride import search_pride_json


def search_publications_professional(
    *,
    year_from: int,
    year_to: int,
    page_size: int = 25,
    cfg: dict | None = None,
    atlas_context: dict[str, Any] | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    disc = (cfg or {}).get("discovery") or {}
    lit_cfg = disc.get("literature") or {}
    min_rel = float(lit_cfg.get("min_relevance") or 0.25)

    pubs_raw, search_stats = search_atlas_literature(
        year_from=year_from,
        year_to=year_to,
        page_size=max(page_size, int(disc.get("publications_max") or page_size)),
        min_relevance=min_rel,
    )

    enriched, ai_stats = enrich_publications_with_ai(
        pubs_raw, cfg=cfg, atlas_context=atlas_context
    )
    ai_stats = {**ai_stats, "literature_search": search_stats}
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
    max_tmt_channels: int = 18,
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
        reject_plexes=set(pdc_cfg.get("reject_plexes") or [2, 6]),
        min_channels=int(pdc_cfg.get("min_plex_channels") or 7),
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
            "literature_raw_hits": (abstract_ai_stats.get("literature_search") or {}).get("raw_hits", 0),
            "literature_prefilter_kept": (abstract_ai_stats.get("literature_search") or {}).get("prefilter_kept", 0),
            "literature_with_repo_id": (abstract_ai_stats.get("literature_search") or {}).get("with_repository_id", 0),
        },
    }
