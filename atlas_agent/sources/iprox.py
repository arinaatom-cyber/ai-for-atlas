from __future__ import annotations

import time
from typing import Any

import requests

from atlas_agent.discovery.organism_terms import is_human_text, is_non_human_text
from atlas_agent.sources.text_limits import DESCRIPTION_LIMIT

IPROX_SEARCH = "https://www.iprox.cn/proteomics/search"


def _organism_text(item: dict[str, Any]) -> str:
    for k in ("species", "organism", "organisms", "taxonomy", "Species"):
        v = item.get(k)
        if isinstance(v, list):
            return " ".join(
                str(x.get("name", x) if isinstance(x, dict) else x) for x in v
            )
        if isinstance(v, dict):
            return str(v.get("name") or v.get("scientificName") or "")
        if v:
            return str(v)
    return ""


def _human_flag(org: str, blob: str) -> bool | None:
    text = f"{org} {blob}"
    if is_non_human_text(text):
        return False
    if is_human_text(org) or is_human_text(blob):
        return True
    return None


def search_iprox_tmt(
    keywords: list[str] | None = None,
    *,
    max_results: int | None = None,
    max_pages: int = 8,
    exclude_accessions: set[str] | None = None,
    stats: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    kws = keywords or ["TMT", "tandem mass tag"]
    known = {a.upper() for a in (exclude_accessions or set())}
    page_size = 200 if max_results is None else min(int(max_results), 200)
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    failed_requests = 0

    for kw in kws[:3]:
        for page in range(1, max_pages + 1):
            data = None
            for attempt in range(3):
                try:
                    r = requests.get(
                        IPROX_SEARCH,
                        params={"q": kw, "pageSize": page_size, "page": page},
                        headers={"Accept": "application/json"},
                        timeout=45,
                    )
                    if r.status_code != 200:
                        break
                    data = r.json()
                    break
                except (requests.RequestException, ValueError):
                    if attempt < 2:
                        time.sleep(2 ** attempt)
                    else:
                        data = None
            if not data:
                failed_requests += 1
                break

            items = data if isinstance(data, list) else data.get("list", data.get("data", []))
            if not items:
                break
            new_this_page = 0
            for item in items or []:
                acc = (item.get("projectId") or item.get("accession") or "").upper()
                if not acc.startswith("IPX") or acc in seen or acc in known:
                    continue
                desc = str(item.get("summary") or item.get("description") or "")
                org = _organism_text(item)
                blob = f"{item.get('title', '')} {desc} {org}".lower()
                if "tmt" not in blob and "isobaric" not in blob:
                    continue
                seen.add(acc)
                new_this_page += 1
                out.append({
                    "accession": acc,
                    "title": (item.get("title") or "")[:500],
                    "description": desc[:DESCRIPTION_LIMIT],
                    "organisms": [org] if org else [],
                    "url": item.get("projectUrl") or f"https://www.iprox.cn/page/project.html?id={acc}",
                    "source": "iprox_api",
                    "tmt_detected": True,
                    "human": _human_flag(org, blob),
                })
                if max_results is not None and len(out) >= max_results:
                    if stats is not None:
                        stats["failed_requests"] = failed_requests
                    return out
            if new_this_page == 0 or len(items) < page_size:
                break
            time.sleep(0.2)
    if stats is not None:
        stats["failed_requests"] = failed_requests
    return out
