from __future__ import annotations

from atlas_agent.discovery.evaluation.llm_evaluator import LLMEvaluatorRegistry
from atlas_agent.discovery.evaluation.schemas import ModelTrustLevel

_registry = LLMEvaluatorRegistry()


def trust_level_for_engine(engine: str | None) -> ModelTrustLevel:
    return _registry.trust_for_engine(str(engine or ""))


def evidence_source_label(trust: ModelTrustLevel) -> str:
    if trust == ModelTrustLevel.HIGH:
        return "llm_high"
    if trust == ModelTrustLevel.LOW:
        return "llm_low"
    return "regex_engine"
