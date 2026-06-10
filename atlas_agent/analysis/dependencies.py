from __future__ import annotations

import pandas as pd

# Логические связи между колонками таблицы (для отчёта и проверок)
COLUMN_GROUPS = {
    "идентификация": ["Database", "Project ID", "PMID", "Title", "URL"],
    "дизайн_образцов": [
        "Total Samples",
        "Samples Original N",
        "Samples Used N",
        "Experimental Design",
        "Sample Type",
        "Tissue",
        "Organ",
        "Disease",
    ],
    "tmt_плекс": [
        "TMT Label (Unified)",
        "TMT Channels Used",
        "TMT Channels Comparison",
        "TMT Additional Channels",
        "Platform MS (Unified)",
    ],
    "нормализация_квантификация": [
        "Normalization Strategy",
        "Z-Score Level",
        "Z-Score Scope",
        "Quantification_Format",
        "Proteins Quantified",
        "FDR (Unified %)",
    ],
    "база_белков": ["FASTA (Unified)", "FASTA Year", "Modifications"],
    "файлы": ["Result Files"],
}


def column_coverage(df: pd.DataFrame) -> dict:
    out = {}
    for group, cols in COLUMN_GROUPS.items():
        present = [c for c in cols if c in df.columns]
        missing = [c for c in cols if c not in df.columns]
        filled = {}
        for c in present:
            s = df[c].astype(str).str.strip()
            nonempty = s[~s.isin(["", "nan", "None", "—", "-", "Not specified"])]
            filled[c] = {
                "filled_rows": int(len(nonempty)),
                "total_rows": int(len(df)),
                "pct": round(100 * len(nonempty) / max(len(df), 1), 1),
            }
        out[group] = {"present": present, "missing": missing, "columns": filled}
    return out


def dependency_rules(df: pd.DataFrame) -> list[dict]:
    """Правила-связи: если заполнено A, ожидается B."""
    rules = []
    if "TMT Label (Unified)" not in df.columns:
        return rules

    tmt_mask = df["TMT Label (Unified)"].astype(str).str.contains("TMT", case=False, na=False)
    tmt_n = int(tmt_mask.sum())

    if "Normalization Strategy" in df.columns:
        norm_filled = df.loc[tmt_mask, "Normalization Strategy"].astype(str).str.strip()
        empty_norm = norm_filled.isin(["", "nan", "Not specified", "—", "-"])
        rules.append(
            {
                "rule": "TMT-проекты должны иметь Normalization Strategy",
                "violations": int(empty_norm.sum()),
                "scope": tmt_n,
            }
        )

    if "Result Files" in df.columns:
        rf = df.loc[tmt_mask, "Result Files"].astype(str).str.strip()
        empty_rf = rf.isin(["", "nan", "—"])
        rules.append(
            {
                "rule": "TMT-проекты должны иметь Result Files",
                "violations": int(empty_rf.sum()),
                "scope": tmt_n,
            }
        )

    if "Organ" in df.columns and "Tissue" in df.columns:
        both = df["Organ"].astype(str).str.strip().ne("") & df["Tissue"].astype(str).str.strip().ne("")
        rules.append(
            {
                "rule": "Organ и Tissue согласованы (оба заполнены)",
                "violations": int((~both).sum()),
                "scope": int(len(df)),
            }
        )

    return rules


def normalization_landscape(df: pd.DataFrame) -> dict:
    if "Normalization Strategy" not in df.columns:
        return {}
    s = df["Normalization Strategy"].fillna("").astype(str).str.strip()
    s = s.replace({"": "(пусто)", "Not specified": "(не указано)", "—": "(не указано)"})
    counts = s.value_counts().head(25)
    return {k: int(v) for k, v in counts.items()}
