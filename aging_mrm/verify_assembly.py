from __future__ import annotations

from typing import Any

import pandas as pd

from aging_mrm.normalize import parse_number

BIG_COLUMNS = [
    "channel_id",
    "patient_id",
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
    "delivery_batch",
    "trypsin_batch",
    "trypsin_brand",
    "std_mix",
]


def to_big_table(long_table: pd.DataFrame) -> pd.DataFrame:
    out = long_table.copy()
    if "intensity" in out.columns:
        out = out.loc[out["intensity"].notna()].copy()
    for col in BIG_COLUMNS:
        if col not in out.columns:
            out[col] = pd.NA
    sort_cols = [c for c in ("cohort", "patient_id", "peptide_index") if c in out.columns]
    return out[BIG_COLUMNS].sort_values(sort_cols).reset_index(drop=True)


def _key(frame: pd.DataFrame) -> pd.Series:
    return frame["channel_id"].astype(str) + "|" + frame["peptide_sequence"].astype(str)


def verify_assembly(
    big: pd.DataFrame,
    *,
    channels: pd.DataFrame,
    peptides: pd.DataFrame,
    intensities: pd.DataFrame,
    patients: pd.DataFrame,
) -> dict[str, Any]:
    errors: list[dict[str, Any]] = []

    if big.empty:
        errors.append({"code": "empty_file", "detail": "big table has 0 rows"})
        return _pack(errors, big, channels, peptides)

    for col in ("channel_id", "patient_id", "peptide_sequence", "intensity"):
        if col not in big.columns:
            errors.append({"code": "missing_column", "detail": col})

    if errors:
        return _pack(errors, big, channels, peptides)

    measured = intensities.loc[intensities["intensity"].notna()].copy() if not intensities.empty else intensities
    expected_n = int(len(measured))
    if len(big) != expected_n:
        errors.append(
            {
                "code": "row_count",
                "detail": f"got {len(big)}, expected measured intensities={expected_n}",
            }
        )

    dups = big[_key(big).duplicated(keep=False)]
    if not dups.empty:
        errors.append(
            {
                "code": "duplicate_channel_peptide",
                "n": int(dups.shape[0]),
                "examples": dups[["channel_id", "patient_id", "peptide_sequence"]].head(10).to_dict("records"),
            }
        )

    blank_ch = big["channel_id"].isna() | (big["channel_id"].astype(str).str.strip() == "")
    blank_pt = big["patient_id"].isna() | (big["patient_id"].astype(str).str.strip() == "")
    if blank_ch.any():
        errors.append({"code": "empty_channel_id", "n": int(blank_ch.sum())})
    if blank_pt.any():
        errors.append({"code": "empty_patient_id", "n": int(blank_pt.sum())})

    ch_map = channels.drop_duplicates("channel_id").set_index("channel_id")["patient_id"].astype(str)
    got_map = big.drop_duplicates("channel_id").set_index("channel_id")["patient_id"].astype(str)
    mismatches = []
    for channel_id, patient_id in got_map.items():
        expected = ch_map.get(channel_id)
        if expected is None:
            mismatches.append({"code": "channel_not_in_srm", "channel_id": str(channel_id)})
        elif str(expected) != str(patient_id):
            mismatches.append(
                {
                    "code": "channel_patient_mismatch",
                    "channel_id": str(channel_id),
                    "patient_id_file": str(patient_id),
                    "patient_id_srm": str(expected),
                }
            )
        if len(mismatches) >= 20:
            break
    errors.extend(mismatches)

    clinical = set(patients["patient_id"].astype(str))
    unknown = sorted(set(big["patient_id"].astype(str)) - clinical)
    if unknown:
        errors.append({"code": "patient_not_in_clinical", "patients": unknown[:20], "n": len(unknown)})

    src = measured.copy()
    src["_k"] = _key(src)
    file_ = big.copy()
    file_["_k"] = _key(file_)
    merged = file_[["_k", "intensity"]].merge(
        src[["_k", "intensity"]],
        on="_k",
        how="outer",
        suffixes=("_file", "_src"),
        indicator=True,
    )
    missing_keys = merged.loc[merged["_merge"] == "right_only", "_k"].astype(str).tolist()
    extra_keys = merged.loc[merged["_merge"] == "left_only", "_k"].astype(str).tolist()
    if missing_keys:
        errors.append({"code": "missing_keys_vs_srm", "n": len(missing_keys), "examples": missing_keys[:10]})
    if extra_keys:
        errors.append({"code": "extra_keys_vs_srm", "n": len(extra_keys), "examples": extra_keys[:10]})

    both = merged.loc[merged["_merge"] == "both"]
    bad = []
    for key, vf, vs in zip(both["_k"], both["intensity_file"], both["intensity_src"]):
        a = parse_number(vf)
        b = parse_number(vs)
        if a is None and b is None:
            continue
        if a is None or b is None or abs(float(a) - float(b)) > max(1e-6, 1e-8 * abs(float(b))):
            bad.append({"key": str(key), "file": a, "srm": b})
            if len(bad) >= 20:
                break
    if bad:
        errors.append({"code": "intensity_value_mismatch", "n": len(bad), "examples": bad})

    age_missing = int(big["age"].isna().sum()) if "age" in big.columns else len(big)
    if age_missing:
        errors.append({"code": "clinical_age_missing", "n": age_missing})
    sex_missing = int((big["sex"].fillna("").astype(str).str.strip() == "").sum()) if "sex" in big.columns else 0
    if sex_missing:
        errors.append({"code": "clinical_sex_missing", "n": sex_missing})

    return _pack(errors, big, channels, peptides, expected_rows=expected_n)


def _pack(
    errors: list[dict[str, Any]],
    big: pd.DataFrame,
    channels: pd.DataFrame,
    peptides: pd.DataFrame,
    expected_rows: int | None = None,
) -> dict[str, Any]:
    n_measured = int(big["intensity"].notna().sum()) if not big.empty and "intensity" in big.columns else 0
    return {
        "ok": len(errors) == 0,
        "n_errors": len(errors),
        "n_rows": int(len(big)),
        "n_channels": int(big["channel_id"].nunique()) if not big.empty and "channel_id" in big.columns else 0,
        "n_patients": int(big["patient_id"].nunique()) if not big.empty and "patient_id" in big.columns else 0,
        "n_peptides": int(big["peptide_sequence"].nunique()) if not big.empty and "peptide_sequence" in big.columns else 0,
        "n_measured": n_measured,
        "expected_rows": int(expected_rows if expected_rows is not None else n_measured),
        "errors": errors,
    }
