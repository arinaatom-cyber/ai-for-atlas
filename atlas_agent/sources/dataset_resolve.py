from __future__ import annotations

import re
import time
from typing import Any

import requests

from atlas_agent.discovery.filters import extract_ids_from_text
from atlas_agent.discovery.evaluation.llm_evaluator import LLMEvaluatorRegistry
from atlas_agent.discovery.evaluation.schemas import ModelTrustLevel
from atlas_agent.discovery.evaluation.thresholds import LITERATURE_SEMANTIC_MIN
from atlas_agent.discovery.fit_rules import is_non_study_literature
from atlas_agent.discovery.literature_search import publication_has_repository_id
from atlas_agent.discovery.sample_material_qc import assess_sample_material
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
    return publication_has_repository_id(pub)


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
    known = {a.upper() for a in known_accessions}
    seen: set[str] = set()
    out: list[dict[str, Any]] = []

    for pub in pubs[: max_resolve * 3]:
        if len(out) >= max_resolve:
            break
        if _pub_has_accession(pub):
            continue
        fit, score = _atlas_fit(pub)
        if fit == "no":
            continue
        if fit == "maybe" and score and score < min_score:
            continue
        if fit == "yes" and score and score < min_score:
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


def _literature_material_specified(pub: dict[str, Any], title: str, abstract: str) -> bool:
    ai = pub.get("abstract_ai") or {}
    material = str(ai.get("material") or "").strip().lower()
    if material in ("plasma", "serum", "blood", "organoid", "pdx"):
        return False
    if ai.get("material_suitable") is False:
        return False
    if material and material not in ("unclear", "", "other"):
        return True
    blob = " ".join(
        [
            title,
            abstract,
            str(pub.get("abstract_snippet") or ""),
            str(ai.get("summary_en") or ""),
            str(ai.get("summary_ru") or ""),
        ]
    )
    mq = assess_sample_material({**pub, "human": True}, blob)
    return mq.get("qc_status") in ("candidate", "requires_manual_check")


def literature_semantic_candidates(
    pubs: list[dict[str, Any]],
    *,
    known_accessions: set[str],
    min_score: float = LITERATURE_SEMANTIC_MIN,
) -> list[dict[str, Any]]:
    known = {a.upper() for a in known_accessions}
    known_pmids = {re.sub(r"\D", "", x) for x in known if re.sub(r"\D", "", x)}
    registry = LLMEvaluatorRegistry()
    out: list[dict[str, Any]] = []

    for pub in pubs:
        if _pub_has_accession(pub):
            continue
        title = str(pub.get("title") or "")
        abstract = str(pub.get("abstract") or "")
        if is_non_study_literature(title, abstract):
            continue
        if not _literature_material_specified(pub, title, abstract):
            continue

        fit, score = _atlas_fit(pub)
        if fit not in ("yes", "maybe"):
            continue

        reader = str(pub.get("abstract_reader") or "")
        trust = registry.trust_for_engine(reader)
        effective_min = min_score
        if trust == ModelTrustLevel.LOW:
            effective_min = max(min_score, 0.62)
            if fit == "yes" and str((pub.get("abstract_ai") or {}).get("regex_fit") or "") != "yes":
                fit = "maybe"
        elif trust == ModelTrustLevel.MEDIUM:
            effective_min = max(min_score, 0.55)
            if fit == "yes" and str((pub.get("abstract_ai") or {}).get("regex_fit") or "") == "no":
                fit = "maybe"

        if score and score < effective_min:
            continue
        if fit == "maybe" and (not score or score < effective_min - 0.05):
            continue

        pmid = re.sub(r"\D", "", str(pub.get("pmid") or ""))
        if pmid and pmid in known_pmids:
            continue

        ai = pub.get("abstract_ai") or {}
        rel = pub.get("literature_relevance")
        out.append(
            {
                "pmid": pmid,
                "doi": pub.get("doi", ""),
                "title": title[:400],
                "abstract_snippet": abstract[:500],
                "source": "literature_semantic_candidate",
                "atlas_fit": fit,
                "atlas_fit_score": score,
                "literature_relevance": rel,
                "abstract_ai": ai,
                "abstract_reader": reader,
                "pride_search_terms": ai.get("pride_search_terms", ""),
                "summary_ru": ai.get("summary_ru", ""),
                "verdict": "requires_manual_check",
                "filter_reasons": [
                    "Semantically similar to TMT ATLAS — verify manually in PRIDE/PDC "
                    "(accession not extracted from abstract)"
                ],
                "human": bool(ai.get("human_suitable")),
                "tmt_detected": str(ai.get("tmt") or "") not in ("none", "unclear", ""),
                "recommendation": "literature_manual_resolve",
            }
        )
    out.sort(key=lambda x: float(x.get("atlas_fit_score") or 0), reverse=True)
    return out


def _url_for_accession(acc: str) -> str:
    acc = (acc or "").strip().upper()
    if acc.startswith("PDC"):
        return f"https://proteomic.datacommons.cancer.gov/pdc/study/{acc}"
    if acc.startswith("PXD"):
        return f"https://www.ebi.ac.uk/pride/archive/projects/{acc}"
    if acc.startswith("MSV"):
        return f"https://massive.ucsd.edu/ProteoSAFe/dataset.jsp?accession={acc}"
    if acc.startswith("IPX"):
        return f"https://www.iprox.cn/page/project.html?id={acc}"
    return ""
