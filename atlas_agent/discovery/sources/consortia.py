"""Поиск по консорциумам: PDC, CCLE, GTEx, CPTAC (публикации + API где доступно)."""
from __future__ import annotations

import re
from typing import Any

import requests

from atlas_agent.discovery.filters import extract_ids_from_text

EUROPE_PMC = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
PDC_GRAPHQL = "https://pdc.cancer.gov/graphql"

CONSORTIA = {
    "PDC": {
        "keywords": ["proteomic data commons", "PDC", "CPTAC proteomics"],
        "id_prefix": "PDC",
    },
    "CCLE": {
        "keywords": ["CCLE", "Cancer Cell Line Encyclopedia", "cell line proteomics TMT"],
        "id_prefix": "MSV",
    },
    "GTEx": {
        "keywords": ["GTEx", "Genotype-Tissue Expression", "tissue proteomics"],
        "id_prefix": "GTEx",
    },
    "CPTAC": {
        "keywords": ["CPTAC", "clinical proteomic tumor analysis"],
        "id_prefix": "PDC",
    },
}


def search_europe_pmc_consortium(
    consortium: str,
    *,
    extra_terms: list[str] | None = None,
    year_from: int = 2023,
    page_size: int = 15,
) -> list[dict[str, Any]]:
    meta = CONSORTIA.get(consortium, {})
    terms = list(meta.get("keywords", [consortium]))
    if extra_terms:
        terms.extend(extra_terms[:3])
    q = f"({' OR '.join(terms)}) AND (TMT OR proteomics OR mass spectrometry) AND PUB_YEAR:[{year_from} TO 2026]"
    try:
        r = requests.get(
            EUROPE_PMC,
            params={"query": q, "format": "json", "pageSize": min(page_size, 50), "resultType": "core"},
            timeout=45,
        )
        r.raise_for_status()
        hits = (r.json().get("resultList") or {}).get("result") or []
    except requests.RequestException:
        return []
    out = []
    for h in hits:
        title = h.get("title") or ""
        abstract = h.get("abstractText") or ""
        blob = f"{title} {abstract}"
        for key in ("dataAvailability", "dataAvailabilityStatement"):
            if h.get(key):
                blob += " " + str(h[key])
        ids = sorted(
            set(_extract_accessions(blob, meta.get("id_prefix", "")))
            | set(sum((extract_ids_from_text(blob).get(k) or [] for k in ("PXD", "PDC", "MSV", "IPX")), []))
        )
        out.append(
            {
                "source": f"europe_pmc_{consortium.lower()}",
                "consortium": consortium,
                "pmid": str(h.get("pmid") or ""),
                "title": title[:300],
                "year": h.get("pubYear", ""),
                "doi": h.get("doi", ""),
                "accessions_mentioned": ids,
                "url": f"https://pubmed.ncbi.nlm.nih.gov/{h.get('pmid')}/" if h.get("pmid") else "",
            }
        )
    return out


def _extract_accessions(text: str, prefix: str) -> list[str]:
    patterns = [
        r"PDC\d{6,9}",
        r"PXD\d{6,9}",
        r"MSV\d{6,12}",
        r"CPTAC-[A-Z0-9-]+",
    ]
    if prefix:
        patterns.insert(0, rf"{re.escape(prefix)}\w{{4,12}}")
    found = set()
    for p in patterns:
        for m in re.finditer(p, text, re.I):
            found.add(m.group(0).upper())
    return sorted(found)


def search_pdc_studies(
    query: str = "TMT",
    *,
    limit: int = 20,
    known_accessions: set[str] | None = None,
) -> list[dict[str, Any]]:
    """PDC GraphQL uiStudySummary — TMT-исследования (read-only)."""
    from atlas_agent.sources.pdc import search_pdc_tmt_studies

    return search_pdc_tmt_studies(known_accessions=known_accessions)[:limit]


def scan_all_consortia(
    profile_keywords: list[str] | None = None,
    *,
    year_from: int = 2023,
) -> dict[str, list[dict]]:
    extra = profile_keywords or []
    result = {}
    for name in ("PDC", "CCLE", "GTEx", "CPTAC"):
        try:
            result[name] = search_europe_pmc_consortium(
                name, extra_terms=extra, year_from=year_from, page_size=12
            )
        except Exception as e:
            result[name] = [{"error": str(e), "consortium": name}]
    try:
        result["PDC_API"] = search_pdc_studies("TMT", limit=25)
    except Exception as e:
        result["PDC_API"] = [{"error": str(e)}]
    return result
