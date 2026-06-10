"""Резолв PXD/PDC/MSV/IPX из публикаций (Europe PMC, DOI)."""
from __future__ import annotations

import re
import time
from typing import Any

import requests

from atlas_agent.discovery.filters import extract_ids_from_text

EUROPE_PMC = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
PRIDE_API = "https://www.ebi.ac.uk/pride/ws/archive/v3"


def _epmc_get(params: dict, *, retries: int = 3) -> dict:
    for attempt in range(retries):
        try:
            r = requests.get(EUROPE_PMC, params=params, timeout=45)
            r.raise_for_status()
            return r.json()
        except requests.RequestException:
            if attempt < retries - 1:
                time.sleep(2 ** attempt)
    return {}


def fetch_europe_pmc_record(pmid: str = "", doi: str = "") -> dict[str, Any]:
    pmid = re.sub(r"\D", "", str(pmid or ""))
    doi = (doi or "").strip()
    if pmid:
        q = f"EXT_ID:{pmid}"
    elif doi:
        q = f"DOI:{doi}"
    else:
        return {}
    data = _epmc_get({"query": q, "format": "json", "resultType": "core", "pageSize": 1})
    hits = (data.get("resultList") or {}).get("result") or []
    return hits[0] if hits else {}


def resolve_accessions_from_publication(
    *,
    pmid: str = "",
    doi: str = "",
    title: str = "",
    abstract: str = "",
) -> dict[str, list[str]]:
    """Извлечь ID репозиториев из публикации (abstract + data availability)."""
    record = fetch_europe_pmc_record(pmid=pmid, doi=doi) if (pmid or doi) else {}
    parts = [
        title,
        abstract,
        record.get("title") or "",
        record.get("abstractText") or "",
    ]
    for key in ("dataAvailability", "dataAvailabilityStatement", "datasetLinks"):
        val = record.get(key)
        if val:
            parts.append(str(val))
    blob = " ".join(parts)
    ids = extract_ids_from_text(blob)
    return {k: v for k, v in ids.items() if k in ("PXD", "PDC", "MSV", "IPX")}


def enrich_pride_accession(accession: str) -> dict[str, Any] | None:
    acc = accession.strip().upper()
    if not acc.startswith("PXD"):
        return None
    try:
        r = requests.get(f"{PRIDE_API}/projects/{acc}", timeout=30)
        if r.status_code != 200:
            return None
        p = r.json()
        from atlas_agent.sources.pride import project_to_record

        return project_to_record(p, source="pride_resolve")
    except requests.RequestException:
        return None


def publications_to_projects(
    pubs: list[dict[str, Any]],
    *,
    known_accessions: set[str],
    max_resolve: int = 40,
) -> list[dict[str, Any]]:
    """PMID/DOI → PXD/PDC через Europe PMC, затем обогащение PRIDE."""
    known = {a.upper() for a in known_accessions}
    seen: set[str] = set()
    out: list[dict[str, Any]] = []

    for pub in pubs[:max_resolve]:
        ids = resolve_accessions_from_publication(
            pmid=str(pub.get("pmid") or ""),
            doi=str(pub.get("doi") or ""),
            title=str(pub.get("title") or ""),
            abstract=str(pub.get("abstract") or pub.get("abstract_snippet") or ""),
        )
        for kind in ("PXD", "PDC", "MSV", "IPX"):
            for acc in ids.get(kind) or []:
                acc = acc.upper()
                if acc in known or acc in seen:
                    continue
                seen.add(acc)
                if acc.startswith("PXD"):
                    rec = enrich_pride_accession(acc)
                    if rec and rec.get("human") is not False:
                        rec["source"] = "pride_via_publication"
                        rec["pmid"] = pub.get("pmid", "")
                        rec["doi"] = pub.get("doi", "")
                        out.append(rec)
                else:
                    out.append(
                        {
                            "accession": acc,
                            "title": (pub.get("title") or "")[:300],
                            "pmid": pub.get("pmid", ""),
                            "doi": pub.get("doi", ""),
                            "source": f"{kind.lower()}_via_publication",
                            "url": _url_for_accession(acc),
                            "tmt_detected": True,
                            "human": True,
                        }
                    )
    return out


def _url_for_accession(acc: str) -> str:
    if acc.startswith("PDC"):
        return f"https://proteomic.datacommons.cancer.gov/pdc/study/{acc}"
    if acc.startswith("PXD"):
        return f"https://www.ebi.ac.uk/pride/archive/projects/{acc}"
    if acc.startswith("MSV"):
        return f"https://massive.ucsd.edu/ProteoSAFe/dataset.jsp?task={acc}"
    return ""
