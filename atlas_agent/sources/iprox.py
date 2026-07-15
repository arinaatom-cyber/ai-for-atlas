"""iProX — JSON search (read-only, best-effort)."""
from __future__ import annotations

import time
from typing import Any

import requests

IPROX_SEARCH = "https://www.iprox.cn/proteomics/search"


def search_iprox_tmt(
    keywords: list[str] | None = None,
    *,
    max_results: int = 30,
    exclude_accessions: set[str] | None = None,
) -> list[dict[str, Any]]:
    kws = keywords or ["TMT", "tandem mass tag"]
    known = {a.upper() for a in (exclude_accessions or set())}
    out: list[dict[str, Any]] = []
    seen: set[str] = set()

    for kw in kws[:3]:
        for attempt in range(3):
            try:
                r = requests.get(
                    IPROX_SEARCH,
                    params={"q": kw, "pageSize": max_results},
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
            continue

        items = data if isinstance(data, list) else data.get("list", data.get("data", []))
        for item in items or []:
            acc = (item.get("projectId") or item.get("accession") or "").upper()
            if not acc.startswith("IPX") or acc in seen or acc in known:
                continue
            blob = f"{item.get('title', '')} {item.get('summary', '')} {item.get('description', '')}".lower()
            if "tmt" not in blob and "isobaric" not in blob:
                continue
            seen.add(acc)
            out.append({
                "accession": acc,
                "title": (item.get("title") or "")[:500],
                "description": (item.get("summary") or item.get("description") or "")[:800],
                "url": item.get("projectUrl") or f"https://www.iprox.cn/page/project.html?id={acc}",
                "source": "iprox_api",
                "tmt_detected": True,
                "human": None,
            })
            if len(out) >= max_results:
                return out
    return out
