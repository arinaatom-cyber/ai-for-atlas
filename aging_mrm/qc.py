"""Quality checks: pointwise channel–patient–age, not a 5000 grid."""

from __future__ import annotations

from typing import Any

import pandas as pd


def _ids(frame: pd.DataFrame, column: str) -> set[str]:
    if column not in frame.columns or frame.empty:
        return set()
    return {str(value) for value in frame[column].dropna().astype(str) if str(value).strip()}


def qc_report(
    patients: pd.DataFrame,
    channels: pd.DataFrame,
    peptides: pd.DataFrame,
    intensities: pd.DataFrame,
    long_table: pd.DataFrame,
    annotation: pd.DataFrame | None = None,
    pointcheck: pd.DataFrame | None = None,
) -> dict[str, Any]:
    patient_ids = _ids(patients, "patient_id")
    channel_patients = _ids(channels, "patient_id")
    missing_intensity = int(intensities["intensity"].isna().sum()) if not intensities.empty else 0
    measured = int(intensities["intensity"].notna().sum()) if not intensities.empty else 0

    source = pointcheck if pointcheck is not None and not pointcheck.empty else annotation
    age_mismatch = pd.DataFrame()
    sex_mismatch = pd.DataFrame()
    status_counts: dict[str, int] = {}
    if source is not None and not source.empty:
        if "status" in source.columns:
            status_counts = source["status"].value_counts().to_dict()
        cols_age = [c for c in ("patient_id", "channel_id", "age", "srm_age", "status") if c in source.columns]
        cols_sex = [c for c in ("patient_id", "channel_id", "sex", "srm_sex", "status") if c in source.columns]
        age_mismatch = (
            source.loc[source["age_match"].astype(str) == "0", cols_age]
            .drop_duplicates("patient_id")
            .sort_values("patient_id")
        )
        sex_mismatch = (
            source.loc[source["sex_match"].astype(str) == "0", cols_sex]
            .drop_duplicates("patient_id")
            .sort_values("patient_id")
        )

    by_cohort = {}
    if "cohort" in patients.columns and not patients.empty:
        by_cohort = patients.groupby("cohort")["patient_id"].nunique().to_dict()

    by_age_bin = {}
    if not patients.empty and "age_bin" in patients.columns:
        by_age_bin = patients.groupby("age_bin")["patient_id"].nunique().to_dict()

    return {
        "rule": "точечная проверка: один пациент — один канал — возраст из клиники",
        "n_patients": int(patients["patient_id"].nunique()) if not patients.empty else 0,
        "n_patients_by_cohort": {str(k): int(v) for k, v in by_cohort.items()},
        "n_patients_by_age_bin": {str(k): int(v) for k, v in by_age_bin.items()},
        "n_channels": int(len(channels)),
        "n_peptides": int(len(peptides)),
        "n_intensity_rows": int(len(intensities)),
        "n_measured": measured,
        "n_missing_intensity": missing_intensity,
        "n_long_rows": int(len(long_table)),
        "n_pointcheck_rows": int(len(pointcheck)) if pointcheck is not None else 0,
        "n_ok": int(status_counts.get("ok", 0)),
        "n_fail": int(sum(v for k, v in status_counts.items() if k != "ok")),
        "status_counts": {str(k): int(v) for k, v in status_counts.items()},
        "patients_not_in_srm": sorted(patient_ids - channel_patients),
        "srm_patients_not_in_clinical": sorted(channel_patients - patient_ids),
        "n_age_mismatch_patients": int(len(age_mismatch)),
        "age_mismatches": age_mismatch.to_dict(orient="records"),
        "n_sex_mismatch_patients": int(len(sex_mismatch)),
        "sex_mismatches": sex_mismatch.to_dict(orient="records"),
        "duplicate_channel_ids": int(channels["channel_id"].duplicated().sum()) if not channels.empty else 0,
        "channels_without_patient": int((channels["patient_id"] == "").sum()) if not channels.empty else 0,
    }
