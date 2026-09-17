"""Application service — delegates to EvaluationPipeline."""
from __future__ import annotations

import logging
from typing import Any

from atlas_agent.discovery.evaluation.factory import get_default_pipeline
from atlas_agent.discovery.evaluation.pipeline import EvaluationPipeline
from atlas_agent.discovery.evaluation.sanitize import sanitize_summary
from atlas_agent.discovery.evaluation.schemas import ExclusionReason, ItemKind, ProjectEvaluation

logger = logging.getLogger(__name__)


class EvaluationService:
    """Single entry point; inject a custom pipeline for tests."""

    def __init__(self, pipeline: EvaluationPipeline | None = None) -> None:
        self._pipeline = pipeline or get_default_pipeline()

    def evaluate(
        self,
        item: dict[str, Any],
        *,
        kind: ItemKind | str,
        has_accession: bool = False,
    ) -> ProjectEvaluation:
        return self._pipeline.run(item, kind=kind, has_accession=has_accession)

    def apply_literature_exclusions(self, item: dict[str, Any]) -> dict[str, Any]:
        title = str(item.get("title") or "")
        abstract = str(item.get("abstract") or "")
        ai = dict(item.get("abstract_ai") or {})

        chain = self._pipeline.exclusion_engine.scan(title, abstract)
        exclusion = chain[0] if chain else None
        if exclusion is not None and exclusion.reason is not None:
            reason = exclusion.reason
            ai["atlas_fit"] = "no"
            ai["atlas_fit_score"] = None
            if reason == ExclusionReason.NON_HUMAN:
                ai["exclusion_reason"] = "non-human / xenograft"
            elif reason in (ExclusionReason.METHODOLOGY, ExclusionReason.SINGLE_CELL, ExclusionReason.REVIEW_SOFTWARE):
                ai["exclusion_reason"] = "review / methods / software"
            elif reason == ExclusionReason.PHOSHO_ONLY:
                ai["exclusion_reason"] = "phospho-only emphasis"
            elif reason == ExclusionReason.OFF_ATLAS_DISEASE:
                ai["exclusion_reason"] = "off-atlas / non-cancer disease"
            elif reason == ExclusionReason.BIOFLUID:
                ai["exclusion_reason"] = "biofluid only — need tissue or cell line"
            else:
                ai["exclusion_reason"] = exclusion.detail or reason.value
            logger.info("apply_literature_exclusions: %s", ai["exclusion_reason"])

        for key in ("summary_en", "summary_ru"):
            if key in ai:
                ai[key] = sanitize_summary(ai.get(key))
        if ai.get("summary_ru") and not ai.get("summary_en"):
            ai["summary_en"] = sanitize_summary(ai["summary_ru"])

        item["abstract_ai"] = ai

        evaluation = self._pipeline.run(item, kind=ItemKind.LITERATURE)
        verdict = evaluation.final_verdict
        if ai.get("atlas_fit") == "no":
            item["atlas_fit"] = "no"
            item["atlas_fit_score"] = None
        elif ai.get("atlas_fit") in ("yes", "maybe"):
            item["atlas_fit"] = ai["atlas_fit"]
            if ai.get("atlas_fit_score") is not None:
                item["atlas_fit_score"] = ai["atlas_fit_score"]
        elif verdict == "Watch":
            ai["atlas_fit"] = "maybe"
            item["atlas_fit"] = "maybe"
        elif verdict == "Exclude":
            ai["atlas_fit"] = "no"
            item["atlas_fit"] = "no"
            ai["atlas_fit_score"] = None
            item["atlas_fit_score"] = None

        item["evaluation"] = evaluation.model_dump()
        item["confidence_tier"] = evaluation.confidence
        item["confidence_css"] = evaluation.confidence_css
        item["confidence_evidence"] = evaluation.confidence_bullets
        item["requires_manual_review"] = evaluation.requires_manual_review
        return item
