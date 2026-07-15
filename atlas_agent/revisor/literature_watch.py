"""Поиск новых TMT human proteomics (Europe PMC + PRIDE JSON)."""
from __future__ import annotations

import re
import time
from typing import Any

import requests

from atlas_agent.discovery.filters import extract_ids_from_text
from atlas_agent.sources.literature import fetch_abstract
from atlas_agent.sources.pride import (
    fetch_projects_json,
    project_to_record,
    search_pride_json,
)
from atlas_agent.sources.projects_table import primary_project_id

EUROPE_PMC = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"


def search_new_publications(
    *,
    query: str | None = None,
    year_from: int = 2026,
    year_to: int = 2026,
    page_size: int = 25,
) -> list[dict[str, Any]]:
    q = query or f"(TMT OR isobaric OR proteomics) AND HUMAN AND PUB_YEAR:[{year_from} TO {year_to}]"
    params = {"query": q, "format": "json", "pageSize": min(page_size, 100), "resultType": "core"}
    hits = []
    for attempt in range(3):
        try:
            r = requests.get(EUROPE_PMC, params=params, timeout=45)
            r.raise_for_status()
            hits = (r.json().get("resultList") or {}).get("result") or []
            break
        except requests.RequestException:
            if attempt < 2:
                time.sleep(2 ** attempt)
            else:
                return []
    out = []
    for h in hits:
        pmid = str(h.get("pmid") or h.get("id") or "")
        title = h.get("title") or ""
        abstract = h.get("abstractText") or ""
        data_avail = ""
        for key in ("dataAvailability", "dataAvailabilityStatement"):
            if h.get(key):
                data_avail += " " + str(h[key])
        blob = f"{title} {abstract} {data_avail}"
        ids = extract_ids_from_text(blob)
        out.append(
            {
                "pmid": pmid,
                "title": title[:500],
                "abstract": abstract[:4000],
                "data_availability": data_avail.strip()[:2000],
                "journal": h.get("journalTitle", ""),
                "year": h.get("pubYear", ""),
                "doi": h.get("doi", ""),
                "pxd_mentioned": ids.get("PXD") or [],
                "accessions_mentioned": sum((ids.get(k) or [] for k in ("PXD", "PDC", "MSV", "IPX")), []),
                "source": "europe_pmc",
            }
        )
    return out


def discover_pride_2026(
    *,
    year_from: int = 2026,
    year_to: int = 2026,
    pride_max: int = 50,
    pub_max: int = 40,
    pride_keywords: list[str] | None = None,
    profile_keywords: list[str] | None = None,
    known_accessions: set[str] | None = None,
) -> tuple[list[dict], list[dict]]:
    """Обратная совместимость — делегирует в профессиональный поиск."""
    from atlas_agent.discovery.sources.pro_search import discover_projects_professional

    result = discover_projects_professional(
        year_from=year_from,
        year_to=year_to,
        pride_max=pride_max,
        pub_max=pub_max,
        pride_keywords=pride_keywords,
        profile_keywords=profile_keywords,
        known_accessions=known_accessions,
    )
    return result["repository_projects"], result["publications"]


def filter_novel_items(
    items: list[dict],
    known_pmids: set[str],
    known_pxds: set[str],
    *,
    id_key: str = "pmid",
    pxd_field: str = "pxd_mentioned",
) -> list[dict]:
    novel = []
    for it in items:
        if id_key == "pmid":
            pid = re.sub(r"\D", "", str(it.get("pmid") or ""))
            if pid and pid in known_pmids:
                continue
        acc = (it.get("accession") or it.get("projectAccession") or "").upper()
        if acc and acc in known_pxds:
            continue
        pxds = it.get(pxd_field) or []
        if pxds and all(p in known_pxds for p in pxds):
            continue
        novel.append(it)
    return novel


def build_known_sets(df) -> tuple[set[str], set[str]]:
    known_pmids: set[str] = set()
    known_pxds: set[str] = set()
    if "PMID" in df.columns:
        for v in df["PMID"].dropna():
            p = re.sub(r"\D", "", str(v))
            if p:
                known_pmids.add(p)
    if "Project ID" in df.columns:
        for v in df["Project ID"].dropna():
            known_pxds.add(primary_project_id(str(v)))
    return known_pmids, known_pxds


def scan_new_content(
    df,
    *,
    pride_max: int = 30,
    pub_max: int = 25,
    year_from: int = 2026,
    year_to: int = 2026,
    pride_keywords: list[str] | None = None,
    annotate_similar: bool = True,
    cfg: dict | None = None,
) -> dict[str, Any]:
    from atlas_agent.revisor.similarity import annotate_candidates

    known_pmids, known_pxds = build_known_sets(df)

    pride_all, pubs_raw = discover_pride_2026(
        year_from=year_from,
        year_to=year_to,
        pride_max=pride_max,
        pub_max=pub_max,
        pride_keywords=pride_keywords,
    )
    pride_novel = filter_novel_items(
        pride_all, known_pmids, known_pxds, id_key="accession"
    )
    pubs_novel = filter_novel_items(pubs_raw, known_pmids, known_pxds)

    for p in pubs_novel[:15]:
        pmid = re.sub(r"\D", "", str(p.get("pmid") or ""))
        if pmid and not p.get("abstract_snippet"):
            lit = fetch_abstract(pmid)
            if lit.get("found"):
                p["abstract_snippet"] = (lit.get("abstract") or "")[:400]

    if annotate_similar:
        pride_novel = annotate_candidates(pride_novel, df)
        pubs_novel = annotate_candidates(pubs_novel, df)

    github_novel: list[dict] = []
    if cfg and cfg.get("github"):
        try:
            from atlas_agent.sources.github_analyzer import build_github_integration_report

            gh = build_github_integration_report(cfg, df)
            github_novel = gh.get("novel_github_projects") or []
            if annotate_similar and github_novel:
                github_novel = annotate_candidates(github_novel, df)
        except Exception as e:
            github_novel = [{"error": str(e)}]

    return {
        "year_from": year_from,
        "year_to": year_to,
        "known_pmids": len(known_pmids),
        "known_pxds": len(known_pxds),
        "new_pride": pride_novel[:30],
        "new_publications": pubs_novel[:30],
        "pride_json_total": len(pride_all),
        "new_github_projects": github_novel[:30],
    }
