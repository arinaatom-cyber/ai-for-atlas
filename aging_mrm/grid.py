"""Designed analysis grids: annotation (500) and core values (10 × 500)."""

from __future__ import annotations

import pandas as pd

from aging_mrm.core import core_sequences
from aging_mrm.normalize import age_bin

ANNOTATION_COLUMNS = [
    "patient_id",
    "channel_id",
    "cohort",
    "sex",
    "age",
    "age_bin",
    "in_srm",
    "srm_sex",
    "srm_age",
    "sex_match",
    "age_match",
    "delivery_batch",
    "trypsin_batch",
    "trypsin_brand",
    "std_mix",
    "bmi",
    "id_duble",
]

VALUES_COLUMNS = [
    "patient_id",
    "channel_id",
    "peptide_sequence",
    "intensity",
    "log2_intensity",
    "protein",
    "uniprot",
    "peptide_index",
    "cohort",
    "sex",
    "age",
    "age_bin",
    "present",
    "missing_reason",
    "in_srm",
    "srm_age",
    "age_match",
    "sex_match",
    "delivery_batch",
    "trypsin_batch",
    "std_mix",
]


def _flag_match(left: pd.Series, right: pd.Series, *, numeric: bool = False) -> pd.Series:
    if numeric:
        ok = (left.notna() & right.notna() & ((left - right).abs() <= 1))
        both = left.notna() & right.notna()
        return pd.Series(
            ["1" if a else ("0" if b else "") for a, b in zip(ok.tolist(), both.tolist())],
            index=left.index,
        )
    left_s = left.fillna("").astype(str)
    right_s = right.fillna("").astype(str)
    both = (left_s != "") & (right_s != "")
    ok = both & (left_s == right_s)
    return pd.Series(
        ["1" if a else ("0" if b else "") for a, b in zip(ok.tolist(), both.tolist())],
        index=left.index,
    )


def assemble_observed(
    patients: pd.DataFrame,
    channels: pd.DataFrame,
    intensities: pd.DataFrame,
) -> pd.DataFrame:
    """Observed peptide intensities with clinical age/sex as source of truth."""
    clinical = patients.drop_duplicates("patient_id", keep="first")
    merged = intensities.merge(channels, on=["channel_id", "patient_id"], how="left")
    merged = merged.merge(clinical, on="patient_id", how="left", suffixes=("", "_clinical"))
    if "cohort" in merged.columns:
        merged["cohort"] = merged["cohort"].where(
            merged["cohort"].notna() & (merged["cohort"].astype(str) != ""),
            merged.get("cohort_from_name"),
        )
    else:
        merged["cohort"] = merged.get("cohort_from_name")
    merged["age_bin"] = merged["age"].map(age_bin)
    merged["sex_match"] = _flag_match(merged["sex"], merged["srm_sex"])
    merged["age_match"] = _flag_match(merged["age"], merged["srm_age"], numeric=True)
    merged["in_srm"] = 1
    merged["present"] = merged["intensity"].notna().map({True: 1, False: 0})
    merged["missing_reason"] = ""
    merged.loc[merged["present"] == 0, "missing_reason"] = "no_intensity"
    cols = [
        "patient_id",
        "channel_id",
        "peptide_sequence",
        "intensity",
        "log2_intensity",
        "uniprot",
        "protein",
        "peptide_index",
        "cohort",
        "sex",
        "age",
        "age_bin",
        "present",
        "missing_reason",
        "srm_sex",
        "srm_age",
        "srm_age_group",
        "sex_match",
        "age_match",
        "delivery_batch",
        "trypsin_batch",
        "trypsin_brand",
        "std_mix",
        "bmi",
        "pathology",
        "biomaterial",
        "id_duble",
        "sample_id",
        "srm_id",
        "plate",
        "position",
    ]
    for col in cols:
        if col not in merged.columns:
            merged[col] = pd.NA
    return merged[cols]


def assemble_annotation(patients: pd.DataFrame, channels: pd.DataFrame) -> pd.DataFrame:
    """One row per patient: channel if measured, clinical age/sex always."""
    clinical = patients.drop_duplicates("patient_id", keep="first")
    keep_ch = [
        col
        for col in (
            "patient_id",
            "channel_id",
            "srm_sex",
            "srm_age",
            "delivery_batch",
            "trypsin_batch",
            "trypsin_brand",
            "std_mix",
            "id_duble",
        )
        if col in channels.columns
    ]
    out = clinical.merge(channels[keep_ch], on="patient_id", how="left")
    out["in_srm"] = out["channel_id"].notna() & (out["channel_id"].astype(str).str.strip() != "")
    out["in_srm"] = out["in_srm"].astype(int)
    out["age_bin"] = out["age"].map(age_bin)
    out["sex_match"] = _flag_match(out["sex"], out.get("srm_sex", pd.Series("", index=out.index)))
    out["age_match"] = _flag_match(
        out["age"], out.get("srm_age", pd.Series(index=out.index, dtype=float)), numeric=True
    )
    for col in ANNOTATION_COLUMNS:
        if col not in out.columns:
            out[col] = pd.NA
    return out[ANNOTATION_COLUMNS].sort_values(["cohort", "age_bin", "patient_id"]).reset_index(drop=True)


def assemble_values_5000(
    patients: pd.DataFrame,
    channels: pd.DataFrame,
    peptides: pd.DataFrame,
    intensities: pd.DataFrame,
) -> pd.DataFrame:
    """Complete designed grid: core peptides × every clinical patient."""
    sequences = core_sequences(peptides)
    pep = peptides.drop_duplicates("peptide_sequence")
    pep = pep[pep["peptide_sequence"].isin(sequences)].copy()
    clinical = patients.drop_duplicates("patient_id", keep="first")
    if pep.empty or clinical.empty:
        return pd.DataFrame(columns=VALUES_COLUMNS)
    order = {seq: i for i, seq in enumerate(sequences)}
    pep["_ord"] = pep["peptide_sequence"].map(order)
    pep = pep.sort_values("_ord")
    clinical = patients.drop_duplicates("patient_id", keep="first")
    grid = clinical.merge(pep, how="cross")
    ch_keep = [
        col
        for col in (
            "patient_id",
            "channel_id",
            "srm_sex",
            "srm_age",
            "delivery_batch",
            "trypsin_batch",
            "trypsin_brand",
            "std_mix",
        )
        if col in channels.columns
    ]
    grid = grid.merge(channels[ch_keep], on="patient_id", how="left")
    obs = intensities[
        intensities["peptide_sequence"].isin(sequences)
    ][["patient_id", "peptide_sequence", "intensity", "log2_intensity"]]
    grid = grid.merge(obs, on=["patient_id", "peptide_sequence"], how="left")
    grid["age_bin"] = grid["age"].map(age_bin)
    has_channel = grid["channel_id"].notna() & (grid["channel_id"].astype(str).str.strip() != "")
    grid["in_srm"] = has_channel.astype(int)
    grid["present"] = grid["intensity"].notna().astype(int)
    grid["missing_reason"] = ""
    grid.loc[~has_channel, "missing_reason"] = "no_srm_channel"
    grid.loc[has_channel & (grid["present"] == 0), "missing_reason"] = "no_intensity"
    grid["sex_match"] = _flag_match(grid["sex"], grid.get("srm_sex", pd.Series("", index=grid.index)))
    grid["age_match"] = _flag_match(
        grid["age"], grid.get("srm_age", pd.Series(index=grid.index, dtype=float)), numeric=True
    )
    for col in VALUES_COLUMNS:
        if col not in grid.columns:
            grid[col] = pd.NA
    return (
        grid.sort_values(["cohort", "age_bin", "patient_id", "_ord"])[VALUES_COLUMNS]
        .reset_index(drop=True)
    )
