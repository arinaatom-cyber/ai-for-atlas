"""Похожие проекты в каталоге (для дедупликации и подсказок)."""
from __future__ import annotations

import re
from typing import Any

import pandas as pd

from atlas_agent.sources.projects_table import primary_project_id

WORD_RE = re.compile(r"[a-z0-9]{4,}", re.I)
STOP = {
    "with", "from", "that", "this", "using", "human", "study", "analysis",
    "proteome", "proteomic", "proteomics", "mass", "spectrometry", "based",
}


def _tokens(text: str) -> set[str]:
    return {w.lower() for w in WORD_RE.findall(text or "") if w.lower() not in STOP}


def jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def catalog_token_index(df: pd.DataFrame) -> list[dict[str, Any]]:
    rows = []
    for idx, r in df.iterrows():
        pid = primary_project_id(str(r.get("Project ID", "")))
        if not pid:
            continue
        blob = " ".join(
            str(r.get(c, "") or "")
            for c in ("Title", "Organ", "Tissue", "Disease", "Short Description", "TMT Label (Unified)")
        )
        rows.append(
            {
                "row_index": int(idx),
                "project_id": pid,
                "tokens": _tokens(blob),
                "organ": str(r.get("Organ", "") or "").lower(),
                "title": str(r.get("Title", "") or "")[:120],
            }
        )
    return rows


def find_similar(
    candidate: dict[str, Any],
    df: pd.DataFrame,
    *,
    threshold: float = 0.18,
    top_k: int = 5,
) -> list[dict[str, Any]]:
    """Возвращает похожие строки каталога (не дубликат по PXD)."""
    cand_acc = (
        candidate.get("accession") or candidate.get("project_id") or candidate.get("pxd") or ""
    ).upper()
    cand_tokens = _tokens(
        " ".join(
            [
                candidate.get("title", ""),
                " ".join(str(x) for x in (candidate.get("organisms") or [])),
                candidate.get("abstract_snippet", "") or candidate.get("abstract", ""),
            ]
        )
    )
    index = catalog_token_index(df)
    scored = []
    for entry in index:
        if entry["project_id"] == cand_acc:
            continue
        score = jaccard(cand_tokens, entry["tokens"])
        if score >= threshold:
            scored.append(
                {
                    "project_id": entry["project_id"],
                    "score": round(score, 3),
                    "title": entry["title"],
                    "row_index": entry["row_index"],
                }
            )
    scored.sort(key=lambda x: -x["score"])
    return scored[:top_k]


def annotate_candidates(
    candidates: list[dict],
    df: pd.DataFrame,
    *,
    threshold: float = 0.18,
) -> list[dict]:
    out = []
    for c in candidates:
        c = dict(c)
        sim = find_similar(c, df, threshold=threshold)
        c["similar_in_catalog"] = sim
        c["has_close_match"] = bool(sim and sim[0]["score"] >= 0.35)
        out.append(c)
    return out
