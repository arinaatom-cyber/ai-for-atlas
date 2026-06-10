from __future__ import annotations

import re
from typing import Any

import pandas as pd

from atlas_agent.workflow.completeness import patient_summary


def _classify_design(row: pd.Series) -> str:
    blob = " ".join(
        str(row.get(c, "") or "")
        for c in ("Experimental Design", "Sample Type", "Disease", "Short Description")
    ).lower()
    if re.search(r"paired|longitudinal|before.?after|matched", blob):
        return "paired"
    if re.search(r"time\s*course|longitudinal|days?\s*\d", blob):
        return "time_course"
    if re.search(r"pan.?organ|multi.?organ|≥\s*8|multiple organs", blob):
        return "pan_organ"
    if "cell line" in blob:
        return "cell_line"
    if re.search(r"case.?control|tumor|normal|cancer|healthy", blob):
        return "case_control"
    return "other"


def build_stats_plan(row: pd.Series) -> dict[str, Any]:
    """Структурированный стат-план + прозрачный R-шаблон."""
    design_type = _classify_design(row)
    pat = patient_summary(row)
    n = pat.get("n_samples_used")

    test = "limma"
    blocking = []
    warnings: list[str] = []

    if design_type == "paired":
        test = "limma_paired"
        blocking.append("patient_id")
    elif design_type == "time_course":
        test = "mixed_model_or_limma_time"
        blocking.append("patient_id")
    elif design_type == "pan_organ":
        test = "limma_with_organ_covariate"
        warnings.append("Не объединять органы в один DE без covariate Organ")
    elif design_type == "cell_line":
        test = "limma"
        blocking.append("cell_line")
    elif n and n < 6:
        test = "wilcoxon_or_limma_small_n"
        warnings.append(f"Мало образцов (n={n}) — осторожно с множественными сравнениями")

    norm = str(row.get("Normalization Strategy", "") or "").strip()
    if not norm or norm.lower() in ("nan", "not specified"):
        warnings.append("Normalization Strategy пуст — извлечь из статьи перед DE")

    pid = str(row.get("Project ID", "")).strip()
    rf = str(row.get("Result Files", "") or "").strip().split("\n")[0]

    r_template = f"""# Stats plan for {pid}
# Design: {design_type} | Patient level: {pat['level']}
library(limma)

# 1) Load protein matrix from Result File: {rf[:80]}
# mat <- read_protein_matrix("tmt-projects/Projects/{pid}/...")

# 2) Filter: >=70% valid values per comparison group
# mat_f <- filter_by_group_presence(mat, groups, min_frac=0.7)

# 3) Log2 if not already (check Normalization Strategy in sheet)
# norm_in_sheet: {norm[:100] if norm else 'MISSING'}

# 4) Design matrix
# design <- model.matrix(~ 0 + group + {' + '.join(blocking) if blocking else 'group'})

# 5) Test: {test}
# fit <- lmFit(mat_f, design)
# fit2 <- eBayes(contrasts.fit(fit, contrast_matrix))
# topTable(fit2, adjust.method="BH", number=Inf)

# 6) Patient-level: aggregate technical replicates to patient before DE if needed
"""

    return {
        "project_id": pid,
        "design_type": design_type,
        "patient_level": pat["level"],
        "n_samples_used": n,
        "n_patients_hint": pat.get("n_patients_hint"),
        "test": test,
        "multiple_testing": "FDR_BH",
        "blocking_factors": blocking,
        "normalization_sheet": norm,
        "software": ["R", "limma"],
        "warnings": warnings,
        "r_template": r_template,
    }
