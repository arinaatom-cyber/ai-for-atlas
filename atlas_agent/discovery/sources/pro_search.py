"""Профессиональный поиск: репозитории первично, литература — для резолва accession."""
from __future__ import annotations

from typing import Any

from atlas_agent.discovery.filters import extract_ids_from_text
from atlas_agent.revisor.literature_watch import search_new_publications
from atlas_agent.sources.dataset_resolve import publications_to_projects
from atlas_agent.sources.pdc import search_pdc_tmt_studies
from atlas_agent.sources.pride import search_pride_json


def _professional_pub_queries(year_from: int, year_to: int) -> list[str]:
    base = f"PUB_YEAR:[{year_from} TO {year_to}]"
    return [
        f"(TMT OR isobaric OR tandem mass tag) AND (PXD OR PDC OR MassIVE OR proteomexchange) AND HUMAN AND {base}",
        f"(TMT OR isobaric) AND (data availability OR supplementary) AND proteomics AND HUMAN AND {base}",
        f"(TMT OR isobaric) AND (cancer OR tumor OR clinical) AND proteomics AND HUMAN AND (PXD OR PDC) AND {base}",
    ]


def search_publications_professional(
    *,
    year_from: int,
    year_to: int,
    page_size: int = 25,
) -> list[dict[str, Any]]:
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
            ids = extract_ids_from_text(f"{p.get('title', '')} {p.get('abstract', '')}")
            p["extracted_ids_preview"] = ids
            p["pxd_mentioned"] = ids.get("PXD") or p.get("pxd_mentioned") or []
            out.append(p)
    return out[:page_size]


def discover_projects_professional(
    *,
    year_from: int = 2024,
    year_to: int = 2026,
    pride_max: int = 50,
    pub_max: int = 30,
    pride_keywords: list[str] | None = None,
    profile_keywords: list[str] | None = None,
    known_accessions: set[str] | None = None,
    min_tmt_channels: int = 7,
    max_tmt_channels: int = 16,
) -> dict[str, Any]:
    """
    1. PRIDE v3 /search/projects — свежие human TMT PXD
    2. PDC uiStudySummary — все TMT-исследования
    3. Europe PMC — публикации с PXD/PDC → резолв accession
    """
    known = {a.upper() for a in (known_accessions or set())}

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

    pdc_raw = search_pdc_tmt_studies(
        known_accessions=known,
        allowed_plexes=set(ATLAS_TMT_PLEXES),
    )

    pubs_raw = search_publications_professional(
        year_from=year_from,
        year_to=year_to,
        page_size=pub_max,
    )
    pride_from_pubs = publications_to_projects(pubs_raw, known_accessions=known, max_resolve=pub_max)

    merged: dict[str, dict] = {}
    for item in pride_raw + pdc_raw + pride_from_pubs:
        acc = (item.get("accession") or "").upper()
        if acc and acc not in known:
            merged[acc] = item

    return {
        "repository_projects": list(merged.values()),
        "pride_count": len(pride_raw),
        "pdc_count": len(pdc_raw),
        "pub_resolved_count": len(pride_from_pubs),
        "publications": pubs_raw,
        "sources": {
            "pride_v3_search": len(pride_raw),
            "pdc_uiStudySummary": len(pdc_raw),
            "literature_resolved": len(pride_from_pubs),
            "publications_scanned": len(pubs_raw),
        },
    }
