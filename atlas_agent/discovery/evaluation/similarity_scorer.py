"""Semantic / lexical similarity gate with actionable threshold."""
from __future__ import annotations

import logging

from atlas_agent.discovery.evaluation.atlas_index import AtlasIndex, SimilarityHit
from atlas_agent.discovery.evaluation.schemas import EvaluationEvidence

logger = logging.getLogger(__name__)


class SimilarityScorer:
    """Score query text against atlas index; mark low scores non-actionable."""

    def __init__(self, atlas_index: AtlasIndex, *, threshold: float = 0.35) -> None:
        self._index = atlas_index
        self._threshold = threshold

    @property
    def threshold(self) -> float:
        return self._threshold

    def evaluate(self, query: str, *, top_k: int = 3) -> EvaluationEvidence:
        hits = self._index.search(query, top_k=top_k)
        if not hits:
            logger.debug("SimilarityScorer: no hits for query len=%s", len(query))
            return EvaluationEvidence(
                source="similarity_scorer",
                score=0.0,
                is_actionable=False,
                detail="no catalog similarity hits",
            )
        best: SimilarityHit = hits[0]
        actionable = best.score >= self._threshold
        detail = f"nearest {best.project_id} ({best.score:.3f})"
        if not actionable:
            detail = f"below threshold {self._threshold}: {detail}"
        logger.debug("SimilarityScorer: %s actionable=%s", detail, actionable)
        return EvaluationEvidence(
            source="similarity_scorer",
            score=best.score,
            is_actionable=actionable,
            detail=detail,
        )
