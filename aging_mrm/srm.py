from __future__ import annotations

import math
from pathlib import Path

import pandas as pd

from aging_mrm import normalize as n
from aging_mrm.paths import COHORT_100, COHORT_50, COHORT_350
from aging_mrm.tables import read_csv_raw

ANNOT_WIDTH = 11
META_LABELS = {
    "donor id": "patient_id",
    "id duble": "id_duble",
    "пол": "srm_sex_raw",
    "возраст": "srm_age_raw",
    "group": "srm_age_group_raw",
    "sample delivery batch": "delivery_batch",
    "trypsinolysis  batch": "trypsin_batch",
    "trypsinolysis batch": "trypsin_batch",
    "trypsin promega/molecta": "trypsin_brand",
    "std mix": "std_mix",
}

STAT_COLS = {"av", "std", "cv"}
PEPTIDE_COLUMNS = [
    "peptide_index",
    "peptide_sequence",
    "uniprot",
    "protein",
    "panel",
    "role",
    "panel_detail",
    "sample_coverage",
    "n_samples_for_analysis",
    "n_samples_with_hits",
]


def infer_cohort(channel_id: str) -> str:
    name = channel_id.strip()
    if name.upper().startswith("OY_HPL"):
        return COHORT_350
    if name.upper().startswith("OY") and name.upper().endswith("_AV"):
        return COHORT_100
    if "nm" in name.lower():
        return COHORT_50
    return ""


def _cell(raw: pd.DataFrame, row: int, col: int):
    if row >= len(raw.index) or col >= len(raw.columns):
        return None
    return raw.iat[row, col]


def parse_srm_matrix(path: Path) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    raw = read_csv_raw(path)
    if raw.empty:
        raise ValueError(f"Empty SRM table: {path}")

    header = [_blank_to_text(_cell(raw, 0, col)) for col in range(len(raw.columns))]
    sample_cols = [
        col
        for col in range(ANNOT_WIDTH, len(header))
        if header[col] and header[col].strip().lower() not in STAT_COLS
    ]

    meta: dict[str, list] = {}
    peptide_start = 1
    for row in range(1, min(len(raw.index), 20)):
        label = n.as_text(_cell(raw, row, 0)).lower()
        mapped = META_LABELS.get(label)
        if not mapped:
            first = _cell(raw, row, 0)
            if n.parse_number(first) is not None or (
                n.as_text(_cell(raw, row, 1)) and not mapped
            ):
                peptide_start = row
                break
            continue
        meta[mapped] = [_cell(raw, row, col) for col in sample_cols]

    channels = []
    for i, col in enumerate(sample_cols):
        channel_id = header[col]
        pid = n.patient_id(meta.get("patient_id", [None] * len(sample_cols))[i])
        srm_age = n.parse_age(meta.get("srm_age_raw", [None] * len(sample_cols))[i])
        srm_sex = n.normalize_sex(meta.get("srm_sex_raw", [None] * len(sample_cols))[i])
        channels.append(
            {
                "channel_id": channel_id,
                "channel_index": i,
                "patient_id": pid,
                "id_duble": n.as_text(meta.get("id_duble", [None] * len(sample_cols))[i]),
                "cohort_from_name": infer_cohort(channel_id),
                "srm_sex": srm_sex,
                "srm_age": srm_age,
                "srm_age_bin": n.age_bin(srm_age),
                "srm_age_group": n.normalize_age_group_label(
                    meta.get("srm_age_group_raw", [None] * len(sample_cols))[i]
                ),
                "delivery_batch": n.as_text(
                    meta.get("delivery_batch", [None] * len(sample_cols))[i]
                ),
                "trypsin_batch": n.as_text(
                    meta.get("trypsin_batch", [None] * len(sample_cols))[i]
                ),
                "trypsin_brand": n.as_text(
                    meta.get("trypsin_brand", [None] * len(sample_cols))[i]
                ),
                "std_mix": n.as_text(meta.get("std_mix", [None] * len(sample_cols))[i]),
            }
        )
    channels_df = pd.DataFrame(channels)

    peptides = []
    keep_rows: list[int] = []
    for row in range(peptide_start, len(raw.index)):
        seq = n.as_text(_cell(raw, row, 1))
        if not seq:
            continue
        keep_rows.append(row)
        peptides.append(
            {
                "peptide_index": n.as_text(_cell(raw, row, 0)),
                "peptide_sequence": seq,
                "uniprot": n.as_text(_cell(raw, row, 3)),
                "protein": n.as_text(_cell(raw, row, 4)),
                "panel": n.as_text(_cell(raw, row, 5)),
                "role": n.as_text(_cell(raw, row, 6)),
                "panel_detail": n.as_text(_cell(raw, row, 7)),
                "sample_coverage": n.as_text(_cell(raw, row, 8)),
                "n_samples_for_analysis": n.parse_number(_cell(raw, row, 9)),
                "n_samples_with_hits": n.parse_number(_cell(raw, row, 10)),
            }
        )
    peptides_df = pd.DataFrame(peptides, columns=PEPTIDE_COLUMNS)

    if not keep_rows:
        intensities_df = pd.DataFrame(
            columns=[
                "channel_id",
                "patient_id",
                "peptide_index",
                "peptide_sequence",
                "uniprot",
                "protein",
                "intensity",
                "log2_intensity",
            ]
        )
        return channels_df, peptides_df, intensities_df

    wide = raw.iloc[keep_rows, sample_cols].copy()
    wide.columns = [header[col] for col in sample_cols]
    wide = wide.apply(lambda col: col.map(n.parse_number))
    wide.insert(0, "peptide_index", peptides_df["peptide_index"].to_list())
    wide.insert(1, "peptide_sequence", peptides_df["peptide_sequence"].to_list())
    wide.insert(2, "uniprot", peptides_df["uniprot"].to_list())
    wide.insert(3, "protein", peptides_df["protein"].to_list())
    intensities_df = wide.melt(
        id_vars=["peptide_index", "peptide_sequence", "uniprot", "protein"],
        var_name="channel_id",
        value_name="intensity",
    )
    channel_patient = channels_df.set_index("channel_id")["patient_id"]
    intensities_df["patient_id"] = intensities_df["channel_id"].map(channel_patient)
    intensities_df["log2_intensity"] = intensities_df["intensity"].map(
        lambda value: math.log2(value) if isinstance(value, (int, float)) and value > 0 else None
    )
    intensities_df = intensities_df[
        [
            "patient_id",
            "channel_id",
            "peptide_index",
            "peptide_sequence",
            "uniprot",
            "protein",
            "intensity",
            "log2_intensity",
        ]
    ]
    return channels_df, peptides_df, intensities_df


def _blank_to_text(value) -> str:
    return n.as_text(value)
