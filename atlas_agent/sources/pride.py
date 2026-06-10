from __future__ import annotations

import re
import time
from typing import Any

import requests

PRIDE_API = "https://www.ebi.ac.uk/pride/ws/archive/v3"
PRIDE_API_V2 = "https://www.ebi.ac.uk/pride/ws/archive/v2"
TMT_HINTS = ("tmt", "tandem mass tag", "isobaric", "itraq")


def fetch_project(accession: str) -> dict | None:
    acc = accession.strip().upper()
    if not acc.startswith("PXD"):
        return None
    url = f"{PRIDE_API_V2}/projects/{acc}"
    r = requests.get(url, timeout=30)
    if r.status_code == 404:
        return None
    r.raise_for_status()
    return r.json()


def fetch_projects_json(accessions: list[str]) -> list[dict]:
    """Полная карточка PRIDE по JSON для каждого PXD."""
    out = []
    for acc in accessions:
        p = fetch_project(acc)
        if p:
            out.append(p)
    return out


def _parse_project_list(data) -> list[dict]:
    if isinstance(data, list):
        return data
    return data.get("_embedded", {}).get("projects", data.get("content", []))


def _project_date(p: dict) -> str:
    return (p.get("submissionDate") or p.get("publicationDate") or "")[:10]


def _is_tmt_project(p: dict) -> bool:
    blob = " ".join(
        str(p.get(k, "") or "")
        for k in (
            "title",
            "projectDescription",
            "keywords",
            "quantificationMethods",
            "sampleProcessingProtocol",
            "dataProcessingProtocol",
        )
    ).lower()
    if "label-free" in blob or "label free" in blob:
        if not any(h in blob for h in ("tmt", "tandem mass tag", "isobaric")):
            return False
    qm = p.get("quantificationMethods") or []
    qm_text = " ".join(str(x) for x in qm).lower() if isinstance(qm, list) else str(qm).lower()
    if qm_text and ("tmt" in qm_text or "isobaric" in qm_text):
        return True
    return any(h in blob for h in TMT_HINTS)


def _is_human(p: dict) -> bool:
    title_desc = f"{p.get('title', '')} {p.get('projectDescription', '')}".lower()
    exclusive_non_human = (
        "chlamydomonas", "porcine", "pig skin", "mouse only", "mice only",
        "murine", "rat liver", "salmonella", "escherichia coli", "bacterial",
        "maize", "arabidopsis", "yeast", "unicellular protist",
    )
    if re.search(r"\b(mouse|mice|murine|rat\b|porcine)\b", title_desc):
        if not re.search(r"\b(patient|patients|clinical|donor|cohort|subjects)\b", title_desc):
            return False
    if any(x in title_desc for x in exclusive_non_human):
        if "human" not in title_desc and "homo" not in title_desc:
            return False
    orgs = p.get("organisms") or []
    org_text = " ".join(_organism_names(p) or [str(o) for o in orgs]).lower()
    if org_text:
        if "homo" in org_text or "human" in org_text:
            return True
        non_human = ("mouse", "mus musculus", "rat", "bacteria", "salmonella", "escherichia", "maize", "plant", "porcine")
        if any(n in org_text for n in non_human):
            return False
    if "human" in title_desc or "patient" in title_desc or "clinical" in title_desc:
        return True
    if any(x in title_desc for x in ("mouse", "mice", "murine", "rat ", "porcine", "chlamydomonas")):
        return False
    return not orgs


def _organism_names(p: dict) -> list[str]:
    orgs = p.get("organisms") or []
    names = []
    for o in orgs:
        if isinstance(o, dict):
            names.append(str(o.get("name") or ""))
        else:
            names.append(str(o))
    return names


def project_to_record(p: dict, *, source: str = "pride_api") -> dict[str, Any]:
    """Нормализованная запись кандидата из JSON PRIDE."""
    acc = (p.get("accession") or "").upper()
    refs = p.get("references") or []
    pmid = ""
    doi = p.get("doi") or ""
    for ref in refs:
        if isinstance(ref, dict):
            if ref.get("pubmedID"):
                pmid = str(ref["pubmedID"])
                break
            if ref.get("referenceLine") and "PMID" in str(ref["referenceLine"]):
                m = re.search(r"\d{5,9}", str(ref["referenceLine"]))
                if m:
                    pmid = m.group(0)
    qm = p.get("quantificationMethods") or []
    desc = str(p.get("projectDescription") or "")
    return {
        "accession": acc,
        "title": (p.get("title") or "")[:500],
        "description": desc[:800],
        "submission_date": _project_date(p),
        "publication_date": (p.get("publicationDate") or "")[:10],
        "organisms": _organism_names(p) or p.get("organisms") or [],
        "instruments": (p.get("instruments") or [])[:5],
        "quantification_methods": qm,
        "pmid": pmid,
        "doi": doi,
        "url": f"https://www.ebi.ac.uk/pride/archive/projects/{acc}",
        "tmt_detected": _is_tmt_project(p),
        "human": _is_human(p),
        "source": source,
    }


def _parse_search_results(data) -> list[dict]:
    if isinstance(data, list):
        return data
    return data.get("content") or data.get("_embedded", {}).get("projects") or []


def _fetch_project_detail(accession: str) -> dict | None:
    for base in (PRIDE_API, PRIDE_API_V2):
        try:
            r = requests.get(f"{base}/projects/{accession}", timeout=30)
            if r.status_code == 200:
                return r.json()
        except requests.RequestException:
            continue
    return None


def search_pride_json(
    keywords: list[str] | None = None,
    *,
    year_from: int = 2026,
    year_to: int = 2026,
    page_size: int = 100,
    max_pages: int = 15,
    exclude_accessions: set[str] | None = None,
    profile_keywords: list[str] | None = None,
) -> list[dict]:
    """
    Профессиональный поиск PRIDE v3 /search/projects (сортировка по дате submission).
    Несколько keyword-запросов + фильтр human/TMT + исключение известных PXD.
    """
    kws = list(keywords or ["TMT", "tandem mass tag", "isobaric"])
    if profile_keywords:
        for pk in profile_keywords[:6]:
            if pk.lower() not in {x.lower() for x in kws} and len(pk) > 3:
                kws.append(pk)
    exclude = {a.upper() for a in (exclude_accessions or set())}
    cutoff_lo = f"{year_from}-01-01"
    cutoff_hi = f"{year_to}-12-31"
    seen: set[str] = set()
    filtered: list[dict] = []

    for kw in kws[:8]:
        for page in range(max_pages):
            params = {
                "keyword": kw,
                "pageSize": min(page_size, 100),
                "page": page,
                "sortDirection": "DESC",
                "sortFields": "submissionDate",
            }
            try:
                r = requests.get(f"{PRIDE_API}/search/projects", params=params, timeout=60)
                r.raise_for_status()
            except requests.RequestException:
                break
            batch = _parse_search_results(r.json())
            if not batch:
                break
            for summary in batch:
                acc = (summary.get("accession") or "").upper()
                if not acc or acc in seen or acc in exclude:
                    continue
                seen.add(acc)
                d = _project_date(summary)
                if d and (d < cutoff_lo or d > cutoff_hi):
                    continue
                detail = summary
                if not summary.get("projectDescription") or not summary.get("organisms"):
                    full = _fetch_project_detail(acc)
                    if full:
                        detail = full
                if not _is_tmt_project(detail):
                    continue
                if not _is_human(detail):
                    continue
                filtered.append(project_to_record(detail, source="pride_search_v3"))
                if len(filtered) >= page_size:
                    return filtered
            if len(batch) < params["pageSize"]:
                break
            time.sleep(0.2)
    return filtered


def search_recent_tmt(keywords: list[str], page_size: int = 40) -> list[dict]:
    q = " OR ".join(f'"{k}"' for k in keywords[:3])
    params = {
        "query": q,
        "pageSize": min(page_size, 100),
        "page": 0,
        "sortDirection": "DESC",
        "sortFields": "submissionDate",
    }
    r = requests.get(f"{PRIDE_API}/projects", params=params, timeout=45)
    r.raise_for_status()
    return _parse_project_list(r.json())


def search_human_tmt_projects(
    keywords: list[str] | None = None,
    *,
    page_size: int = 40,
    year_from: int = 2020,
) -> list[dict]:
    """Human + TMT с year_from (для обратной совместимости)."""
    raw = search_pride_json(
        keywords=keywords,
        year_from=year_from,
        year_to=2030,
        page_size=page_size,
        max_pages=12,
    )
    return [
        {
            "accession": r["accession"],
            "title": r["title"],
            "submissionDate": r["submission_date"],
            "organisms": r["organisms"],
        }
        for r in raw
    ]
