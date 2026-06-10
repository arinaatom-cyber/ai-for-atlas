"""Безопасные авто-исправления таблицы (с бэкапом)."""
from __future__ import annotations

import re
import shutil
from datetime import datetime
from pathlib import Path

import pandas as pd

from atlas_agent.revisor.checks import _normalize_pmid_cell
def apply_safe_fixes(df: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    """Только детерминированные правки без изменения смысла полей."""
    out = df.copy()
    log: list[str] = []

    if "Project ID" in out.columns:
        for i in out.index:
            raw = out.at[i, "Project ID"]
            if pd.isna(raw):
                continue
            s = str(raw).strip()
            if s != str(raw):
                out.at[i, "Project ID"] = s
                log.append(f"row {i}: trim Project ID")

    if "PMID" in out.columns:
        out["PMID"] = out["PMID"].apply(
            lambda x: "" if pd.isna(x) else _normalize_pmid_cell(x) or str(x).strip()
        )
        changed = (out["PMID"] != df["PMID"].astype(str).str.replace(r"\.0$", "", regex=True)).sum()
        if changed:
            log.append(f"PMID: нормализовано ~{int(changed)} ячеек")

    for col in out.columns:
        if out[col].dtype != object:
            continue
        for i in out.index:
            v = out.at[i, col]
            if isinstance(v, str) and v != v.strip() and v.strip():
                out.at[i, col] = v.strip()
                if col in ("Title", "Organ", "Tissue", "Normalization Strategy"):
                    log.append(f"row {i}: trim {col}")

    return out, log


def backup_csv(csv_path: Path) -> Path:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = csv_path.with_name(f"{csv_path.stem}_backup_{ts}{csv_path.suffix}")
    shutil.copy2(csv_path, backup)
    return backup


def save_table(df: pd.DataFrame, csv_path: Path) -> None:
    df.to_csv(csv_path, index=False, encoding="utf-8-sig")


def fix_and_save(csv_path: str | Path, *, dry_run: bool = True) -> dict:
    path = Path(csv_path)
    df = pd.read_csv(path, encoding="utf-8-sig", low_memory=False)
    fixed, log = apply_safe_fixes(df)
    result = {"dry_run": dry_run, "changes": len(log), "log": log[:200]}
    if dry_run or not log:
        result["backup"] = None
        result["saved"] = False
        return result
    backup = backup_csv(path)
    save_table(fixed, path)
    result["backup"] = str(backup)
    result["saved"] = True
    return result
