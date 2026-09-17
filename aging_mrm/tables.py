from __future__ import annotations

from pathlib import Path

import pandas as pd


def read_table(path: Path, *, header: int | None = 0) -> pd.DataFrame:
    suffix = path.suffix.lower()
    if suffix == ".csv":
        return pd.read_csv(path, header=header, encoding="utf-8-sig", dtype=object)
    if suffix in {".xlsx", ".xls"}:
        return pd.read_excel(path, header=header, dtype=object, engine="openpyxl")
    raise ValueError(f"Unsupported table format: {path}")


def read_csv_raw(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, header=None, encoding="utf-8-sig", dtype=object)


def col_names(df: pd.DataFrame) -> list[str]:
    return ["" if pd.isna(name) else str(name).strip() for name in df.columns]


def first_col(df: pd.DataFrame, *candidates: str) -> str | None:
    names = col_names(df)
    lowered = {name.lower(): name for name in names if name}
    for candidate in candidates:
        key = candidate.lower().strip()
        if key in lowered:
            return lowered[key]
        for name in names:
            if name.lower().strip() == key:
                return name
    for candidate in candidates:
        key = candidate.lower().strip()
        for name in names:
            if key and key in name.lower():
                return name
    return None


def series_by_name(df: pd.DataFrame, *candidates: str) -> pd.Series:
    name = first_col(df, *candidates)
    if name is None:
        return pd.Series([pd.NA] * len(df), index=df.index)
    return df[name]
