from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pandas as pd

from src.database_loader import load_catalog_database
from src.utils import load_config

MATCH_COLUMNS = ("Project ID", "PMID", "DOI", "Title", "URL")
ALIASES = {
    "project_id": "Project ID",
    "pmid": "PMID",
    "doi": "DOI",
    "title": "Title",
    "url": "URL",
}


def _norm(val: Any) -> str:
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return ""
    s = str(val).strip()
    if s.lower() in ("nan", "none"):
        return ""
    return s


def _norm_title(t: str) -> str:
    return re.sub(r"\s+", " ", t.lower().strip())[:120]


def load_database(path: Path | None = None) -> pd.DataFrame:
    if path is not None:
        return pd.read_excel(path, sheet_name=0, engine="openpyxl")
    return load_catalog_database()


def check_duplicate(record: dict[str, Any], database: pd.DataFrame | None = None) -> dict[str, Any]:
    db = database if database is not None else load_database()
    if db.empty:
        return {"is_duplicate": False, "matched_on": "", "matched_value": ""}

    rec = {
        "Project ID": _norm(record.get("project_id")),
        "PMID": _norm(record.get("pmid")),
        "DOI": _norm(record.get("doi")),
        "Title": _norm(record.get("title")),
        "URL": _norm(record.get("url")),
    }

    col_map = {}
    for col in db.columns:
        cl = str(col).strip().lower()
        for mc in MATCH_COLUMNS:
            if cl == mc.lower():
                col_map[mc] = col
    if "Project ID" not in col_map:
        for col in db.columns:
            if str(col).strip().lower() in ("pdc study id", "identifier", "accession", "project id"):
                col_map["Project ID"] = col
                break

    from atlas_agent.sources.projects_table import primary_project_id

    pid_re = re.compile(r"\b(PXD\d+|PDC\d+|IPX\d+|MSV\d+)\b", re.I)

    rec_ids = set()
    raw_pid = rec["Project ID"]
    if raw_pid:
        rec_ids.add(raw_pid.upper())
        rec_ids.add(primary_project_id(raw_pid).upper())
        rec_ids |= {m.upper() for m in pid_re.findall(raw_pid)}

    for field in ("Project ID", "PMID", "DOI", "URL"):
        if field not in col_map:
            continue
        val = rec[field]
        if not val:
            continue
        series = db[col_map[field]].astype(str).map(_norm)
        if field == "DOI":
            val_cmp = val.lower()
            if any(val_cmp == v.lower() for v in series if v):
                return {"is_duplicate": True, "matched_on": field, "matched_value": val}
        elif field == "Project ID":
            for cell in series:
                if not cell:
                    continue
                cell_ids = {cell.upper(), primary_project_id(cell).upper()}
                cell_ids |= {m.upper() for m in pid_re.findall(cell)}
                if rec_ids & cell_ids:
                    return {"is_duplicate": True, "matched_on": field, "matched_value": val}
        else:
            if val.upper() in (v.upper() for v in series if v):
                return {"is_duplicate": True, "matched_on": field, "matched_value": val}

    if "Title" in col_map and rec["Title"]:
        rt = _norm_title(rec["Title"])
        for v in db[col_map["Title"]].astype(str):
            if v and _norm_title(v) == rt:
                return {"is_duplicate": True, "matched_on": "Title", "matched_value": rec["Title"][:80]}

    return {"is_duplicate": False, "matched_on": "", "matched_value": ""}
