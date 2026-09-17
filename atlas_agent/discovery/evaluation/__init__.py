"""Typed discovery evaluation — Clean Architecture boundary."""
from atlas_agent.discovery.evaluation.adapters import (
    attach_evaluation,
    display_fit_label,
    display_fit_score,
    evaluate_item,
    verdict_badge,
)
from atlas_agent.discovery.evaluation.exclusion_engine import ExclusionEngine
from atlas_agent.discovery.evaluation.factory import build_pipeline, get_default_pipeline, reset_default_pipeline
from atlas_agent.discovery.evaluation.formatter import AnalysisFormatter
from atlas_agent.discovery.evaluation.llm_evaluator import (
    CloudEvaluator,
    LLMEvaluationResult,
    LLMEvaluator,
    LLMEvaluatorRegistry,
    LocalEvaluator,
    RulesEvaluator,
)
from atlas_agent.discovery.evaluation.pipeline import EvaluationPipeline
from atlas_agent.discovery.evaluation.schemas import (
    ConfidenceTier,
    EvaluationEvidence,
    ExclusionReason,
    FinalVerdict,
    ItemKind,
    LLMVerdict,
    ModelTrustLevel,
    ProjectEvaluation,
)
from atlas_agent.discovery.evaluation.context import EvaluationContext
from atlas_agent.discovery.evaluation.report import evaluate_discovery_report, evaluate_discovery_report_from_config
from atlas_agent.discovery.evaluation.service import EvaluationService
from atlas_agent.discovery.evaluation.similarity_scorer import SimilarityScorer
from atlas_agent.discovery.evaluation.thresholds import DISPLAY_SCORE_MIN

__all__ = [
    "AnalysisFormatter",
    "CloudEvaluator",
    "ConfidenceTier",
    "DISPLAY_SCORE_MIN",
    "EvaluationEvidence",
    "EvaluationPipeline",
    "EvaluationContext",
    "evaluate_discovery_report",
    "evaluate_discovery_report_from_config",
    "EvaluationService",
    "ExclusionEngine",
    "ExclusionReason",
    "FinalVerdict",
    "ItemKind",
    "LLMEvaluationResult",
    "LLMEvaluator",
    "LLMEvaluatorRegistry",
    "LLMVerdict",
    "LocalEvaluator",
    "ModelTrustLevel",
    "ProjectEvaluation",
    "RulesEvaluator",
    "SimilarityScorer",
    "attach_evaluation",
    "build_pipeline",
    "display_fit_label",
    "display_fit_score",
    "evaluate_item",
    "get_default_pipeline",
    "reset_default_pipeline",
    "verdict_badge",
]
