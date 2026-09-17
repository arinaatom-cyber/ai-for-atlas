"""Capability-based LLM evaluators — trust from providers.yml, not model filenames."""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from atlas_agent.discovery.evaluation.config_loader import load_providers_config, parse_trust_level
from atlas_agent.discovery.evaluation.sanitize import sanitize_summary
from atlas_agent.discovery.evaluation.schemas import EvaluationEvidence, LLMVerdict, ModelTrustLevel
from atlas_agent.discovery.evaluation.thresholds import DISPLAY_SCORE_MIN

logger = logging.getLogger(__name__)


@dataclass
class LLMEvaluationResult:
    verdict: LLMVerdict | None
    evidence: list[EvaluationEvidence] = field(default_factory=list)
    requires_manual_review: bool = False
    confidence_downgrade: int = 0


class LLMEvaluator(ABC):
    trust: ModelTrustLevel

    @abstractmethod
    def evaluate(self, item: dict[str, Any]) -> LLMEvaluationResult:
        ...


def _parse_score(raw: Any) -> float | None:
    try:
        if raw is None:
            return None
        return max(0.0, min(1.0, float(raw)))
    except (TypeError, ValueError):
        return None


def _legacy_fit_bool(fit_raw: str) -> bool:
    return str(fit_raw or "").lower() == "yes"


def _build_verdict_from_item(item: dict[str, Any]) -> tuple[str, LLMVerdict | None, float | None, str]:
    ai = item.get("abstract_ai") or {}
    fit_raw = str(ai.get("atlas_fit") or item.get("atlas_fit") or "").lower()
    if not fit_raw:
        return "", None, None, ""
    reader = str(item.get("abstract_reader") or ai.get("reader") or "")
    score = _parse_score(ai.get("atlas_fit_score"))
    material = str(ai.get("material") or "")[:100] or None
    reasoning = sanitize_summary(ai.get("summary_en") or ai.get("summary_ru") or "")[:150]
    if not reasoning:
        reasoning = f"atlas_fit={fit_raw}"
    verdict = LLMVerdict(fit=_legacy_fit_bool(fit_raw), material=material, reasoning=reasoning)
    return fit_raw, verdict, score, reader


class CloudEvaluator(LLMEvaluator):
    trust = ModelTrustLevel.HIGH

    def evaluate(self, item: dict[str, Any]) -> LLMEvaluationResult:
        fit_raw, verdict, score, reader = _build_verdict_from_item(item)
        if verdict is None:
            return LLMEvaluationResult(verdict=None)
        actionable = score is None or score >= DISPLAY_SCORE_MIN
        ev = EvaluationEvidence(
            source="llm_high",
            score=score,
            is_actionable=actionable and fit_raw in ("yes", "maybe"),
            detail=f"reader={reader}; fit={fit_raw}",
        )
        manual = fit_raw in ("yes", "maybe") and not _legacy_fit_bool(fit_raw)
        return LLMEvaluationResult(
            verdict=verdict,
            evidence=[ev],
            requires_manual_review=manual or fit_raw == "maybe",
        )


class MediumEvaluator(LLMEvaluator):
    trust = ModelTrustLevel.MEDIUM

    def evaluate(self, item: dict[str, Any]) -> LLMEvaluationResult:
        fit_raw, verdict, score, reader = _build_verdict_from_item(item)
        if verdict is None:
            return LLMEvaluationResult(verdict=None)
        regex_fit = str((item.get("abstract_ai") or {}).get("regex_fit") or "").lower()
        actionable = score is None or score >= DISPLAY_SCORE_MIN
        evidence = [
            EvaluationEvidence(
                source="llm_medium",
                score=score,
                is_actionable=actionable and fit_raw in ("yes", "maybe"),
                detail=f"reader={reader}; fit={fit_raw}; regex={regex_fit or '?'}",
            )
        ]
        requires_manual = fit_raw in ("yes", "maybe")
        downgrade = 0
        if verdict.fit and regex_fit != "yes":
            requires_manual = True
            if regex_fit == "no":
                downgrade = 1
        elif fit_raw == "maybe":
            requires_manual = True
        return LLMEvaluationResult(
            verdict=verdict,
            evidence=evidence,
            requires_manual_review=requires_manual,
            confidence_downgrade=downgrade,
        )


class LocalEvaluator(LLMEvaluator):
    trust = ModelTrustLevel.LOW

    def evaluate(self, item: dict[str, Any]) -> LLMEvaluationResult:
        fit_raw, verdict, score, reader = _build_verdict_from_item(item)
        if verdict is None:
            return LLMEvaluationResult(verdict=None)
        actionable = score is not None and score >= DISPLAY_SCORE_MIN
        evidence = [
            EvaluationEvidence(
                source="llm_low",
                score=score,
                is_actionable=actionable and fit_raw in ("yes", "maybe"),
                detail=f"reader={reader}; fit={fit_raw}",
            )
        ]
        requires_manual = False
        downgrade = 0
        if verdict.fit:
            requires_manual = True
            downgrade = 1
            evidence.append(
                EvaluationEvidence(
                    source="llm_low_override",
                    score=score,
                    is_actionable=True,
                    detail="LOW-trust model positive fit — manual review required",
                )
            )
            logger.info("LocalEvaluator override: fit=True reader=%s downgrade=1", reader)
        elif fit_raw == "maybe":
            requires_manual = True
        return LLMEvaluationResult(
            verdict=verdict,
            evidence=evidence,
            requires_manual_review=requires_manual,
            confidence_downgrade=downgrade,
        )


class RulesEvaluator(LLMEvaluator):
    trust = ModelTrustLevel.RULES

    def evaluate(self, item: dict[str, Any]) -> LLMEvaluationResult:
        fit_raw, verdict, score, reader = _build_verdict_from_item(item)
        if verdict is None:
            return LLMEvaluationResult(verdict=None)
        ev = EvaluationEvidence(
            source="regex_engine",
            score=score,
            is_actionable=bool(score and score >= DISPLAY_SCORE_MIN),
            detail=f"reader={reader}; fit={fit_raw}",
        )
        return LLMEvaluationResult(verdict=verdict, evidence=[ev], requires_manual_review=fit_raw == "maybe")


class LLMEvaluatorRegistry:
    """Resolve evaluator implementation from providers.yml — prefix match only."""

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        cfg = config if config is not None else load_providers_config()
        self._default_key = str(cfg.get("default_evaluator") or "local")
        evaluators_cfg = cfg.get("evaluators") or {}
        self._implementations: dict[str, LLMEvaluator] = {
            "cloud": CloudEvaluator(),
            "medium": MediumEvaluator(),
            "local": LocalEvaluator(),
            "rules": RulesEvaluator(),
        }
        self._provider_map: dict[str, str] = {}
        providers = cfg.get("providers") or {}
        if isinstance(providers, dict):
            for provider_id, evaluator_key in providers.items():
                self._provider_map[str(provider_id).lower()] = str(evaluator_key).lower()
        self._evaluator_trust: dict[str, ModelTrustLevel] = {}
        if isinstance(evaluators_cfg, dict):
            for key, meta in evaluators_cfg.items():
                if isinstance(meta, dict) and meta.get("trust"):
                    self._evaluator_trust[str(key).lower()] = parse_trust_level(str(meta["trust"]))
        logger.info(
            "LLMEvaluatorRegistry: %s providers, default=%s",
            len(self._provider_map),
            self._default_key,
        )

    def resolve_provider_key(self, engine: str) -> str:
        e = str(engine or "").strip().lower()
        if not e:
            return self._default_key
        if e in self._provider_map:
            return self._provider_map[e]
        prefix = e.split(":", 1)[0]
        if prefix in self._provider_map:
            return self._provider_map[prefix]
        for provider_id, evaluator_key in self._provider_map.items():
            if e.startswith(f"{provider_id}:"):
                return evaluator_key
        logger.debug("Unknown engine %s — default evaluator %s", engine, self._default_key)
        return self._default_key

    def for_engine(self, engine: str) -> LLMEvaluator:
        key = self.resolve_provider_key(engine)
        impl = self._implementations.get(key)
        if impl is None:
            logger.warning("Evaluator key %s missing — using local", key)
            return self._implementations["local"]
        return impl

    def trust_for_engine(self, engine: str) -> ModelTrustLevel:
        key = self.resolve_provider_key(engine)
        if key in self._evaluator_trust:
            return self._evaluator_trust[key]
        return self.for_engine(engine).trust
