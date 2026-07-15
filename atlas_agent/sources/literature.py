from __future__ import annotations

import re

import requests

EUROPE_PMC = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"


def fetch_abstract(pmid: str) -> dict:
    pmid = re.sub(r"\D", "", str(pmid or ""))
    if not pmid:
        return {"pmid": "", "title": "", "abstract": "", "found": False}
    params = {"query": f"EXT_ID:{pmid}", "format": "json", "pageSize": 1}
    r = requests.get(EUROPE_PMC, params=params, timeout=25)
    r.raise_for_status()
    hits = (r.json().get("resultList") or {}).get("result") or []
    if not hits:
        return {"pmid": pmid, "title": "", "abstract": "", "found": False}
    h = hits[0]
    return {
        "pmid": pmid,
        "title": h.get("title") or "",
        "abstract": h.get("abstractText") or "",
        "year": str(h.get("pubYear") or h.get("firstPublicationDate") or "")[:4],
        "journal": h.get("journalTitle") or "",
        "found": True,
    }


def text_mentions_normalization(text: str, strategy: str) -> dict:
    """Простая эвристика: есть ли слова из таблицы в статье/описании PRIDE."""
    blob = (text or "").lower()
    strat = (strategy or "").lower()
    if not strat or strat in ("not specified", "—", "-", "n/a"):
        return {"status": "unknown", "hits": [], "note": "В таблице нормализация не указана"}

    tokens = []
    for part in re.split(r"[,;/]| per | and ", strat):
        part = part.strip()
        if len(part) > 4:
            tokens.append(part)

    hits = []
    for t in tokens[:8]:
        key = t[:40]
        if key in blob:
            hits.append(key)

    kw = [
        "median normalization",
        "reporter ion",
        "summed intensity",
        "reference channel",
        "global median",
        "vsn",
        "quantile",
        "tmt",
        "isobaric",
    ]
    for k in kw:
        if k in blob and k not in hits:
            hits.append(k)

    if hits:
        return {"status": "supported", "hits": hits, "note": "Термины совпадают с текстом"}
    return {
        "status": "not_found",
        "hits": [],
        "note": "В статье/описании не найдены явные формулировки из таблицы",
    }
