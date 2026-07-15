"""Поиск крупных когортных статей по протеомике / мульти-омике (Europe PMC + text mining)."""
from __future__ import annotations

import re
from typing import Any

from atlas_agent.revisor.literature_watch import search_new_publications

PATIENT_N_PATTERNS = [
    re.compile(r"\b(\d{1,5})\s+patients?\b", re.I),
    re.compile(r"\b(\d{1,5})\s+participants?\b", re.I),
    re.compile(r"\b(\d{1,5})\s+subjects?\b", re.I),
    re.compile(r"\b(\d{1,5})\s+individuals?\b", re.I),
    re.compile(r"\bcohort\s+of\s+(\d{1,5})\b", re.I),
    re.compile(r"\b(?:n|N)\s*[=:]\s*(\d{1,5})\b"),
    re.compile(r"\bincluded\s+(\d{1,5})\b", re.I),
    re.compile(r"\bcomprising\s+(\d{1,5})\b", re.I),
    re.compile(r"\bfrom\s+(\d{1,5})\s+patients?\b", re.I),
    re.compile(r"\btotal\s+of\s+(\d{1,5})\b", re.I),
    re.compile(r"\b(\d{1,5})\s+human\s+(?:samples?|specimens?)\b", re.I),
    re.compile(r"\b(\d{1,5})\s+clinical\s+samples?\b", re.I),
]

OMICS_PATTERNS: dict[str, re.Pattern[str]] = {
    "proteomics": re.compile(r"\bproteom(?:ic|ics|e)\b", re.I),
    "phosphoproteomics": re.compile(r"\bphosphoproteom", re.I),
    "transcriptomics": re.compile(r"\btranscriptom", re.I),
    "genomics": re.compile(r"\bgenom(?:ic|ics)\b", re.I),
    "metabolomics": re.compile(r"\bmetabolom", re.I),
    "lipidomics": re.compile(r"\blipidom", re.I),
    "glycoproteomics": re.compile(r"\bglycoproteom", re.I),
    "multi_omics": re.compile(r"\bmulti[- ]?omics\b|\bintegrative omics\b|\bomics integration\b", re.I),
}

PATIENT_YES = re.compile(
    r"\b(patient|patients|clinical cohort|multicenter|multi-center|participants?|subjects?|"
    r"biopsy|tumor tissue|plasma|serum|cohort)\b",
    re.I,
)
PATIENT_NO = re.compile(
    r"\b(mouse|mice|murine|rat\b|cell[- ]line[- ]only|in vitro only|review|editorial|"
    r"protocol paper|perspective)\b",
    re.I,
)
TMT_HINT = re.compile(r"\b(tmt|isobaric|tandem mass tag|tmtpro)\b", re.I)
LARGE_SCALE = re.compile(
    r"\b(large[- ]scale|deep proteome|clinical proteome|population[- ]scale|"
    r"thousands? of proteins|proteogenomic)\b",
    re.I,
)


def _cohort_pub_queries(year_from: int, year_to: int) -> list[str]:
    yr = f"PUB_YEAR:[{year_from} TO {year_to}]"
    human = "HUMAN"
    return [
        f'(proteomics OR phosphoproteomics) AND (cohort OR patients OR multicenter OR "clinical cohort") AND {human} AND {yr}',
        f'(proteomics AND ("multi-omics" OR multiomics OR transcriptomics OR genomics OR metabolomics)) AND (patients OR cohort) AND {human} AND {yr}',
        f'("large-scale" OR "deep proteome" OR "clinical proteome" OR proteogenomic) AND proteomics AND patients AND {human} AND {yr}',
        f'(TMT OR isobaric OR "tandem mass tag") AND proteomics AND (cohort OR participants OR "n patients") AND {human} AND {yr}',
        f'(proteomics OR phosphoproteomics) AND (biobank OR "thousand" OR nationwide) AND patients AND {human} AND {yr}',
    ]


def extract_patient_count(text: str) -> int | None:
    """Извлечь максимальное правдоподобное N пациентов/участников из текста."""
    if not text:
        return None
    found: list[int] = []
    for pat in PATIENT_N_PATTERNS:
        for m in pat.finditer(text):
            n = int(m.group(1))
            if 5 <= n <= 500_000:
                found.append(n)
    if not found:
        return None
    # Prefer explicit patient/participant counts over stray n=
    best = max(found)
    return best if best >= 5 else None


def detect_omics(text: str) -> list[str]:
    blob = text or ""
    return [k for k, pat in OMICS_PATTERNS.items() if pat.search(blob)]


def assess_patients(text: str, patient_n: int | None) -> str:
    blob = text or ""
    if PATIENT_NO.search(blob) and not PATIENT_YES.search(blob):
        return "no"
    if patient_n and patient_n >= 10:
        return "yes"
    if PATIENT_YES.search(blob):
        return "maybe"
    return "no"


def build_description_ru(item: dict[str, Any]) -> str:
    """Краткое описание для вкладки (без LLM)."""
    parts: list[str] = []
    omics = item.get("omics") or []
    if omics:
        labels = {
            "proteomics": "протеомика",
            "phosphoproteomics": "фосфопротеомика",
            "transcriptomics": "транскриптомика",
            "genomics": "геномика",
            "metabolomics": "метаболомика",
            "lipidomics": "липидомика",
            "glycoproteomics": "гликопротеомика",
            "multi_omics": "мульти-омика",
        }
        parts.append("Омики: " + ", ".join(labels.get(o, o) for o in omics[:5]))
    n = item.get("patient_n")
    if n:
        parts.append(f"Когорта: ~{n} пациентов/участников (из абстракта)")
    elif item.get("has_patients") == "maybe":
        parts.append("Пациенты упомянуты, точное N не извлечено")
    elif item.get("has_patients") == "no":
        parts.append("Пациенты в абстракте не подтверждены")
    if item.get("tmt_detected"):
        parts.append("TMT/isobaric")
    if item.get("large_scale"):
        parts.append("крупномасштабное исследование")
    journal = item.get("journal") or ""
    year = item.get("year") or ""
    if journal or year:
        parts.append(f"{journal} {year}".strip())
    return ". ".join(parts) if parts else "Клиническая протеомика / мульти-омика (Europe PMC)."


def mine_publication(pub: dict[str, Any]) -> dict[str, Any]:
    """Text mining абстракта: N пациентов, омики, наличие пациентов."""
    blob = " ".join(
        str(pub.get(k) or "")
        for k in ("title", "abstract", "data_availability")
    )
    patient_n = extract_patient_count(blob)
    omics = detect_omics(blob)
    has_patients = assess_patients(blob, patient_n)
    out = dict(pub)
    out.update(
        {
            "patient_n": patient_n,
            "omics": omics,
            "has_patients": has_patients,
            "tmt_detected": bool(TMT_HINT.search(blob)),
            "large_scale": bool(LARGE_SCALE.search(blob)),
            "multi_omics": "multi_omics" in omics or len(omics) >= 2,
            "description_ru": "",
            "cohort_score": 0,
        }
    )
    out["description_ru"] = build_description_ru(out)
    out["cohort_score"] = _cohort_score(out)
    return out


def _cohort_score(item: dict[str, Any]) -> int:
    score = 0
    n = item.get("patient_n") or 0
    if n >= 500:
        score += 50
    elif n >= 200:
        score += 40
    elif n >= 100:
        score += 30
    elif n >= 50:
        score += 20
    elif n >= 20:
        score += 10
    elif n > 0:
        score += 5
    if item.get("has_patients") == "yes":
        score += 15
    elif item.get("has_patients") == "maybe":
        score += 5
    if "proteomics" in (item.get("omics") or []):
        score += 10
    if item.get("multi_omics"):
        score += 10
    if item.get("large_scale"):
        score += 8
    if item.get("tmt_detected"):
        score += 5
    return score


def search_cohort_literature(
    *,
    year_from: int = 2023,
    year_to: int = 2026,
    page_size: int = 30,
    min_patients: int = 50,
    min_score: int = 25,
    known_pmids: set[str] | None = None,
    include_without_n: bool = True,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """
    Поиск крупных когортных статей в Europe PMC + text mining абстрактов.
    Возвращает отсортированный список и статистику.
    """
    known = {re.sub(r"\D", "", p) for p in (known_pmids or set()) if p}
    seen: set[str] = set()
    raw: list[dict[str, Any]] = []
    queries = _cohort_pub_queries(year_from, year_to)
    per_q = max(8, page_size // len(queries))

    for q in queries:
        batch = search_new_publications(
            query=q, year_from=year_from, year_to=year_to, page_size=per_q
        )
        for p in batch:
            pmid = re.sub(r"\D", "", str(p.get("pmid") or ""))
            if not pmid or pmid in seen or pmid in known:
                continue
            seen.add(pmid)
            raw.append(p)

    mined = [mine_publication(p) for p in raw]
    kept: list[dict[str, Any]] = []
    for item in mined:
        n = item.get("patient_n") or 0
        score = item.get("cohort_score") or 0
        has_prot = "proteomics" in (item.get("omics") or []) or "phosphoproteomics" in (
            item.get("omics") or []
        )
        if not has_prot:
            continue
        if n >= min_patients:
            kept.append(item)
        elif include_without_n and score >= min_score and item.get("has_patients") in (
            "yes",
            "maybe",
        ):
            if item.get("large_scale") or item.get("multi_omics"):
                kept.append(item)

    kept.sort(key=lambda x: (-(x.get("patient_n") or 0), -(x.get("cohort_score") or 0)))
    kept = kept[:page_size]

    stats = {
        "queries": len(queries),
        "scanned": len(raw),
        "kept": len(kept),
        "with_patient_n": sum(1 for x in kept if x.get("patient_n")),
        "multi_omics": sum(1 for x in kept if x.get("multi_omics")),
        "min_patients_threshold": min_patients,
    }
    return kept, stats
