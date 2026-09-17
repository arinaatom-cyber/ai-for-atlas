"""Professional Europe PMC literature search for TMT ATLAS."""
from __future__ import annotations

import re
from typing import Any

from atlas_agent.discovery.evaluation.exclusion_engine import ExclusionEngine
from atlas_agent.discovery.evaluation.heuristics import has_hard_exclusion, scan_literature_text
from atlas_agent.discovery.filters import extract_ids_from_text
from atlas_agent.revisor.literature_watch import search_new_publications

# Patient cohort studies — exclude methods/reviews at query level (Europe PMC syntax).
_NEGATIVE = (
    'NOT (review OR editorial OR protocol OR "narrative review" OR perspective OR '
    'benchmark OR tutorial OR integrator OR workflow OR toolbox OR "case study highlighting" OR '
    'phosphoproteom* OR "single-cell" OR microfluidic OR degradomics OR "multi omics integration")'
)

_TMT = '(TMT OR "tandem mass tag" OR isobaric OR TMTpro OR "TMT 10" OR "TMT 11")'
_HUMAN = "HUMAN"
_CLINICAL = "(patient OR patients OR clinical OR cohort OR biopsy OR FFPE OR tissue OR \"cell line\" OR tumor OR tumour OR cancer)"


def atlas_literature_queries(year_from: int, year_to: int) -> list[str]:
    """Targeted queries — patient TMT proteomics, not software papers."""
    yr = f"PUB_YEAR:[{year_from} TO {year_to}]"
    return [
        f"{_TMT} AND proteomics AND {_CLINICAL} AND {_HUMAN} AND {yr} {_NEGATIVE}",
        f"{_TMT} AND (proteome OR \"protein quantification\") AND (tumor OR cancer OR carcinoma) AND {_HUMAN} AND {yr} {_NEGATIVE}",
        f"{_TMT} AND quantitative proteomics AND (tissue OR \"cell line\" OR FFPE OR biopsy) AND {_HUMAN} AND {yr} {_NEGATIVE}",
        f"(PRIDE OR ProteomeXchange OR \"data availability\") AND {_TMT} AND proteomics AND {_HUMAN} AND {yr}",
    ]


def _blob(pub: dict[str, Any]) -> str:
    return " ".join(
        str(pub.get(k) or "")
        for k in ("title", "abstract", "data_availability", "journal")
    )


def publication_has_repository_id(pub: dict[str, Any]) -> bool:
    ids = extract_ids_from_text(_blob(pub))
    mentioned = pub.get("accessions_mentioned") or pub.get("pxd_mentioned") or []
    if mentioned:
        return True
    return any(ids.get(k) for k in ("PXD", "PDC", "MSV", "IPX"))


def score_publication_relevance(pub: dict[str, Any]) -> float:
    """Heuristic 0..1 — rank before LLM (regex only, fast)."""
    blob = _blob(pub).lower()
    score = 0.0
    if re.search(r"\b(tmt|tandem mass tag|isobaric|tmtpro)\b", blob):
        score += 0.25
    if re.search(r"\b(patient|patients|clinical|cohort|donor)\b", blob):
        score += 0.2
    if re.search(r"\b(tumor|tumou?r|cancer|carcinoma|biopsy|ffpe|tissue|cell\s+line)\b", blob):
        score += 0.2
    if re.search(r"\b(proteome|protein[- ]level|protein quant|global proteom)\b", blob):
        score += 0.15
    if publication_has_repository_id(pub):
        score += 0.25
    if re.search(r"\b(data availability|proteomexchange|pride)\b", blob):
        score += 0.1
    if re.search(r"\b(review|editorial|integrator|workflow|phosphoproteom|single-cell)\b", blob):
        score -= 0.4
    if re.search(
        r"\b(spectral cluster|search-assisted|building consensus|consensus spectra|"
        r"computational platform|data reanalysis|benchmark)\b",
        blob,
    ):
        score -= 0.35
    if not re.search(r"\b(patient|patients|clinical|cohort|donor|biopsy|ffpe|cell\s+line|tissue)\b", blob):
        score = min(score, 0.45)
    if re.search(r"\b(mouse|mice|murine|rat\b|chicken|gallus)\b", blob):
        score -= 0.5
    return max(0.0, min(1.0, score))


def prefilter_publication(
    pub: dict[str, Any],
    *,
    engine: ExclusionEngine | None = None,
    min_relevance: float = 0.25,
) -> tuple[bool, str]:
    """
    Return (keep, reason).
    Hard exclusions → drop before LLM.
    Low relevance without repo ID → drop.
    """
    title = str(pub.get("title") or "")
    abstract = str(pub.get("abstract") or "")
    if not title.strip():
        return False, "empty title"

    chain = scan_literature_text(title, abstract, engine=engine)
    if has_hard_exclusion(chain):
        detail = chain[0].detail or chain[0].reason.value if chain[0].reason else "excluded"
        return False, f"exclusion: {detail}"

    rel = score_publication_relevance(pub)
    pub["literature_relevance"] = round(rel, 3)
    blob_l = _blob(pub).lower()
    if rel <= 0.45 and re.search(
        r"\b(spectral cluster|search-assisted|building consensus|computational platform|"
        r"data reanalysis|benchmark|integrator)\b",
        blob_l,
    ):
        return False, "methods / pipeline paper"
    if rel < min_relevance and not publication_has_repository_id(pub):
        return False, f"low relevance ({rel:.2f})"
    return True, "ok"


def search_atlas_literature(
    *,
    year_from: int,
    year_to: int,
    page_size: int = 40,
    min_relevance: float = 0.25,
    engine: ExclusionEngine | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """
    Multi-query Europe PMC search → dedupe → prefilter → rank.
    Returns publications ready for LLM enrichment (top page_size after rank).
    """
    seen_pmids: set[str] = set()
    raw: list[dict[str, Any]] = []
    queries = atlas_literature_queries(year_from, year_to)
    per_q = max(12, page_size // max(len(queries), 1))

    for q in queries:
        batch = search_new_publications(
            query=q, year_from=year_from, year_to=year_to, page_size=per_q
        )
        for pub in batch:
            pmid = re.sub(r"\D", "", str(pub.get("pmid") or ""))
            if pmid and pmid in seen_pmids:
                continue
            if pmid:
                seen_pmids.add(pmid)
            raw.append(pub)

    kept: list[dict[str, Any]] = []
    dropped = 0
    drop_reasons: dict[str, int] = {}
    for pub in raw:
        ok, reason = prefilter_publication(pub, engine=engine, min_relevance=min_relevance)
        if ok:
            kept.append(pub)
        else:
            dropped += 1
            key = reason.split(":", 1)[0].strip()
            drop_reasons[key] = drop_reasons.get(key, 0) + 1

    kept.sort(key=lambda p: score_publication_relevance(p), reverse=True)
    trimmed = kept[:page_size]

    stats = {
        "queries": len(queries),
        "raw_hits": len(raw),
        "prefilter_kept": len(kept),
        "prefilter_dropped": dropped,
        "drop_reasons": drop_reasons,
        "returned": len(trimmed),
        "with_repository_id": sum(1 for p in trimmed if publication_has_repository_id(p)),
        "preprints": sum(1 for p in trimmed if p.get("is_preprint")),
        "peer_reviewed": sum(1 for p in trimmed if p.get("publication_status") == "journal"),
    }
    return trimmed, stats
