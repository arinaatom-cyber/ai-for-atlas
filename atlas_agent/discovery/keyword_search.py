"""Поиск новых проектов по ключевым словам (каталог + config) с ИИ-разбором абстрактов."""
from __future__ import annotations

from typing import Any

import pandas as pd

from atlas_agent.discovery.agent import _known_accessions
from atlas_agent.discovery.catalog_profile import build_atlas_semantic_context, build_catalog_profile
from atlas_agent.discovery.filters import apply_filters, default_filter_config
from atlas_agent.discovery.sources.pro_search import discover_projects_professional
from atlas_agent.revisor.literature_watch import build_known_sets, filter_novel_items, search_new_publications
from atlas_agent.revisor.similarity import annotate_candidates


def default_search_keywords(cfg: dict, profile: dict | None = None) -> list[str]:
    """Ключевые слова: pride_keywords из config + органы/болезни из TMT ATLAS."""
    disc = cfg.get("discovery") or {}
    scan = cfg.get("scan") or {}
    base = list(disc.get("pride_keywords") or scan.get("pride_keywords") or ["TMT", "tandem mass tag", "isobaric"])
    if profile:
        for k in profile.get("search_keywords") or []:
            if k and k not in base:
                base.append(k)
    seen: set[str] = set()
    out: list[str] = []
    for k in base:
        kl = k.strip()
        if kl and kl.lower() not in seen:
            seen.add(kl.lower())
            out.append(kl)
    return out[:24]


def build_literature_query(keywords: list[str], year_from: int, year_to: int) -> str:
    """Europe PMC: TMT + тематика из ключевых слов."""
    tmt = [k for k in keywords if any(x in k.lower() for x in ("tmt", "isobaric", "mass tag", "plex"))]
    theme = [k for k in keywords if k not in tmt][:6]
    core = " OR ".join(f'"{k}"' for k in (tmt[:4] or ["TMT", "isobaric", "tandem mass tag"]))
    if theme:
        theme_part = " OR ".join(f'"{k}"' for k in theme)
    else:
        theme_part = "patient OR cancer OR tumor OR plasma OR biopsy"
    return (
        f"({core}) AND ({theme_part}) AND proteomics AND HUMAN "
        f"AND PUB_YEAR:[{year_from} TO {year_to}]"
    )


def run_keyword_ai_search(
    df: pd.DataFrame,
    cfg: dict,
    *,
    keywords: list[str] | None = None,
    extra_query: str = "",
    year_from: int = 2024,
    year_to: int = 2026,
    pride_max: int = 25,
    pub_max: int = 15,
    massive_max: int = 15,
    iprox_max: int = 10,
) -> dict[str, Any]:
    """
    Лёгкий поиск для Streamlit: PRIDE/PDC/MassIVE/iProX + Europe PMC + ИИ на абстрактах.
    Каталог только read-only; новые ID не добавляются автоматически.
    """
    profile = build_catalog_profile(df)
    kw = [k.strip() for k in (keywords or default_search_keywords(cfg, profile)) if k.strip()]
    known = _known_accessions(df, cfg)
    known_pmids, known_pxds = build_known_sets(df)
    atlas_ctx = build_atlas_semantic_context(df)

    disc = cfg.get("discovery") or {}
    filt_cfg = {**default_filter_config(), **(disc.get("filters") or {})}

    pro = discover_projects_professional(
        year_from=year_from,
        year_to=year_to,
        pride_max=pride_max,
        pub_max=pub_max,
        massive_max=massive_max,
        iprox_max=iprox_max,
        pride_keywords=kw[:8],
        profile_keywords=kw,
        known_accessions=known,
        cfg=cfg,
        atlas_context=atlas_ctx,
    )

    repo_raw = pro.get("repository_projects") or []
    pubs_raw = pro.get("publications") or []

    epmc_q = build_literature_query(kw, year_from, year_to)
    if extra_query.strip():
        epmc_q = f"({extra_query.strip()}) AND HUMAN AND PUB_YEAR:[{year_from} TO {year_to}]"

    extra_pubs = search_new_publications(query=epmc_q, year_from=year_from, year_to=year_to, page_size=pub_max)
    seen_pmids = {str(p.get("pmid") or "") for p in pubs_raw}
    for p in extra_pubs:
        pmid = str(p.get("pmid") or "")
        if pmid and pmid not in seen_pmids:
            seen_pmids.add(pmid)
            pubs_raw.append(p)

    if disc.get("abstract_llm", True) and pubs_raw:
        from atlas_agent.discovery.abstract_reader import enrich_publications_with_ai

        pubs_raw, ai_stats = enrich_publications_with_ai(
            pubs_raw[:pub_max],
            cfg=cfg,
            atlas_context=atlas_ctx,
        )
    else:
        ai_stats = {}

    repo_novel = filter_novel_items(repo_raw, known_pmids, known_pxds, id_key="accession")
    pubs_novel = filter_novel_items(pubs_raw, known_pmids, known_pxds)

    repo_novel = annotate_candidates(repo_novel, df)
    pubs_novel = annotate_candidates(pubs_novel, df)

    filtered_repo, filter_stats = apply_filters(repo_novel, df, filt_cfg)

    return {
        "keywords": kw,
        "literature_query": epmc_q,
        "year_from": year_from,
        "year_to": year_to,
        "repository_hits": repo_raw,
        "repository_novel": repo_novel,
        "repository_candidates": filtered_repo,
        "publications": pubs_novel,
        "source_stats": {
            "pride": pro.get("pride_count", 0),
            "pdc": pro.get("pdc_count", 0),
            "massive": pro.get("massive_count", 0),
            "iprox": pro.get("iprox_count", 0),
            "publications": len(pubs_raw),
            **(ai_stats or {}),
            **(filter_stats or {}),
        },
        "abstract_ai_stats": ai_stats,
    }
