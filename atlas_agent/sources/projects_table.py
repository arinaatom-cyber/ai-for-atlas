from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

PID_RE = re.compile(r"(PXD\d+|PDC\d+|IPX\d+|MSV\d+)", re.I)


def load_projects_table(projects_csv: str | None) -> pd.DataFrame:
    """Только локальный CSV — без Google Sheets."""
    if not projects_csv:
        raise FileNotFoundError("Укажите sheet.projects_csv в config.yaml")
    path = Path(projects_csv)
    if not path.is_file():
        raise FileNotFoundError(f"Файл таблицы не найден: {path}")
    return pd.read_csv(path, encoding="utf-8-sig", low_memory=False)


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
