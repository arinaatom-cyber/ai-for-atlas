from __future__ import annotations

import re
import time
import xml.etree.ElementTree as ET
from typing import Any

import requests

from src.utils import load_config

PRIDE_V3 = "https://www.ebi.ac.uk/pride/ws/archive/v3"
PRIDE_V2 = "https://www.ebi.ac.uk/pride/ws/archive/v2"
PDC_GRAPHQL = "https://pdc.cancer.gov/graphql"
MASSIVE_API = "https://massive.ucsd.edu/ProteoSAFe/datasets_json.jsp"
OMICSDI_API = "https://www.omicsdi.org/ws/dataset/search"
IPROX_SEARCH = "https://www.iprox.cn/proteomics/search"
EUROPE_PMC = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
PUBMED_EUTILS = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"

RECORD_KEYS = (
    "database", "project_id", "pmid", "doi", "title", "url",
    "description", "organism", "method", "sample_type", "publication",
)


def _blank(database: str) -> dict[str, str]:
    return {k: "" for k in RECORD_KEYS} | {"database": database}


def _request_json(url: str, *, method: str = "GET", **kwargs) -> Any:
    kwargs.setdefault("timeout", 45)
    for attempt in range(3):
        try:
            if method == "POST":
                r = requests.post(url, **kwargs)
            else:
                r = requests.get(url, **kwargs)
            if r.status_code == 200:
                return r.json()
            if r.status_code in (429, 503) and attempt < 2:
                time.sleep(2 ** attempt)
                continue
            return None
        except requests.RequestException:
            if attempt < 2:
                time.sleep(2 ** attempt)
    return None


def _cfg_search() -> dict[str, Any]:
    cfg = load_config()
    return cfg.get("search") or {}


def search_pride(keywords: list[str] | None = None, max_results: int | None = None) -> list[dict]:
    sc = _cfg_search()
    keywords = keywords or sc.get("keywords") or ["TMT"]
    max_results = max_results or int(sc.get("pride_max") or 50)
    out: list[dict] = []
    seen: set[str] = set()

    for kw in keywords[:4]:
        data = _request_json(
            f"{PRIDE_V3}/search/projects",
            params={"keyword": kw, "pageSize": min(max_results, 100), "page": 0},
        )
        if not data:
            continue
        projects = data if isinstance(data, list) else data.get("content", data.get("_embedded", {}).get("projects", []))
        for p in projects or []:
            acc = (p.get("accession") or "").upper()
            if not acc or acc in seen:
                continue
            seen.add(acc)
            orgs = p.get("organisms") or []
            org_names = []
            for o in orgs:
                org_names.append(o.get("name", o) if isinstance(o, dict) else str(o))
            rec = _blank("PRIDE")
            rec.update({
                "project_id": acc,
                "title": p.get("title") or "",
                "description": p.get("projectDescription") or "",
                "organism": "; ".join(org_names),
                "method": " ".join(str(x) for x in (p.get("quantificationMethods") or [])),
                "url": f"https://www.ebi.ac.uk/pride/archive/projects/{acc}",
                "publication": " ".join(
                    str(p.get(k, "")) for k in ("submitters", "labPIs")
                ),
            })
            out.append(rec)
        if len(out) >= max_results:
            break
    return out[:max_results]


def search_pdc(max_results: int | None = None) -> list[dict]:
    sc = _cfg_search()
    max_results = max_results or int(sc.get("pdc_max") or 80)
    q = """query {
      uiStudySummary {
        pdc_study_id
        submitter_id_name
        experiment_type
        program_name
        project_name
        disease_type
        analytical_fraction
        primary_site
      }
    }"""
    try:
        r = requests.post(PDC_GRAPHQL, json={"query": q}, timeout=60)
        body = r.json() if r.status_code == 200 else None
    except requests.RequestException:
        body = None
    if not body:
        return []
    rows = body.get("data", {}).get("uiStudySummary") or []
    out: list[dict] = []
    for s in rows:
        exp = (s.get("experiment_type") or "").lower()
        if "tmt" not in exp and "isobaric" not in exp:
            continue
        acc = (s.get("pdc_study_id") or "").upper()
        if not acc:
            continue
        title = " — ".join(
            x for x in (
                s.get("submitter_id_name"),
                s.get("project_name"),
                s.get("program_name"),
            ) if x
        )
        rec = _blank("PDC")
        rec.update({
            "project_id": acc,
            "title": title or f"PDC {acc}",
            "description": f"{s.get('disease_type', '')} · {s.get('analytical_fraction', '')}".strip(" ·"),
            "organism": "Homo sapiens",
            "method": s.get("experiment_type") or "",
            "sample_type": s.get("primary_site") or "",
            "url": f"https://proteomic.datacommons.cancer.gov/pdc/study/{acc}",
            "publication": s.get("program_name") or "",
        })
        out.append(rec)
        if len(out) >= max_results:
            break
    return out


def search_massive(keywords: list[str] | None = None, max_results: int | None = None) -> list[dict]:
    sc = _cfg_search()
    keywords = keywords or sc.get("keywords") or ["TMT"]
    max_results = max_results or int(sc.get("massive_max") or 30)
    out: list[dict] = []
    seen: set[str] = set()

    for kw in keywords[:2]:
        data = _request_json(MASSIVE_API, params={"task": "search", "query": kw})
        if not data:
            continue
        datasets = data if isinstance(data, list) else data.get("datasets", [])
        for d in datasets or []:
            acc = (d.get("accession") or d.get("dataset") or "").upper()
            if not acc.startswith("MSV") or acc in seen:
                continue
            seen.add(acc)
            rec = _blank("MassIVE")
            rec.update({
                "project_id": acc,
                "title": d.get("title") or d.get("name") or "",
                "description": d.get("description") or "",
                "url": f"https://massive.ucsd.edu/ProteoSAFe/dataset.jsp?task={acc}",
            })
            out.append(rec)
        if len(out) >= max_results:
            break
    return out[:max_results]


def search_iprox(keywords: list[str] | None = None, max_results: int | None = None) -> list[dict]:
    sc = _cfg_search()
    keywords = keywords or sc.get("keywords") or ["TMT"]
    max_results = max_results or int(sc.get("iprox_max") or 30)
    out: list[dict] = []
    seen: set[str] = set()

    for kw in keywords[:2]:
        data = _request_json(
            IPROX_SEARCH,
            params={"q": kw, "pageSize": max_results},
            headers={"Accept": "application/json"},
        )
        if not data:
            continue
        items = data if isinstance(data, list) else data.get("list", data.get("data", []))
        for item in items or []:
            acc = (item.get("projectId") or item.get("accession") or "").upper()
            if not acc.startswith("IPX") or acc in seen:
                continue
            seen.add(acc)
            rec = _blank("iProX")
            rec.update({
                "project_id": acc,
                "title": item.get("title") or "",
                "description": item.get("summary") or item.get("description") or "",
                "url": item.get("projectUrl") or f"https://www.iprox.cn/page/project.html?id={acc}",
            })
            out.append(rec)
    return out[:max_results]


def search_omicsdi(keywords: list[str] | None = None, max_results: int | None = None) -> list[dict]:
    sc = _cfg_search()
    keywords = keywords or sc.get("keywords") or ["TMT proteomics"]
    max_results = max_results or int(sc.get("omicsdi_max") or 30)
    out: list[dict] = []
    seen: set[str] = set()

    for kw in keywords[:2]:
        data = _request_json(
            OMICSDI_API,
            params={"query": kw, "size": max_results, "start": 0},
        )
        if not data:
            continue
        for ds in (data.get("datasets") or []):
            acc = (ds.get("id") or ds.get("accession") or "").upper()
            source = (ds.get("source") or ds.get("database") or "").upper()
            pid = acc
            if source and not acc.startswith(("PXD", "PDC", "MSV", "IPX")):
                pid = f"{source}:{acc}"
            if pid in seen:
                continue
            seen.add(pid)
            rec = _blank("OmicsDI")
            rec.update({
                "project_id": pid,
                "title": ds.get("title") or ds.get("name") or "",
                "description": ds.get("description") or "",
                "doi": ds.get("doi") or "",
                "url": ds.get("fullDatasetLink") or ds.get("file") or "",
            })
            out.append(rec)
    return out[:max_results]


def search_pubmed(query: str | None = None, max_results: int | None = None) -> list[dict]:
    sc = _cfg_search()
    max_results = max_results or int(sc.get("pubmed_max") or 25)
    q = query or '("tandem mass tag"[Title/Abstract] OR TMT[Title/Abstract]) AND proteomics'
    year = int(sc.get("year_from") or 2020)
    q = f"{q} AND {year}:3000[dp]"

    search_data = _request_json(
        f"{PUBMED_EUTILS}/esearch.fcgi",
        params={"db": "pubmed", "term": q, "retmax": max_results, "retmode": "json"},
    )
    if not search_data:
        return []
    ids = search_data.get("esearchresult", {}).get("idlist", [])
    if not ids:
        return []

    fetch_r = requests.get(
        f"{PUBMED_EUTILS}/efetch.fcgi",
        params={"db": "pubmed", "id": ",".join(ids), "retmode": "xml"},
        timeout=60,
    )
    if fetch_r.status_code != 200:
        return []

    out: list[dict] = []
    root = ET.fromstring(fetch_r.text)
    for article in root.findall(".//PubmedArticle"):
        pmid_el = article.find(".//PMID")
        pmid = pmid_el.text if pmid_el is not None else ""
        title_el = article.find(".//ArticleTitle")
        title = "".join(title_el.itertext()) if title_el is not None else ""
        abstract_parts = article.findall(".//AbstractText")
        abstract = " ".join("".join(a.itertext()) for a in abstract_parts)
        doi_el = article.find(".//ArticleId[@IdType='doi']")
        doi = doi_el.text if doi_el is not None else ""

        blob = f"{title} {abstract}"
        project_id = ""
        for pat in (r"\b(PXD\d{6,9})\b", r"\b(PDC\d{6,9})\b", r"\b(MSV\d{6,12})\b", r"\b(IPX\d{6,12})\b"):
            m = re.search(pat, blob, re.I)
            if m:
                project_id = m.group(1).upper()
                break

        rec = _blank("PubMed")
        rec.update({
            "project_id": project_id,
            "pmid": pmid,
            "doi": doi,
            "title": title,
            "description": abstract[:2000],
            "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/" if pmid else "",
            "publication": title,
        })
        out.append(rec)
    return out


def search_europepmc(query: str | None = None, max_results: int | None = None) -> list[dict]:
    sc = _cfg_search()
    max_results = max_results or int(sc.get("europepmc_max") or 25)
    q = query or "TMT proteomics human"
    year = int(sc.get("year_from") or 2020)
    data = _request_json(
        EUROPE_PMC,
        params={
            "query": f"{q} AND FIRST_PDATE:[{year}-01-01 TO 3000-12-31]",
            "resultType": "core",
            "pageSize": max_results,
            "format": "json",
        },
    )
    if not data:
        return []

    out: list[dict] = []
    for hit in data.get("resultList", {}).get("result", []):
        pmid = str(hit.get("pmid") or "")
        doi = hit.get("doi") or ""
        title = hit.get("title") or ""
        abstract = hit.get("abstractText") or ""
        blob = f"{title} {abstract}"
        project_id = ""
        for pat in (r"\b(PXD\d{6,9})\b", r"\b(PDC\d{6,9})\b", r"\b(MSV\d{6,12})\b", r"\b(IPX\d{6,12})\b"):
            m = re.search(pat, blob, re.I)
            if m:
                project_id = m.group(1).upper()
                break

        rec = _blank("Europe PMC")
        rec.update({
            "project_id": project_id,
            "pmid": pmid,
            "doi": doi,
            "title": title,
            "description": abstract[:2000],
            "url": hit.get("fullTextUrlList", {}).get("fullTextUrl", [{}])[0].get("url", "")
                if isinstance(hit.get("fullTextUrlList"), dict) else f"https://europepmc.org/article/MED/{pmid}",
            "publication": hit.get("journalTitle") or "",
        })
        out.append(rec)
    return out


def run_all_searches(cfg: dict | None = None) -> tuple[list[dict], list[str], list[str]]:
    cfg = cfg or load_config()
    sources = cfg.get("sources") or {}
    records: list[dict] = []
    errors: list[str] = []
    warnings: list[str] = []

    runners = [
        ("pride", search_pride),
        ("pdc", search_pdc),
        ("massive", search_massive),
        ("iprox", search_iprox),
        ("omicsdi", search_omicsdi),
        ("pubmed", search_pubmed),
        ("europepmc", search_europepmc),
    ]
    for name, fn in runners:
        if not sources.get(name, False):
            continue
        try:
            hits = fn()
            records.extend(hits)
            if not hits:
                warnings.append(f"{name}: 0 results")
        except Exception as exc:
            errors.append(f"{name}: {exc}")

    return records, errors, warnings
