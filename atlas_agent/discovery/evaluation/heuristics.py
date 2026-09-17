from __future__ import annotations

from atlas_agent.discovery.evaluation.exclusion_engine import ExclusionEngine
from atlas_agent.discovery.evaluation.schemas import EvaluationEvidence

_default_engine = ExclusionEngine()


def scan_literature_text(title: str, abstract: str = "", *, engine: ExclusionEngine | None = None) -> list[EvaluationEvidence]:
    eng = engine or _default_engine
    return eng.scan(title, abstract)


def scan_cohort_text(title: str, abstract: str = "", *, engine: ExclusionEngine | None = None) -> list[EvaluationEvidence]:
    eng = engine or _default_engine
    hits = list(eng.scan(title, abstract))
    extra = eng.check_cohort(title, abstract)
    if extra is not None and extra.reason is not None:
        if not any(h.reason == extra.reason and h.detail == extra.detail for h in hits):
            hits.append(extra)
    return hits


def has_hard_exclusion(chain: list[EvaluationEvidence]) -> bool:
    return any(e.reason is not None for e in chain)
