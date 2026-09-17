"""Normalize records; optional HTML fallback for incomplete API metadata."""
from __future__ import annotations

import re
from typing import Any

import requests
from bs4 import BeautifulSoup

from src.utils import load_config

RECORD_TEMPLATE = {
    "database": "",
    "project_id": "",
    "pmid": "",
    "doi": "",
    "title": "",
    "url": "",
    "description": "",
    "organism": "",
    "method": "",
    "sample_type": "",
    "publication": "",
    "source_type": "",
    "evidence_url": "",
    "evidence_text": "",
    "keywords": "",
}


def _fetch_html(url: str) -> str:
    if not url:
        return ""
    try:
        r = requests.get(url, timeout=30, headers={"User-Agent": "TMT-Project-Finder/1.0"})
        if r.status_code == 200:
            return r.text
    except requests.RequestException:
        pass
    return ""


def _extract_from_html(html: str, url: str) -> dict[str, str]:
    if not html:
        return {}
    soup = BeautifulSoup(html, "html.parser")
    out: dict[str, str] = {"evidence_url": url, "source_type": "html_fallback"}

    title = soup.find("title")
    if title:
        out["title"] = title.get_text(strip=True)[:500]

    meta_desc = soup.find("meta", attrs={"name": re.compile(r"description", re.I)})
    if meta_desc and meta_desc.get("content"):
        out["description"] = meta_desc["content"][:3000]

    text = soup.get_text(" ", strip=True)[:8000]
    out["evidence_text"] = text

    doi_m = re.search(r"\b(10\.\d{4,9}/[^\s\"<>]+)", text)
    if doi_m:
        out["doi"] = doi_m.group(1).rstrip(".,;")

    pmid_m = re.search(r"\bPMID[:\s]*(\d{7,9})\b", text, re.I)
    if pmid_m:
        out["pmid"] = pmid_m.group(1)

    kw_meta = soup.find("meta", attrs={"name": re.compile(r"keywords", re.I)})
    if kw_meta and kw_meta.get("content"):
        out["keywords"] = kw_meta["content"][:500]

    return out


def _pride_json_fallback(project_id: str) -> dict[str, str]:
    if not project_id.upper().startswith("PXD"):
        return {}
    url = f"https://www.ebi.ac.uk/pride/ws/archive/v2/projects/{project_id.upper()}"
    try:
        r = requests.get(url, timeout=30)
        if r.status_code != 200:
            return {}
        p = r.json()
        orgs = [o.get("name", "") for o in (p.get("organisms") or []) if isinstance(o, dict)]
        return {
            "title": p.get("title") or "",
            "description": p.get("projectDescription") or "",
            "organism": "; ".join(orgs),
            "method": " ".join(str(x) for x in (p.get("quantificationMethods") or [])),
            "keywords": ", ".join(str(x) for x in (p.get("keywords") or [])),
            "source_type": "pride_api_v2",
            "evidence_url": url,
        }
    except (requests.RequestException, ValueError):
        return {}


def normalize_record(record: dict[str, Any], *, use_html_fallback: bool | None = None) -> dict[str, Any]:
    """Bring any source record to unified schema."""
    cfg = load_config()
    if use_html_fallback is None:
        use_html_fallback = bool(cfg.get("use_html_fallback", True))

    out = dict(RECORD_TEMPLATE)
    for k in RECORD_TEMPLATE:
        if record.get(k):
            out[k] = str(record[k]).strip()

    # Aliases from raw APIs
    aliases = {
        "accession": "project_id",
        "project_accession": "project_id",
        "projectDescription": "description",
        "abstract": "description",
    }
    for src, dst in aliases.items():
        if record.get(src) and not out.get(dst):
            out[dst] = str(record[src]).strip()

    if out["project_id"]:
        out["project_id"] = out["project_id"].upper()

    if not out["url"] and out["project_id"]:
        pid = out["project_id"]
        if pid.startswith("PXD"):
            out["url"] = f"https://www.ebi.ac.uk/pride/archive/projects/{pid}"
        elif pid.startswith("PDC"):
            out["url"] = f"https://proteomic.datacommons.cancer.gov/pdc/study/{pid}"
        elif pid.startswith("MSV"):
            out["url"] = f"https://massive.ucsd.edu/ProteoSAFe/dataset.jsp?task={pid}"

    needs_enrichment = not out["description"] or not out["title"]
    if use_html_fallback and needs_enrichment:
        extra: dict[str, str] = {}
        if out["project_id"].startswith("PXD"):
            extra = _pride_json_fallback(out["project_id"])
        elif out["url"]:
            html = _fetch_html(out["url"])
            extra = _extract_from_html(html, out["url"])

        for k, v in extra.items():
            if v and not out.get(k):
                out[k] = v
            elif k in ("evidence_text", "evidence_url", "source_type", "keywords") and v:
                out[k] = v

    return out
