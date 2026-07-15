from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pandas as pd

PID_RE = re.compile(r"(PXD\d+|PDC\d+|IPX\d+|MSV\d+)", re.I)
DEFAULT_ATLAS_SHEET = "TMT ATLAS"


def catalog_path(sheet_cfg: dict[str, Any]) -> str | None:
    return sheet_cfg.get("projects_file") or sheet_cfg.get("projects_csv")


def catalog_sheet(sheet_cfg: dict[str, Any]) -> str | None:
    return sheet_cfg.get("projects_sheet")


def load_projects_table(
    projects_path: str | None,
    *,
    sheet: str | None = None,
) -> pd.DataFrame:
    """Локальный каталог: CSV или Excel (лист TMT ATLAS)."""
    if not projects_path:
        raise FileNotFoundError("Укажите sheet.projects_file в config.yaml")
    path = Path(projects_path)
    if not path.is_file():
        raise FileNotFoundError(f"Файл таблицы не найден: {path}")

    if path.suffix.lower() in (".xlsx", ".xlsm"):
        sheet_name = sheet or DEFAULT_ATLAS_SHEET
        return pd.read_excel(path, sheet_name=sheet_name, engine="openpyxl")
    return pd.read_csv(path, encoding="utf-8-sig", low_memory=False)


def load_catalog(cfg: dict[str, Any] | None = None, *, sheet_cfg: dict | None = None) -> pd.DataFrame:
    """Каталог из config.yaml (по умолчанию TMT ATLAS в project of Proteomics.xlsx)."""
    sc = sheet_cfg or (cfg or {}).get("sheet") or {}
    path = catalog_path(sc)
    return load_projects_table(path, sheet=catalog_sheet(sc))


def is_excel_catalog(sheet_cfg: dict[str, Any]) -> bool:
    path = catalog_path(sheet_cfg)
    return bool(path and Path(path).suffix.lower() in (".xlsx", ".xlsm"))


def primary_project_id(raw: str) -> str:
    if raw is None or (isinstance(raw, float) and pd.isna(raw)):
        return ""
    s = str(raw).strip()
    m = re.match(r"^(IPX\d+)\s*\((PXD\d+)\)", s, re.I)
    if m:
        return m.group(2).upper()
    m = PID_RE.search(s)
    return m.group(1).upper() if m else s


def protein_count(cell) -> int | None:
    if cell is None or (isinstance(cell, float) and pd.isna(cell)):
        return None
    nums = [int(x) for x in re.findall(r"\d{2,7}", str(cell).replace(",", ""))]
    return max(nums) if nums else None
