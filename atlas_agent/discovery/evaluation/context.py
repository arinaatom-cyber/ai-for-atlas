from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

import pandas as pd

from atlas_agent.discovery.evaluation.adapters import attach_evaluation, evaluate_item
from atlas_agent.discovery.evaluation.factory import build_pipeline
from atlas_agent.discovery.evaluation.formatter import AnalysisFormatter
from atlas_agent.discovery.evaluation.pipeline import EvaluationPipeline
from atlas_agent.discovery.evaluation.schemas import ItemKind, ProjectEvaluation
from atlas_agent.discovery.evaluation.stale import should_recompute_evaluation

logger = logging.getLogger(__name__)


@dataclass
class EvaluationContext:

    pipeline: EvaluationPipeline
    formatter: AnalysisFormatter = field(default_factory=AnalysisFormatter)

    @classmethod
    def create(cls, *, catalog_df: pd.DataFrame | None = None) -> EvaluationContext:
        pipe = build_pipeline(catalog_df=catalog_df)
        logger.info("EvaluationContext ready (catalog_rows=%s)", len(catalog_df) if catalog_df is not None else 0)
        return cls(pipeline=pipe)

    def resolve(
        self,
        item: dict[str, Any],
        *,
        kind: ItemKind | str,
        has_accession: bool = False,
        mutate: bool = True,
    ) -> ProjectEvaluation:
        stored = item.get("evaluation")
        if stored and item.get("confidence_tier") and not should_recompute_evaluation(item, kind):
            try:
                return ProjectEvaluation.model_validate(stored)
            except Exception:
                logger.warning("Invalid stored evaluation on %s — recomputing", item.get("pmid") or item.get("accession"))

        ev = evaluate_item(item, kind=kind, has_accession=has_accession, pipeline=self.pipeline)
        if mutate:
            item["confidence_tier"] = ev.confidence
            item["confidence_css"] = ev.confidence_css
            item["confidence_evidence"] = ev.confidence_bullets
            item["evaluation"] = ev.model_dump()
            item["ui_verdict"] = ev.final_verdict
            item["requires_manual_review"] = ev.requires_manual_review
        return ev

    def attach(
        self,
        item: dict[str, Any],
        *,
        kind: ItemKind | str,
        has_accession: bool = False,
    ) -> ProjectEvaluation:
        attach_evaluation(item, kind=kind, has_accession=has_accession, pipeline=self.pipeline)
        return ProjectEvaluation.model_validate(item["evaluation"])
