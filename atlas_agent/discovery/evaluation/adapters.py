"""Adapters between legacy dict pipeline and typed ProjectEvaluation."""
from __future__ import annotations

from typing import Any

from atlas_agent.discovery.evaluation.factory import get_default_pipeline
from atlas_agent.discovery.evaluation.pipeline import EvaluationPipeline
from atlas_agent.discovery.evaluation.schemas import FinalVerdict, ItemKind, ProjectEvaluation
from atlas_agent.discovery.evaluation.service import EvaluationService
from atlas_agent.discovery.evaluation.thresholds import DISPLAY_SCORE_MIN


def _service(pipeline: EvaluationPipeline | None = None) -> EvaluationService:
    return EvaluationService(pipeline or get_default_pipeline())


def evaluate_item(
    item: dict[str, Any],
    *,
    kind: ItemKind | str,
    has_accession: bool = False,
    pipeline: EvaluationPipeline | None = None,
) -> ProjectEvaluation:
    return _service(pipeline).evaluate(item, kind=kind, has_accession=has_accession)


def attach_evaluation(
    item: dict[str, Any],
    *,
    kind: ItemKind | str,
    has_accession: bool = False,
    pipeline: EvaluationPipeline | None = None,
) -> None:
    """Drop-in replacement for confidence.attach_confidence — writes legacy + structured fields."""
    ev = _service(pipeline).evaluate(item, kind=kind, has_accession=has_accession)
    item["confidence_tier"] = ev.confidence
    item["confidence_css"] = ev.confidence_css
    item["confidence_evidence"] = ev.confidence_bullets
    item["evaluation"] = ev.model_dump()
    item["ui_verdict"] = ev.final_verdict
    item["requires_manual_review"] = ev.requires_manual_review


def verdict_badge(evaluation: ProjectEvaluation) -> tuple[str, str, str]:
    """UI layer: label, badge class, tooltip — separated from scoring."""
    v = evaluation.final_verdict
    if v == FinalVerdict.CANDIDATE.value:
        return ("Candidate", "badge-ok", evaluation.confidence_bullets[0] if evaluation.confidence_bullets else "")
    if v == FinalVerdict.EXCLUDE.value:
        detail = ""
        for e in evaluation.evidence_chain:
            if e.detail:
                detail = e.detail
                break
        return ("Exclude", "badge-bad", detail or "Atlas exclusion")
    tip = evaluation.confidence_bullets[0] if evaluation.confidence_bullets else "Needs manual review"
    return ("Review" if evaluation.confidence in ("B", "C") else "Watch", "badge-warn", tip)


def display_fit_score(score: float | None, *, min_threshold: float = DISPLAY_SCORE_MIN) -> str | None:
    """Formatting only — never used inside evaluators."""
    if score is None or score < min_threshold:
        return None
    return f"{score:.2f}"


def display_fit_label(item: dict[str, Any], evaluation: ProjectEvaluation | None = None) -> str:
    if evaluation and evaluation.display_fit_label:
        return evaluation.display_fit_label
    fit = str(item.get("atlas_fit") or (item.get("abstract_ai") or {}).get("atlas_fit") or "").strip()
    if not fit:
        return ""
    return f"LLM {fit}"
