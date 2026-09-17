#!/usr/bin/env python3
"""Create template existing_database.xlsx (only if missing)."""
from __future__ import annotations

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "existing_database.xlsx"

COLUMNS = ["Project ID", "PMID", "DOI", "Title", "URL", "Notes"]


def main() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    if DB_PATH.exists():
        print(f"Already exists (not modified): {DB_PATH}")
        return
    main_df = pd.DataFrame(columns=COLUMNS)
    deleted_df = pd.DataFrame(columns=COLUMNS)
    with pd.ExcelWriter(DB_PATH, engine="openpyxl") as writer:
        main_df.to_excel(writer, sheet_name="Database", index=False)
        deleted_df.to_excel(writer, sheet_name="Удалено", index=False)
    print(f"Created: {DB_PATH}")


if __name__ == "__main__":
    main()
