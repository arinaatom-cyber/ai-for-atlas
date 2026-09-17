"""Factory for default evaluation pipeline (dependency injection)."""
from __future__ import annotations

import logging
from typing import Any

import pandas as pd

from atlas_agent.discovery.evaluation.atlas_index import AtlasIndex, TokenAtlasIndex, build_atlas_index
from atlas_agent.discovery.evaluation.config_loader import load_exclusion_config, load_providers_config
from atlas_agent.discovery.evaluation.exclusion_engine import ExclusionEngine
from atlas_agent.discovery.evaluation.llm_evaluator import LLMEvaluatorRegistry
from atlas_agent.discovery.evaluation.pipeline import EvaluationPipeline
from atlas_agent.discovery.evaluation.similarity_scorer import SimilarityScorer
from atlas_agent.discovery.evaluation.thresholds import DISPLAY_SCORE_MIN, SIMILARITY_CLOSE_MATCH_MIN

logger = logging.getLogger(__name__)

_default_pipeline: EvaluationPipeline | None = None


def build_pipeline(
    *,
    catalog_df: pd.DataFrame | None = None,
    atlas_index: AtlasIndex | None = None,
    exclusion_engine: ExclusionEngine | None = None,
    llm_registry: LLMEvaluatorRegistry | None = None,
    similarity_threshold: float = SIMILARITY_CLOSE_MATCH_MIN,
) -> EvaluationPipeline:
    exclusion = exclusion_engine or ExclusionEngine.from_config(load_exclusion_config())
    registry = llm_registry or LLMEvaluatorRegistry(load_providers_config())
    index = atlas_index
    if index is None and catalog_df is not None and not catalog_df.empty:
        index = build_atlas_index(catalog_df, prefer_faiss=False)
    similarity = SimilarityScorer(index, threshold=similarity_threshold) if index is not None else None
    if similarity is None:
        similarity = SimilarityScorer(TokenAtlasIndex(index=[]), threshold=similarity_threshold)
    logger.info(
        "EvaluationPipeline built exclusion_rules=%s similarity_threshold=%s",
        exclusion.rules_count(),
        similarity_threshold,
    )
    return EvaluationPipeline(exclusion, similarity, registry)


def get_default_pipeline(catalog_df: pd.DataFrame | None = None) -> EvaluationPipeline:
    global _default_pipeline
    if _default_pipeline is None or catalog_df is not None:
        _default_pipeline = build_pipeline(catalog_df=catalog_df)
    return _default_pipeline


def reset_default_pipeline() -> None:
    global _default_pipeline
    _default_pipeline = None
