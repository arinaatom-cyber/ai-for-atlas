"""Read-only drift check: runtime CSV vs curator Excel (TMT ATLAS).

Discovery always indexes `data/projects.csv`. The workbook is a curator copy.
This module never writes either file.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pandas as pd

from atlas_agent.sources.projects_table import (
    DEFAULT_ATLAS_SHEET,
    all_repo_ids,
    curator_workbook_path,
    load_projects_table,
    primary_project_id,
)

KEY_COLS = [
    "Database",
    "Project ID",
    "PMID",
    "Title",
    "Organ",
    "Disease",
    "TMT Label (Unified)",
]


def _cell_text(value: Any) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    s = str(value).replace("\r\n", "\n").replace("\r", "\n")
    return re.sub(r"[ \t]+", " ", s).strip()


def catalog_id_set(df: pd.DataFrame) -> set[str]:
    ids: set[str] = set()
    if "Project ID" not in df.columns:
        return ids
    for v in df["Project ID"].dropna():
        ids |= all_repo_ids(str(v))
        pid = primary_project_id(str(v))
        if pid:
            ids.add(pid.upper())
    return ids


def compare_frames(
    left: pd.DataFrame,
    right: pd.DataFrame,
    *,
    left_name: str = "csv",
    right_name: str = "xlsx",
) -> dict[str, Any]:
    left_ids = catalog_id_set(left)
    right_ids = catalog_id_set(right)
    only_left = sorted(left_ids - right_ids)
    only_right = sorted(right_ids - left_ids)
    common = left_ids & right_ids
    cols = [c for c in KEY_COLS if c in left.columns and c in right.columns]
    left_by = {}
    right_by = {}
    if "Project ID" in left.columns:
        for i, p in enumerate(left["Project ID"]):
            pid = primary_project_id(str(p))
            if pid and pid not in left_by:
                left_by[pid] = i
    if "Project ID" in right.columns:
        for i, p in enumerate(right["Project ID"]):
            pid = primary_project_id(str(p))
            if pid and pid not in right_by:
                right_by[pid] = i
    cell_diffs: list[dict[str, str]] = []
    for pid in sorted(set(left_by) & set(right_by)):
        li, ri = left_by[pid], right_by[pid]
        for col in cols:
            lv = left.at[li, col]
            rv = right.at[ri, col]
            ls = _cell_text(lv)
            rs = _cell_text(rv)
            if ls != rs:
                cell_diffs.append({"project_id": pid, "column": col, "left": ls[:80], "right": rs[:80]})
    in_sync = not only_left and not only_right and not cell_diffs
    return {
        "left": left_name,
        "right": right_name,
        "left_rows": int(len(left)),
        "right_rows": int(len(right)),
        "only_left": only_left,
        "only_right": only_right,
        "shared_ids": len(common),
        "cell_diffs": cell_diffs,
        "in_sync": in_sync,
    }


def compare_catalog_files(
    csv_path: str | Path | None,
    xlsx_path: str | Path | None,
    *,
    sheet: str = DEFAULT_ATLAS_SHEET,
) -> dict[str, Any]:
    csv_p = Path(csv_path) if csv_path else None
    xlsx_p = Path(xlsx_path) if xlsx_path else None
    if not csv_p or not csv_p.is_file():
        return {
            "in_sync": False,
            "error": "csv_missing",
            "csv": str(csv_p or ""),
            "xlsx": str(xlsx_p or ""),
        }
    if not xlsx_p or not xlsx_p.is_file():
        return {
            "in_sync": True,
            "warning": "xlsx_missing",
            "csv": str(csv_p),
            "xlsx": str(xlsx_p or ""),
            "note": "Runtime catalog is CSV; workbook absent — nothing to compare.",
        }
    left = load_projects_table(str(csv_p))
    right = load_projects_table(str(xlsx_p), sheet=sheet)
    out = compare_frames(left, right, left_name=str(csv_p), right_name=str(xlsx_p))
    out["sheet"] = sheet
    return out


def compare_from_config(cfg: dict[str, Any] | None) -> dict[str, Any]:
    sc = (cfg or {}).get("sheet") or {}
    csv = sc.get("projects_csv")
    xlsx = curator_workbook_path(sc)
    sheet = sc.get("projects_sheet") or DEFAULT_ATLAS_SHEET
    return compare_catalog_files(csv, xlsx, sheet=sheet)


def format_compare_report(result: dict[str, Any]) -> str:
    if result.get("error"):
        return f"Catalog compare: {result['error']} (csv={result.get('csv')})"
    if result.get("warning"):
        return f"Catalog compare: {result['warning']} — {result.get('note') or ''}".strip()
    lines = [
        f"Runtime CSV rows: {result.get('left_rows')} · workbook rows: {result.get('right_rows')}",
        f"Shared IDs: {result.get('shared_ids')}",
    ]
    only_left = result.get("only_left") or []
    only_right = result.get("only_right") or []
    if only_left:
        lines.append(f"Only in CSV ({len(only_left)}): {', '.join(only_left[:12])}")
    if only_right:
        lines.append(f"Only in workbook ({len(only_right)}): {', '.join(only_right[:12])}")
    diffs = result.get("cell_diffs") or []
    if diffs:
        lines.append(f"Cell diffs: {len(diffs)}")
        for d in diffs[:12]:
            lines.append(f"  {d['project_id']} · {d['column']}: csv={d['left']!r} | xlsx={d['right']!r}")
    if result.get("in_sync"):
        lines.append("CSV and workbook IDs/key columns match.")
    return "\n".join(lines)
