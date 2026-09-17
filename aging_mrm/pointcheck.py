from __future__ import annotations

import pandas as pd

from aging_mrm.grid import assemble_annotation


def _status(row: pd.Series) -> str:
    parts: list[str] = []
    if int(row.get("in_srm") or 0) != 1:
        parts.append("no_srm_channel")
    if str(row.get("age_match", "")) == "0":
        parts.append("age_mismatch")
    if str(row.get("sex_match", "")) == "0":
        parts.append("sex_mismatch")
    if row.get("age") is None or (isinstance(row.get("age"), float) and pd.isna(row.get("age"))):
        parts.append("age_missing")
    return "+".join(parts) if parts else "ok"


def intensity_coverage(intensities: pd.DataFrame) -> pd.DataFrame:
    if intensities.empty:
        return pd.DataFrame(columns=["patient_id", "n_peptides", "n_measured"])
    grouped = intensities.groupby("patient_id", as_index=False).agg(
        n_peptides=("peptide_sequence", "nunique"),
        n_measured=("intensity", lambda s: int(s.notna().sum())),
    )
    return grouped


def pointcheck(patients: pd.DataFrame, channels: pd.DataFrame, intensities: pd.DataFrame) -> pd.DataFrame:
    table = assemble_annotation(patients, channels)
    cov = intensity_coverage(intensities)
    table = table.merge(cov, on="patient_id", how="left")
    table["n_peptides"] = table["n_peptides"].fillna(0).astype(int)
    table["n_measured"] = table["n_measured"].fillna(0).astype(int)
    table["status"] = table.apply(_status, axis=1)
    cols = [
        "patient_id",
        "channel_id",
        "cohort",
        "sex",
        "age",
        "age_bin",
        "srm_sex",
        "srm_age",
        "sex_match",
        "age_match",
        "in_srm",
        "n_peptides",
        "n_measured",
        "status",
    ]
    return table[cols].sort_values(["cohort", "patient_id"]).reset_index(drop=True)


ERROR_TEXT = {
    "age_mismatch": "Возраст в шапке SRM не совпадает с donor_age листа когорты; в таблице используется SRM.",
    "no_srm_channel": "Пациент есть в клинике, канала в матрице SRM нет.",
    "sex_mismatch": "Пол в SRM не совпадает с клиникой.",
    "age_missing": "В клинике нет возраста.",
}


def mismatches_only(point: pd.DataFrame) -> pd.DataFrame:
    return point.loc[point["status"] != "ok"].reset_index(drop=True)


def errors_only(point: pd.DataFrame) -> pd.DataFrame:
    fail = mismatches_only(point)
    if fail.empty:
        return pd.DataFrame(
            columns=[
                "тип_ошибки",
                "пациент",
                "канал",
                "когорта",
                "пол",
                "возраст_клиника",
                "возраст_SRM",
                "пояснение",
            ]
        )
    rows = []
    for _, row in fail.iterrows():
        status = str(row["status"])
        rows.append(
            {
                "тип_ошибки": status,
                "пациент": row["patient_id"],
                "канал": row["channel_id"],
                "когорта": row["cohort"],
                "пол": row["sex"],
                "возраст_клиника": row["age"],
                "возраст_SRM": row["srm_age"],
                "пояснение": " ".join(ERROR_TEXT.get(part, part) for part in status.split("+")),
            }
        )
    return (
        pd.DataFrame(rows)
        .sort_values(["тип_ошибки", "когорта", "пациент"])
        .reset_index(drop=True)
    )
