"""Batch evaluation enrichment for discovery scan reports."""
from __future__ import annotations

import logging
from typing import Any

import pandas as pd

from atlas_agent.discovery.evaluation.context import EvaluationContext
from atlas_agent.discovery.evaluation.schemas import ItemKind

logger = logging.getLogger(__name__)

_REPORT_BUCKETS: tuple[tuple[str, ItemKind], ...] = (
    ("candidates", ItemKind.PROJECT),
    ("new_projects", ItemKind.PROJECT),
    ("repository_manual", ItemKind.PROJECT),
    ("rejected_material", ItemKind.PROJECT),
    ("manual_check", ItemKind.LITERATURE),
    ("literature_semantic", ItemKind.LITERATURE),
    ("cohort_literature", ItemKind.COHORT),
)


def _has_repo_accession(item: dict[str, Any]) -> bool:
    acc = str(item.get("project_accession") or item.get("accession") or "")
    return acc.upper().startswith(("PXD", "PDC", "MSV", "IPX"))


def evaluate_discovery_report(
    report: dict[str, Any],
    *,
    catalog_df: pd.DataFrame | None = None,
) -> EvaluationContext:
    """Attach typed `evaluation` to every discovery bucket item."""
    ctx = EvaluationContext.create(catalog_df=catalog_df)
    total = 0
    seen: set[int] = set()
    for key, kind in _REPORT_BUCKETS:
        for item in report.get(key) or []:
            oid = id(item)
            if oid in seen:
                continue
            seen.add(oid)
            ctx.attach(item, kind=kind, has_accession=_has_repo_accession(item))
            total += 1
    logger.info(
        "Discovery report evaluated (%s items, catalog_rows=%s)",
        total,
        len(catalog_df) if catalog_df is not None else 0,
    )
    return ctx


def evaluate_discovery_report_from_config(report: dict[str, Any], cfg: dict) -> EvaluationContext:
    """Load catalog once and run catalog-backed similarity scoring."""
    from atlas_agent.discovery import load_catalog_readonly

    df: pd.DataFrame | None
    try:
        df = load_catalog_readonly(cfg)
    except Exception as exc:
        logger.warning("Catalog unavailable — evaluation without similarity index: %s", exc)
        df = None
    return evaluate_discovery_report(report, catalog_df=df)
