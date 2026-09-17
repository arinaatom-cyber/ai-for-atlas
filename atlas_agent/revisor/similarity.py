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
    index: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Возвращает похожие строки каталога (не дубликат по PXD). Jaccard по токенам title/organ/tissue."""
    cand_acc = (
        candidate.get("accession") or candidate.get("project_id") or candidate.get("pxd") or ""
    ).upper()
    cand_tokens = _tokens(
        " ".join(
            [
                candidate.get("title", ""),
                str(candidate.get("disease") or ""),
                str(candidate.get("primary_site") or candidate.get("organ") or ""),
                " ".join(str(x) for x in (candidate.get("organisms") or [])),
                candidate.get("abstract_snippet", "") or candidate.get("abstract", ""),
            ]
        )
    )
    catalog_index = index if index is not None else catalog_token_index(df)
    best_by_pid: dict[str, dict[str, Any]] = {}
    for entry in catalog_index:
        pid = str(entry["project_id"] or "").upper()
        if not pid or pid == cand_acc:
            continue
        score = jaccard(cand_tokens, entry["tokens"])
        if score < threshold:
            continue
        hit = {
            "project_id": pid,
            "score": round(score, 3),
            "title": entry["title"],
            "row_index": entry["row_index"],
        }
        prev = best_by_pid.get(pid)
        if prev is None or hit["score"] > prev["score"]:
            best_by_pid[pid] = hit
    scored = sorted(best_by_pid.values(), key=lambda x: -x["score"])
    return scored[:top_k]


def annotate_candidates(
    candidates: list[dict],
    df: pd.DataFrame,
    *,
    threshold: float = 0.18,
) -> list[dict]:
    catalog_index = catalog_token_index(df)
    out = []
    for c in candidates:
        c = dict(c)
        sim = find_similar(c, df, threshold=threshold, index=catalog_index)
        if not sim:
            best = find_similar(c, df, threshold=0.0, top_k=1, index=catalog_index)
            if best and float(best[0].get("score") or 0) > 0:
                sim = best
        c["similar_in_catalog"] = sim
        c["has_close_match"] = bool(sim and sim[0]["score"] >= 0.35)
        out.append(c)
    return out
