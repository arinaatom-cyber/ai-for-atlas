"""Резолв PXD/PDC/MSV/IPX из публикаций (Europe PMC, DOI)."""
from __future__ import annotations

import re
import time
from typing import Any

import requests

from atlas_agent.discovery.filters import extract_ids_from_text
from atlas_agent.sources.pride import find_pride_project_by_pmid, search_pride_by_terms

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
        ai = pub.get("abstract_ai") or {}
        ai_acc = ai.get("accessions") or {}
        ids = {k: list(ai_acc.get(k) or []) for k in ("PXD", "PDC", "MSV", "IPX")}
        if not any(ids.values()):
            ids = resolve_accessions_from_publication(
                pmid=str(pub.get("pmid") or ""),
                doi=str(pub.get("doi") or ""),
                title=str(pub.get("title") or ""),
                abstract=str(pub.get("abstract") or pub.get("abstract_snippet") or ""),
            )
        else:
            # дополнить из Europe PMC data availability
            extra = resolve_accessions_from_publication(
                pmid=str(pub.get("pmid") or ""),
                doi=str(pub.get("doi") or ""),
                title="",
                abstract=str(pub.get("data_availability") or ""),
            )
            for k in ("PXD", "PDC", "MSV", "IPX"):
                ids[k] = sorted(set((ids.get(k) or []) + (extra.get(k) or [])))
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
                        rec["abstract_ai"] = pub.get("abstract_ai")
                        rec["abstract_reader"] = pub.get("abstract_reader")
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
                            "abstract_ai": pub.get("abstract_ai"),
                            "abstract_reader": pub.get("abstract_reader"),
                        }
                    )
    return out


def _pub_has_accession(pub: dict[str, Any]) -> bool:
    """Семантический режим: абстракты без номеров проекта."""
    return False


def _atlas_fit(pub: dict[str, Any]) -> tuple[str, float]:
    ai = pub.get("abstract_ai") or {}
    fit = str(ai.get("atlas_fit") or pub.get("atlas_fit") or "no").lower()
    try:
        score = float(ai.get("atlas_fit_score") or pub.get("atlas_fit_score") or 0)
    except (TypeError, ValueError):
        score = 0.0
    return fit, score


def resolve_semantic_publications(
    pubs: list[dict[str, Any]],
    *,
    known_accessions: set[str],
    year_from: int = 2024,
    year_to: int = 2026,
    max_resolve: int = 12,
    min_score: float = 0.5,
) -> list[dict[str, Any]]:
    """
    Абстракт без PXD, но по смыслу как атлас → PRIDE по PMID или pride_search_terms.
    """
    known = {a.upper() for a in known_accessions}
    seen: set[str] = set()
    out: list[dict[str, Any]] = []

    for pub in pubs[: max_resolve * 3]:
        if len(out) >= max_resolve:
            break
        if _pub_has_accession(pub):
            continue
        fit, score = _atlas_fit(pub)
        if fit == "no" or score < min_score:
            continue
        ai = pub.get("abstract_ai") or {}
        pmid = str(pub.get("pmid") or "")
        rec = find_pride_project_by_pmid(pmid, known_accessions=known | seen) if pmid else None
        if not rec:
            terms = str(ai.get("pride_search_terms") or "").strip()
            if not terms:
                title = str(pub.get("title") or "")
                terms = " ".join(re.findall(r"[A-Za-z]{4,}", title)[:6])
            hits = search_pride_by_terms(
                terms,
                year_from=year_from,
                year_to=year_to,
                limit=2,
                known_accessions=known | seen,
            )
            rec = hits[0] if hits else None
        if not rec:
            continue
        acc = (rec.get("accession") or "").upper()
        if not acc or acc in known or acc in seen:
            continue
        seen.add(acc)
        rec = dict(rec)
        rec["source"] = "pride_via_semantic_abstract"
        rec["pmid"] = pmid
        rec["doi"] = pub.get("doi", "")
        rec["abstract_ai"] = ai
        rec["abstract_reader"] = pub.get("abstract_reader")
        rec["atlas_fit"] = fit
        rec["atlas_fit_score"] = score
        rec["semantic_resolve"] = "pmid" if pmid and rec.get("pmid") else "search_terms"
        out.append(rec)
    return out


def literature_semantic_candidates(
    pubs: list[dict[str, Any]],
    *,
    known_accessions: set[str],
    min_score: float = 0.55,
) -> list[dict[str, Any]]:
    """Статьи похожи на атлас, но PXD так и не найден — ручная проверка."""
    known = {a.upper() for a in known_accessions}
    out: list[dict[str, Any]] = []
    for pub in pubs:
        if _pub_has_accession(pub):
            continue
        fit, score = _atlas_fit(pub)
        if fit not in ("yes", "maybe") or score < min_score:
            continue
        pmid = re.sub(r"\D", "", str(pub.get("pmid") or ""))
        if pmid and pmid in known:
            continue
        ai = pub.get("abstract_ai") or {}
        out.append(
            {
                "pmid": pmid,
                "doi": pub.get("doi", ""),
                "title": (pub.get("title") or "")[:400],
                "abstract_snippet": (pub.get("abstract") or "")[:500],
                "source": "literature_semantic_candidate",
                "atlas_fit": fit,
                "atlas_fit_score": score,
                "abstract_ai": ai,
                "abstract_reader": pub.get("abstract_reader"),
                "pride_search_terms": ai.get("pride_search_terms", ""),
                "summary_ru": ai.get("summary_ru", ""),
                "verdict": "requires_manual_check",
                "filter_reasons": [
                    "По смыслу похоже на TMT ATLAS — проверить вручную (PRIDE/PDC), номер в абстракте не ищем"
                ],
                "human": ai.get("human_suitable", True),
                "tmt_detected": str(ai.get("tmt") or "") not in ("none", "unclear", ""),
                "recommendation": "literature_manual_resolve",
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
