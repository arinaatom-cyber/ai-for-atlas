"""Strategy-pattern exclusion engine — compiled regex from configuration."""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Any

from atlas_agent.discovery.evaluation.config_loader import load_exclusion_config, parse_exclusion_reason
from atlas_agent.discovery.evaluation.schemas import EvaluationEvidence, ExclusionReason

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ExclusionRule:
    pattern: re.Pattern[str]
    reason: ExclusionReason
    detail: str
    scope: str
    unless_pattern: re.Pattern[str] | None
    require_absent: re.Pattern[str] | None


class ExclusionEngine:
    """Evaluate title/abstract against configured exclusion strategies."""

    def __init__(self, rules: list[ExclusionRule] | None = None) -> None:
        self._rules = rules if rules is not None else self._compile_rules(load_exclusion_config())

    @classmethod
    def from_config(cls, patterns: list[dict[str, Any]]) -> ExclusionEngine:
        return cls(rules=cls._compile_rules(patterns))

    @staticmethod
    def _compile_rules(raw_patterns: list[dict[str, Any]]) -> list[ExclusionRule]:
        compiled: list[ExclusionRule] = []
        for idx, row in enumerate(raw_patterns):
            pat = str(row.get("pattern") or "").strip()
            if not pat:
                logger.warning("Skipping exclusion rule %s: empty pattern", idx)
                continue
            reason_raw = row.get("reason")
            try:
                reason = parse_exclusion_reason(str(reason_raw))
            except ValueError:
                logger.warning("Skipping exclusion rule %s: invalid reason %s", idx, reason_raw)
                continue
            unless = row.get("unless_pattern")
            require_absent = row.get("require_absent")
            compiled.append(
                ExclusionRule(
                    pattern=re.compile(pat, re.I),
                    reason=reason,
                    detail=str(row.get("detail") or reason.value),
                    scope=str(row.get("scope") or "full").lower(),
                    unless_pattern=re.compile(str(unless), re.I) if unless else None,
                    require_absent=re.compile(str(require_absent), re.I) if require_absent else None,
                )
            )
        logger.info("ExclusionEngine loaded %s compiled rules", len(compiled))
        return compiled

    def _blob(self, title: str, abstract: str, scope: str) -> str:
        if scope == "title":
            return title or ""
        if scope == "cohort":
            return f"{title or ''} {abstract or ''}"
        return f"{title or ''} {abstract or ''}"

    def _matches_rule(self, rule: ExclusionRule, title: str, abstract: str) -> bool:
        blob = self._blob(title, abstract, rule.scope)
        if not rule.pattern.search(blob):
            return False
        if rule.unless_pattern and rule.unless_pattern.search(blob):
            return False
        if rule.require_absent and rule.require_absent.search(blob):
            return False
        return True

    def rules_count(self) -> int:
        return len(self._rules)

    def check(self, title: str, abstract: str = "") -> EvaluationEvidence | None:
        """Return first matching exclusion evidence, or None."""
        for rule in self._rules:
            if rule.scope == "cohort":
                continue
            if self._matches_rule(rule, title, abstract):
                return EvaluationEvidence(
                    source="exclusion_engine",
                    reason=rule.reason,
                    is_actionable=True,
                    detail=rule.detail,
                )
        return None

    def check_cohort(self, title: str, abstract: str = "") -> EvaluationEvidence | None:
        for rule in self._rules:
            if rule.scope == "cohort" and self._matches_rule(rule, title, abstract):
                return EvaluationEvidence(
                    source="exclusion_engine",
                    reason=rule.reason,
                    is_actionable=True,
                    detail=rule.detail,
                )
            if rule.scope == "title" and rule.reason in (
                ExclusionReason.METHODOLOGY,
                ExclusionReason.REVIEW_SOFTWARE,
            ) and self._matches_rule(rule, title, abstract):
                return EvaluationEvidence(
                    source="exclusion_engine",
                    reason=rule.reason,
                    is_actionable=True,
                    detail=rule.detail,
                )
        return None

    def scan(self, title: str, abstract: str = "") -> list[EvaluationEvidence]:
        """Full evidence chain for all matching rules (literature scope)."""
        hits: list[EvaluationEvidence] = []
        for rule in self._rules:
            if rule.scope == "cohort":
                continue
            if self._matches_rule(rule, title, abstract):
                hits.append(
                    EvaluationEvidence(
                        source="exclusion_engine",
                        reason=rule.reason,
                        is_actionable=True,
                        detail=rule.detail,
                    )
                )
        return hits
