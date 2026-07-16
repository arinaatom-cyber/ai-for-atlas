"""Canonical rules for reading TMT ATLAS cells (empty vs zero vs gap)."""
from __future__ import annotations

import math
import re
from typing import Any, Literal

CellState = Literal["empty", "zero", "value", "text", "invalid"]

_EMPTY_TOKENS = frozenset({"", "nan", "none", "na", "n/a", "—", "-", ".", "null"})

SAMPLE_COUNT_COLS = [
    "Total Samples",
    "preCancer",
    "Case Cancer Untreated",
    "Case Cancer Treated",
    "Control Healthy",
    "Healthy Treated",
    "Patients / donors",
    "Samples Original N",
    "Samples Used N",
]

TEXT_REQUIRED_WHEN_MISSING = {
    "Organ": ("Tissue", "Cell Line Organ", "Tissue for cell lines"),
    "Disease": ("Tumor Type", "Disease Subtype"),
}


def strip_cell(v: Any) -> str:
    if v is None:
        return ""
    if isinstance(v, float) and math.isnan(v):
        return ""
    s = str(v).strip()
    if s.lower() in _EMPTY_TOKENS:
        return ""
    return s


def cell_state(v: Any) -> CellState:
    s = strip_cell(v)
    if not s:
        return "empty"
    try:
        n = float(s.replace(",", ""))
        if n == 0:
            return "zero"
        return "value"
    except ValueError:
        return "text"


def parse_number(v: Any) -> float | None:
    """Empty -> None; explicit 0 -> 0.0; invalid -> None."""
    s = strip_cell(v)
    if not s:
        return None
    try:
        return float(s.replace(",", ""))
    except ValueError:
        return None


def parse_count(v: Any) -> float:
    """For KPI sums: empty/invalid -> 0; explicit zero stays 0."""
    n = parse_number(v)
    return 0.0 if n is None else n


def sample_parts_sum(row: dict[str, Any]) -> float:
    return sum(
        parse_count(row.get(c))
        for c in (
            "preCancer",
            "Case Cancer Untreated",
            "Case Cancer Treated",
            "Control Healthy",
            "Healthy Treated",
        )
    )


def audit_sample_columns(row: dict[str, Any]) -> list[dict[str, str]]:
    """Flag empty vs zero vs Total mismatch (map KPI rules)."""
    issues: list[dict[str, str]] = []
    total = parse_number(row.get("Total Samples"))
    parts = sample_parts_sum(row)

    for col in SAMPLE_COUNT_COLS:
        raw = row.get(col)
        st = cell_state(raw)
        if st == "invalid":
            issues.append({"field": col, "code": "invalid_num", "msg": f"{col}: not a number ({raw!r})"})

    if total is None and parts > 0:
        issues.append({
            "field": "Total Samples",
            "code": "total_empty_parts",
            "msg": f"Total Samples empty but case/control sum={int(parts)}",
        })
    elif total is not None and parts > 0 and abs(total - parts) > max(2, total * 0.15):
        issues.append({
            "field": "Total Samples",
            "code": "total_mismatch",
            "msg": f"Total={int(total)} vs case/control sum={int(parts)}",
        })

    pid = strip_cell(row.get("Project ID"))
    if total == 0 and parts == 0 and pid:
        issues.append({
            "field": "Total Samples",
            "code": "all_counts_empty",
            "msg": "No sample counts (all empty/zero)",
        })
    return issues


def audit_text_gaps(row: dict[str, Any]) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    for col, fallbacks in TEXT_REQUIRED_WHEN_MISSING.items():
        if strip_cell(row.get(col)):
            continue
        fb_vals = [strip_cell(row.get(c)) for c in fallbacks if c in row]
        if any(fb_vals):
            issues.append({
                "field": col,
                "code": "text_gap",
                "msg": f"{col} empty but fallback filled: {', '.join(c for c in fallbacks if strip_cell(row.get(c)))}",
            })
        elif col == "Organ":
            issues.append({
                "field": col,
                "code": "organ_empty",
                "msg": "Organ empty — map uses Tissue/Detail fallback or Other",
            })
    disease = strip_cell(row.get("Disease"))
    if disease.lower() == "nan" or (not disease and strip_cell(row.get("Tumor Type")).lower() == "nan"):
        issues.append({
            "field": "Disease",
            "code": "nan_string",
            "msg": "Literal 'nan' in Disease/Tumor Type — treat as empty in UI",
        })
    return issues
