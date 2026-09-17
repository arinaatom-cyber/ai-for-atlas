from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pandas as pd

from src.database_loader import load_deleted_database
from src.duplicate_check import MATCH_COLUMNS, _norm, _norm_title
from src.utils import load_config

DELETED_SHEET_NAMES = ("удалено", "deleted", "removed", "previously removed")


def check_deleted(record: dict[str, Any], deleted_database: pd.DataFrame | None = None) -> dict[str, Any]:
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
