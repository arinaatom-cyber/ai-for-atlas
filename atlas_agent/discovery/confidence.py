"""Rule-calibrated confidence tiers — delegates to evaluation module."""
from __future__ import annotations

from typing import Any

from atlas_agent.discovery.evaluation import attach_evaluation, evaluate_item
from atlas_agent.discovery.evaluation.schemas import ItemKind


def project_confidence(item: dict[str, Any]) -> tuple[str, str, list[str]]:
    ev = evaluate_item(item, kind=ItemKind.PROJECT)
    return ev.confidence, ev.confidence_css, ev.confidence_bullets


def literature_confidence(item: dict[str, Any], *, has_accession: bool) -> tuple[str, str, list[str]]:
    ev = evaluate_item(item, kind=ItemKind.LITERATURE, has_accession=has_accession)
    return ev.confidence, ev.confidence_css, ev.confidence_bullets


def cohort_confidence(item: dict[str, Any]) -> tuple[str, str, list[str]]:
    ev = evaluate_item(item, kind=ItemKind.COHORT)
    return ev.confidence, ev.confidence_css, ev.confidence_bullets


def attach_confidence(item: dict[str, Any], *, kind: str, has_accession: bool = False) -> None:
    attach_evaluation(item, kind=kind, has_accession=has_accession)
