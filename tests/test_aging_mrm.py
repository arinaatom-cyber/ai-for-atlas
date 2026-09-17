"""Aging MRM-SIS: patient × channel × intensity."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from aging_mrm.normalize import age_bin, normalize_age_group_label, normalize_sex, parse_number, patient_id
from aging_mrm.pipeline import build_aging_mrm
from aging_mrm.srm import infer_cohort, parse_srm_matrix

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "aging_mrm"


def test_normalize_helpers():
    assert patient_id(925.0) == "925"
    assert normalize_sex("муж", 1) == "male"
    assert normalize_sex("ж") == "female"
    assert normalize_sex("2") == "female"
    assert age_bin(90) == "75+"
    assert age_bin(24) == "18-24"
    assert age_bin(float("nan")) == ""
    assert parse_number("19,5") == 19.5
    assert normalize_age_group_label("75 лет и старше") == "75+"


def test_infer_cohort_from_channel_name():
    assert infer_cohort("OY1_AV") == "100_2024"
    assert infer_cohort("101 nM") == "50_2025"
    assert infer_cohort("OY_HPL151") == "350_2025"


def test_srm_matrix_has_patient_channel_intensity():
    channels, peptides, intensities = parse_srm_matrix(FIXTURE_DIR / "SRM data.csv")
    assert list(channels["channel_id"]) == ["OY1_AV", "101 nM", "OY_HPL151"]
    assert list(channels["patient_id"]) == ["925", "929", "37"]
    assert len(peptides) == 2
    assert set(intensities.columns) >= {
        "patient_id",
        "channel_id",
        "peptide_sequence",
        "intensity",
    }
    igkc = intensities[
        (intensities["patient_id"] == "925")
        & (intensities["peptide_sequence"] == "DSTYSLSSTLTLSK")
    ]
    assert float(igkc["intensity"].iloc[0]) == 100.0
    missing = intensities[
        (intensities["patient_id"] == "37")
        & (intensities["peptide_sequence"] == "GPSVFPLAPSSK")
    ]
    assert pd.isna(missing["intensity"].iloc[0])


def test_build_pointcheck_clinical_age(tmp_path: Path):
    tables = build_aging_mrm(csv_dir=FIXTURE_DIR, out_dir=tmp_path, write=True)
    long_table = tables.long_table
    assert len(long_table) == 6
    row_925 = long_table[long_table["patient_id"] == "925"].iloc[0]
    assert row_925["channel_id"] == "OY1_AV"
    assert row_925["age"] == 35
    assert row_925["age_bin"] == "25-44"
    assert row_925["srm_age"] == 35
    assert row_925["age_match"] == "0"
    assert row_925["sex_match"] == "1"
    assert tables.qc["n_age_mismatch_patients"] == 1
    check = tables.annotation
    assert len(check) == 3
    assert set(check["status"]) == {"ok", "age_mismatch"}
    assert check.loc[check["patient_id"] == "925", "status"].iloc[0] == "age_mismatch"
    assert check.loc[check["patient_id"] == "929", "status"].iloc[0] == "ok"
    assert len(tables.mismatches) == 1
    assert not (tmp_path / "values_5000.csv").exists()
    assert not (tmp_path / "errors_only.csv").exists()
    assert not (tmp_path / "pointcheck_mismatches.csv").exists()
    big = tables.big
    assert list(big.columns[:4]) == ["channel_id", "patient_id", "peptide_sequence", "intensity"]
    assert len(big) == 5
    assert int(big["intensity"].notna().sum()) == 5
    assert tables.assembly_check["ok"] is True
    igkc = big[
        (big["channel_id"] == "OY1_AV") & (big["peptide_sequence"] == "DSTYSLSSTLTLSK")
    ].iloc[0]
    assert igkc["patient_id"] == "925"
    assert float(igkc["intensity"]) == 100.0
    assert igkc["age"] == 35
    assert (tmp_path / "channel_patient_intensity.csv").is_file()
