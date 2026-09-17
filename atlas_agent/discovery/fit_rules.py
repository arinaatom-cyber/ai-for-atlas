from __future__ import annotations

import re
from typing import Any

from atlas_agent.discovery.evaluation.adapters import evaluate_item, verdict_badge
from atlas_agent.discovery.evaluation.heuristics import (
    has_hard_exclusion,
    scan_cohort_text,
    scan_literature_text,
)
from atlas_agent.discovery.evaluation.sanitize import GARBAGE_SUMMARY, sanitize_summary
from atlas_agent.discovery.evaluation.schemas import ItemKind, ProjectEvaluation
from atlas_agent.discovery.evaluation.stale import should_recompute_evaluation
from atlas_agent.discovery.evaluation.service import EvaluationService

MOUSE_OR_XENO = re.compile(
    r"\b(mouse|mice|murine|rat\b|xenograft|pdx-only|organoid-only)\b",
    re.I,
)

_EVAL = EvaluationService()


def _stored_or_evaluate(item: dict[str, Any], *, kind: ItemKind, has_accession: bool = False) -> ProjectEvaluation:
    stored = item.get("evaluation")
    if stored and item.get("confidence_tier") and not should_recompute_evaluation(item, kind):
        try:
            return ProjectEvaluation.model_validate(stored)
        except Exception:
            pass
    return evaluate_item(item, kind=kind, has_accession=has_accession)


def is_non_study_literature(title: str, abstract: str = "") -> bool:
    return has_hard_exclusion(scan_literature_text(title, abstract))


def is_cohort_excluded(title: str, abstract: str = "") -> bool:
    return has_hard_exclusion(scan_cohort_text(title, abstract))


def apply_literature_exclusions(item: dict[str, Any]) -> dict[str, Any]:
    return _EVAL.apply_literature_exclusions(item)


def project_verdict(item: dict[str, Any]) -> tuple[str, str, str]:
    ev = _stored_or_evaluate(item, kind=ItemKind.PROJECT)
    label, css, tip = verdict_badge(ev)
    if label == "Review":
        da = item.get("data_availability") or {}
        if da.get("omics_layer") == "mixed":
            return ("Review", "badge-warn", "Protein + phospho files — manual check")
        if da.get("status") == "quant_table":
            return ("Candidate", "badge-ok", "Protein-level table in repository")
        if da.get("status") in ("phospho_table", "raw_only", "no_files"):
            return ("Exclude", "badge-bad", "No suitable protein table")
    if label == "Candidate":
        return ("Candidate", "badge-ok", tip)
    if label == "Exclude":
        return ("Exclude", "badge-bad", tip)
    return (label, css, tip)


def literature_verdict(item: dict[str, Any], *, has_accession: bool) -> tuple[str, str, str]:
    ev = _stored_or_evaluate(item, kind=ItemKind.LITERATURE, has_accession=has_accession)
    label, css, tip = verdict_badge(ev)
    if label == "Exclude":
        return ("Exclude", "badge-bad", tip)
    return ("Watch", css if css != "badge-ok" else "badge-warn", tip)


def cohort_verdict(item: dict[str, Any]) -> tuple[str, str, str]:
    ev = _stored_or_evaluate(item, kind=ItemKind.COHORT)
    label, css, tip = verdict_badge(ev)
    if label == "Exclude":
        return ("Exclude", "badge-bad", tip)
    if item.get("tmt_detected"):
        return ("Watch", "badge-ok", tip or "Large cohort + TMT mention")
    return ("Watch", "badge-warn", tip or "Cohort literature — not a new repository ID")


def fit_display_label(item: dict[str, Any]) -> str:
    from atlas_agent.discovery.evaluation.adapters import display_fit_label

    return display_fit_label(item)
