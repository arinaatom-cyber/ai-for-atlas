from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable

import numpy as np
import pandas as pd

from atlas_agent.revisor.similarity import _tokens, catalog_token_index, find_similar

logger = logging.getLogger(__name__)

WORD_RE = re.compile(r"[a-z0-9]{4,}", re.I)


@dataclass(frozen=True)
class SimilarityHit:
    project_id: str
    score: float
    title: str = ""


@runtime_checkable
class AtlasIndex(Protocol):

    def search(self, query: str, *, top_k: int = 5) -> list[SimilarityHit]:
        ...


class TokenAtlasIndex:

    def __init__(self, df: pd.DataFrame | None = None, index: list[dict[str, Any]] | None = None) -> None:
        self._df = df
        self._index = index if index is not None else (catalog_token_index(df) if df is not None else [])

    def search(self, query: str, *, top_k: int = 5) -> list[SimilarityHit]:
        if not self._index:
            return []
        cand_tokens = _tokens(query)
        if not cand_tokens:
            return []
        from atlas_agent.revisor.similarity import jaccard

        scored: list[SimilarityHit] = []
        for entry in self._index:
            score = jaccard(cand_tokens, entry["tokens"])
            if score > 0:
                scored.append(
                    SimilarityHit(
                        project_id=entry["project_id"],
                        score=round(score, 4),
                        title=entry.get("title", ""),
                    )
                )
        scored.sort(key=lambda h: -h.score)
        return scored[:top_k]


class FaissAtlasIndex:

    def __init__(self, df: pd.DataFrame, *, fallback: TokenAtlasIndex | None = None) -> None:
        self._fallback = fallback or TokenAtlasIndex(df)
        self._ready = False
        self._dim = 0
        self._index = None
        self._project_ids: list[str] = []
        self._titles: list[str] = []
        self._vectorizer = None
        try:
            import faiss
            from sklearn.feature_extraction.text import TfidfVectorizer

            docs: list[str] = []
            for entry in catalog_token_index(df):
                blob = " ".join(sorted(entry["tokens"]))
                docs.append(blob or entry.get("title", ""))
                self._project_ids.append(entry["project_id"])
                self._titles.append(entry.get("title", ""))
            if not docs:
                return
            self._vectorizer = TfidfVectorizer(max_features=4096, lowercase=True)
            matrix = self._vectorizer.fit_transform(docs).astype(np.float32)
            self._dim = matrix.shape[1]
            self._index = faiss.IndexFlatIP(self._dim)
            faiss.normalize_L2(matrix.toarray())
            self._index.add(matrix.toarray())
            self._ready = True
            logger.info("FaissAtlasIndex ready: %s vectors, dim=%s", len(docs), self._dim)
        except ImportError:
            logger.warning("faiss or sklearn not installed — FaissAtlasIndex uses TokenAtlasIndex fallback")
        except Exception as exc:
            logger.warning("FaissAtlasIndex init failed (%s) — using token fallback", exc)

    def search(self, query: str, *, top_k: int = 5) -> list[SimilarityHit]:
        if not self._ready or self._index is None or self._vectorizer is None:
            return self._fallback.search(query, top_k=top_k)
        try:
            import faiss

            q = self._vectorizer.transform([query]).astype(np.float32).toarray()
            faiss.normalize_L2(q)
            scores, indices = self._index.search(q, min(top_k, len(self._project_ids)))
            hits: list[SimilarityHit] = []
            for score, idx in zip(scores[0], indices[0], strict=False):
                if idx < 0 or score <= 0:
                    continue
                hits.append(
                    SimilarityHit(
                        project_id=self._project_ids[idx],
                        score=round(float(score), 4),
                        title=self._titles[idx],
                    )
                )
            return hits
        except Exception as exc:
            logger.warning("FaissAtlasIndex search failed (%s) — token fallback", exc)
            return self._fallback.search(query, top_k=top_k)


def build_atlas_index(df: pd.DataFrame | None, *, prefer_faiss: bool = True) -> AtlasIndex:
    if df is None or df.empty:
        return TokenAtlasIndex(index=[])
    if prefer_faiss:
        return FaissAtlasIndex(df)
    return TokenAtlasIndex(df)
