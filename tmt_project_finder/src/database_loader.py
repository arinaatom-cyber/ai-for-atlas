from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
ATLAS_ROOT = ROOT.parent
if str(ATLAS_ROOT) not in sys.path:
    sys.path.insert(0, str(ATLAS_ROOT))

from atlas_agent.sources.proteomics_workbook import (
    SHEET_ATLAS,
    SHEET_CPTAC,
    load_deleted_catalog,
    load_workbook_catalog,
)
from src.utils import load_config

PID_RE = re.compile(r"\b(PXD\d+|PDC\d+|IPX\d+|MSV\d+)\b", re.I)


def resolve_database_path(cfg: dict | None = None) -> Path:
    cfg = cfg or load_config()
    raw = cfg.get("database_path") or "data/existing_database.xlsx"
    p = Path(raw)
    if not p.is_absolute():
        p = ROOT / p
    if p.is_file():
        return p
    fallback = cfg.get("database_path_fallback")
    if fallback:
        fb = Path(str(fallback))
        if not fb.is_absolute():
            fb = ROOT / fb
        if fb.is_file():
            return fb
    return p


def load_catalog_database(cfg: dict | None = None) -> pd.DataFrame:
    cfg = cfg or load_config()
    path = resolve_database_path(cfg)

    if path.suffix.lower() in (".xlsx", ".xlsm"):
        sheets = {str(s).strip() for s in (cfg.get("catalog_sheets") or [SHEET_ATLAS])}
        reviewed = {str(s).strip() for s in (cfg.get("reviewed_sheets") or [SHEET_CPTAC])}
        return load_workbook_catalog(
            path,
            include_atlas=SHEET_ATLAS in sheets,
            include_cptac=SHEET_CPTAC in reviewed,
        )

    return pd.read_excel(path, sheet_name=0, engine="openpyxl")


def load_deleted_database(cfg: dict | None = None) -> pd.DataFrame:
    cfg = cfg or load_config()
    if not cfg.get("use_deleted_sheet", True):
        return pd.DataFrame(columns=["Project ID", "PMID", "DOI", "Title", "URL"])
    path = resolve_database_path(cfg)
    return load_deleted_catalog(path)
