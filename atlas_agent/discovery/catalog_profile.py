"""Профиль вашего каталога — для поиска похожих проектов в интернете."""
from __future__ import annotations

import re
from collections import Counter
from typing import Any

import pandas as pd

from atlas_agent.sources.projects_table import primary_project_id


def build_catalog_profile(df: pd.DataFrame) -> dict[str, Any]:
    ids = []
    organs: Counter = Counter()
    diseases: Counter = Counter()
    databases: Counter = Counter()
    tmt_labels: Counter = Counter()

    for _, r in df.iterrows():
        pid = primary_project_id(str(r.get("Project ID", "")))
        if pid:
            ids.append(pid)
        db = str(r.get("Database", "") or "").strip()
        if db:
            databases[db] += 1
        for col, bucket in (("Organ", organs), ("Disease", diseases)):
            val = str(r.get(col, "") or "")
            for part in re.split(r"[;,/|]", val):
                part = part.strip()
                if len(part) > 2:
                    bucket[part.lower()] += 1
        tmt = str(r.get("TMT Label (Unified)", "") or "")
        if "tmt" in tmt.lower():
            tmt_labels[tmt[:40]] += 1

    return {
        "n_rows": len(df),
        "n_unique_ids": len(set(ids)),
        "project_ids_sample": sorted(set(ids))[:30],
        "databases": dict(databases.most_common(10)),
        "top_organs": [k for k, _ in organs.most_common(12)],
        "top_diseases": [k for k, _ in diseases.most_common(12)],
        "tmt_plexes": [k for k, _ in tmt_labels.most_common(8)],
        "search_keywords": _build_keywords(organs, diseases, tmt_labels),
    }


def _build_keywords(organs, diseases, tmt_labels) -> list[str]:
    kw = ["TMT", "tandem mass tag", "human proteomics", "isobaric"]
    kw.extend([o for o, _ in organs.most_common(5) if o not in ("", "nan")])
    kw.extend([d for d, _ in diseases.most_common(5) if d not in ("", "nan", "healthy")])
    kw.extend(["PDC", "CPTAC", "CCLE", "GTEx", "proteogenomics"])
    # unique preserve order
    seen = set()
    out = []
    for k in kw:
        kl = k.lower().strip()
        if kl and kl not in seen:
            seen.add(kl)
            out.append(k)
    return out[:20]
