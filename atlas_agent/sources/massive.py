"""MassIVE / ProteoSAFe — JSON search (read-only)."""
from __future__ import annotations

import time
from typing import Any

import requests

MASSIVE_API = "https://massive.ucsd.edu/ProteoSAFe/datasets_json.jsp"


def search_massive_tmt(
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
                r = requests.get(MASSIVE_API, params={"task": "search", "query": kw}, timeout=45)
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

        datasets = data if isinstance(data, list) else data.get("datasets", [])
        for d in datasets or []:
            acc = (d.get("accession") or d.get("dataset") or "").upper()
            if not acc.startswith("MSV") or acc in seen or acc in known:
                continue
            blob = f"{d.get('title', '')} {d.get('description', '')}".lower()
            if "tmt" not in blob and "isobaric" not in blob and "tandem mass tag" not in blob:
                continue
            seen.add(acc)
            out.append({
                "accession": acc,
                "title": (d.get("title") or d.get("name") or "")[:500],
                "description": (d.get("description") or "")[:800],
                "url": f"https://massive.ucsd.edu/ProteoSAFe/dataset.jsp?task={acc}",
                "source": "massive_api",
                "tmt_detected": True,
                "human": None,
            })
            if len(out) >= max_results:
                return out
    return out
