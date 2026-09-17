"""Check if record matches previously removed entries (Удалено / Deleted sheet)."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pandas as pd

from src.database_loader import load_deleted_database
from src.duplicate_check import MATCH_COLUMNS, _norm, _norm_title
from src.utils import load_config

DELETED_SHEET_NAMES = ("удалено", "deleted", "removed", "previously removed")


# load_deleted_database — в database_loader.py (по умолчанию пусто)


def check_deleted(record: dict[str, Any], deleted_database: pd.DataFrame | None = None) -> dict[str, Any]:
    """
    Check Project ID, PMID, DOI, Title, URL against deleted sheet.
    Returns {is_deleted, matched_on, matched_value}.
    """
    from src.duplicate_check import check_duplicate

    db = deleted_database if deleted_database is not None else load_deleted_database()
    if db.empty:
        return {"is_deleted": False, "matched_on": "", "matched_value": ""}

    result = check_duplicate(record, db)
    return {
        "is_deleted": result.get("is_duplicate", False),
        "matched_on": result.get("matched_on", ""),
        "matched_value": result.get("matched_value", ""),
    }
