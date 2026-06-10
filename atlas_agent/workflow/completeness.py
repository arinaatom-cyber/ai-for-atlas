from __future__ import annotations

import re
from typing import Any

import pandas as pd

from atlas_agent.sources.projects_table import primary_project_id

# Колонки «Unified» / обязательные для зелёной строки в Excel
UNIFIED_COLUMNS = [
    "Platform MS (Unified)",
    "TMT Label (Unified)",
    "Normalization Strategy",
    "FASTA (Unified)",
    "FDR (Unified %)",
    "Result Files",
    "Quantification_Format",
]

OPTIONAL_UNIFIED = ["Z-Score Level", "Z-Score Scope", "FASTA Year"]

PATIENT_COLUMNS = [
    "Patients / donors",
    "preCancer",
    "Case Cancer Untreated",
    "Case Cancer Treated",
    "Control Healthy",
    "Healty trraeted",
    "Samples Used N",
    "Total Samples",
]


def _empty(val: Any) -> bool:
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return True
    s = str(val).strip().lower()
    return s in ("", "nan", "none", "—", "-", "not specified", "n/a")


def row_completeness(row: pd.Series) -> dict:
    missing = []
    filled = []
    for col in UNIFIED_COLUMNS:
        if col not in row.index:
            continue
        if _empty(row[col]):
            missing.append(col)
        else:
            filled.append(col)

    optional_missing = [
        c for c in OPTIONAL_UNIFIED if c in row.index and _empty(row[c])
    ]
    score = len(filled) / max(len(UNIFIED_COLUMNS), 1)

    if score >= 0.95 and not missing:
        status = "complete"  # аналог «зелёной» строки
    elif score >= 0.5:
        status = "partial"  # частично заполнено
    else:
        status = "todo"  # белая — нужно дочитать

    return {
        "status": status,
        "score_pct": round(100 * score, 1),
        "filled_unified": filled,
        "missing_unified": missing,
        "optional_missing": optional_missing,
    }


def patient_summary(row: pd.Series) -> dict:
    """Сводка по пациентам/образцам для статистики."""
    out: dict[str, Any] = {}
    for col in PATIENT_COLUMNS:
        if col in row.index and not _empty(row[col]):
            out[col] = str(row[col]).strip()

    n_patients = None
    raw = out.get("Patients / donors", "")
    if raw:
        nums = [int(x) for x in re.findall(r"\d+", raw.replace(",", ""))]
        if nums:
            n_patients = max(nums) if len(nums) == 1 else nums[0]

    try:
        n_samples = int(float(str(row.get("Samples Used N", "")).split(";")[0].strip()))
    except (ValueError, TypeError):
        n_samples = None

    design = str(row.get("Experimental Design", "") or "").lower()
    sample_type = str(row.get("Sample Type", "") or "").lower()

    level = "unknown"
    if n_patients and n_patients > 0 and "patient" in sample_type + design:
        level = "patient"
    elif "cell line" in sample_type:
        level = "cell_line"
    elif n_samples:
        level = "sample"

    return {
        "level": level,
        "n_patients_hint": n_patients,
        "n_samples_used": n_samples,
        "fields": out,
    }


def audit_table(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, r in df.iterrows():
        pid = primary_project_id(str(r.get("Project ID", "")))
        comp = row_completeness(r)
        pat = patient_summary(r)
        rows.append(
            {
                "project_id": pid,
                "status": comp["status"],
                "score_pct": comp["score_pct"],
                "missing": "; ".join(comp["missing_unified"]),
                "patient_level": pat["level"],
                "n_samples": pat["n_samples_used"],
            }
        )
    return pd.DataFrame(rows)
