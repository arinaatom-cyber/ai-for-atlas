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
from atlas_agent.discovery.search_limits import optional_cap
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

    lit_cap = optional_cap(disc.get("publications_max"))
    lit_page = page_size if lit_cap is None else max(page_size, lit_cap)
    pubs_raw, search_stats = search_atlas_literature(
        year_from=year_from,
        year_to=year_to,
        page_size=lit_page,
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
    pride_max: int | None = None,
    pub_max: int | None = 40,
    massive_max: int | None = None,
    iprox_max: int | None = None,
    pride_keywords: list[str] | None = None,
    profile_keywords: list[str] | None = None,
    known_accessions: set[str] | None = None,
    min_tmt_channels: int = 7,
    max_tmt_channels: int = 18,
    cfg: dict | None = None,
    atlas_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    known = {a.upper() for a in (known_accessions or set())}
    disc = (cfg or {}).get("discovery") or {}

    pride_cap = optional_cap(pride_max) if pride_max is not None else optional_cap(disc.get("pride_max"))
    pride_stats: dict[str, Any] = {}
    pride_raw = search_pride_json(
        keywords=pride_keywords,
        profile_keywords=profile_keywords,
        year_from=year_from,
        year_to=year_to,
        page_size=100,
        max_results=pride_cap,
        max_pages=20,
        exclude_accessions=known,
        stats=pride_stats,
    )

    from atlas_agent.discovery.filters import ATLAS_TMT_PLEXES

    pdc_cfg = disc.get("pdc") or {}
    pdc_stats: dict[str, Any] = {}
    pdc_raw = search_pdc_tmt_studies(
        known_accessions=known,
        allowed_plexes=set(pdc_cfg.get("allowed_plexes") or ATLAS_TMT_PLEXES),
        reject_plexes=set(pdc_cfg.get("reject_plexes") or [2, 6]),
        min_channels=int(pdc_cfg.get("min_plex_channels") or 7),
        exclude_programs=pdc_cfg.get("exclude_programs") or [],
        stats=pdc_stats,
    )

    massive_cap = optional_cap(massive_max) if massive_max is not None else optional_cap(disc.get("massive_max"))
    iprox_cap = optional_cap(iprox_max) if iprox_max is not None else optional_cap(disc.get("iprox_max"))
    pub_cap = optional_cap(pub_max) if pub_max is not None else optional_cap(disc.get("publications_max"))

    massive_stats: dict[str, Any] = {}
    massive_raw = search_massive_tmt(
        pride_keywords,
        max_results=massive_cap,
        exclude_accessions=known,
        stats=massive_stats,
    )

    iprox_stats: dict[str, Any] = {}
    iprox_raw = search_iprox_tmt(
        pride_keywords,
        max_results=iprox_cap,
        exclude_accessions=known,
        stats=iprox_stats,
    )

    pubs_raw, abstract_ai_stats = search_publications_professional(
        year_from=year_from,
        year_to=year_to,
        page_size=pub_cap or 200,
        cfg=cfg,
        atlas_context=atlas_context,
    )
    pride_from_pubs: list[dict] = []
    semantic_from_pubs: list[dict] = []
    literature_candidates: list[dict] = []
    if disc.get("abstract_resolve_accessions", False):
        pride_from_pubs = publications_to_projects(
            pubs_raw, known_accessions=known, max_resolve=pub_cap or 40
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
            "abstract_llm_errors": abstract_ai_stats.get("llm_errors") or {},
            "abstract_summary_sanitize": abstract_ai_stats.get("summary_sanitize") or {},
            "abstract_atlas_fit_yes": abstract_ai_stats.get("atlas_fit_yes", 0),
            "abstract_atlas_fit_maybe": abstract_ai_stats.get("atlas_fit_maybe", 0),
            "literature_raw_hits": (abstract_ai_stats.get("literature_search") or {}).get("raw_hits", 0),
            "literature_prefilter_kept": (abstract_ai_stats.get("literature_search") or {}).get("prefilter_kept", 0),
            "literature_with_repo_id": (abstract_ai_stats.get("literature_search") or {}).get("with_repository_id", 0),
            "literature_preprints": (abstract_ai_stats.get("literature_search") or {}).get("preprints", 0),
            "literature_peer_reviewed": (abstract_ai_stats.get("literature_search") or {}).get("peer_reviewed", 0),
            "pdc_tmt_plex_unspecified": pdc_stats.get("tmt_plex_unspecified", 0),
            "regex_only_publications": (abstract_ai_stats.get("regex_only_publications") or [])[:80],
            "failed_source_requests": {
                "pride": pride_stats.get("failed_requests", 0),
                "pdc": pdc_stats.get("failed_requests", 0),
                "massive": massive_stats.get("failed_requests", 0),
                "iprox": iprox_stats.get("failed_requests", 0),
            },
        },
    }
