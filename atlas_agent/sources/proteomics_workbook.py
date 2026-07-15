"""Read-only загрузка каталога из project of Proteomics.xlsx."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pandas as pd

from atlas_agent.sources.projects_table import primary_project_id

PID_RE = re.compile(r"\b(PXD\d+|PDC\d+|IPX\d+|MSV\d+)\b", re.I)

# Листы по договорённости:
# - TMT ATLAS — проекты, подошедшие в атлас
# - CPTAC — уже взято и просмотрено
# - «удалено из general» — явно отклонённые (красные строки)
SHEET_ATLAS = "TMT ATLAS"
SHEET_CPTAC = "CPTAC"
DELETED_SHEET_HINTS = ("удал", "delet", "removed")

CPTAC_ID_COL = "PDC Study ID"
CPTAC_TITLE_COLS = ("Publication Title", "Project Name")
CPTAC_URL_COL = "URL"
CPTAC_PMID_COL = "PMID"


def _all_ids_from_cell(val: Any) -> set[str]:
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return set()
    s = str(val).strip()
    ids = {m.upper() for m in PID_RE.findall(s)}
    pid = primary_project_id(s)
    if pid:
        ids.add(pid.upper())
    return ids


def _row_from_atlas(r: pd.Series) -> dict[str, str]:
    return {
        "Project ID": str(r.get("Project ID") or "").strip(),
        "PMID": str(r.get("PMID") or "").strip(),
        "DOI": "",
        "Title": str(r.get("Title") or "").strip(),
        "URL": str(r.get("URL") or "").strip(),
        "source_sheet": SHEET_ATLAS,
    }


def _row_from_cptac(r: pd.Series) -> dict[str, str]:
    title = ""
    for c in CPTAC_TITLE_COLS:
        if c in r.index and pd.notna(r.get(c)):
            title = str(r[c]).strip()
            break
    pid = str(r.get(CPTAC_ID_COL) or "").strip()
    return {
        "Project ID": pid,
        "PMID": str(r.get(CPTAC_PMID_COL) or "").strip(),
        "DOI": "",
        "Title": title,
        "URL": str(r.get(CPTAC_URL_COL) or "").strip(),
        "source_sheet": SHEET_CPTAC,
    }


def load_workbook_catalog(
    xlsx_path: str | Path,
    *,
    include_atlas: bool = True,
    include_cptac: bool = True,
) -> pd.DataFrame:
    """Единая таблица для duplicate check (read-only)."""
    path = Path(xlsx_path)
    if not path.is_file():
        return pd.DataFrame(columns=["Project ID", "PMID", "DOI", "Title", "URL", "source_sheet"])

    rows: list[dict[str, str]] = []
    xl = pd.ExcelFile(path, engine="openpyxl")

    if include_atlas and SHEET_ATLAS in xl.sheet_names:
        df = pd.read_excel(path, sheet_name=SHEET_ATLAS, engine="openpyxl")
        for _, r in df.iterrows():
            if str(r.get("Project ID") or "").strip():
                rows.append(_row_from_atlas(r))

    if include_cptac and SHEET_CPTAC in xl.sheet_names:
        df = pd.read_excel(path, sheet_name=SHEET_CPTAC, engine="openpyxl")
        for _, r in df.iterrows():
            if str(r.get(CPTAC_ID_COL) or "").strip():
                rows.append(_row_from_cptac(r))

    return pd.DataFrame(rows)


def find_deleted_sheet_name(xl: pd.ExcelFile) -> str | None:
    skip = {"general single and bulk v2", "general v1"}
    for name in xl.sheet_names:
        if name.strip().lower() in skip:
            continue
        low = name.lower()
        if "general" in low and any(h in name.lower() or h in low for h in DELETED_SHEET_HINTS):
            return name
        if any(h in name for h in DELETED_SHEET_HINTS):
            return name
    return None


def _infer_deleted_reason(r: pd.Series) -> str:
    for c in r.index:
        cl = str(c).lower()
        if "reason" in cl and "excl" in cl:
            val = str(r.get(c) or "").strip()
            if val and val.lower() != "nan":
                return val
    for c in r.index:
        cl = str(c).lower()
        if "причин" in cl or "исключ" in cl:
            val = str(r.get(c) or "").strip()
            if val and val.lower() != "nan":
                return val
    platform = str(r.get("Platform") or "")
    if re.search(r"tmt\s*[- ]?6|6\s*[- ]?plex", platform, re.I):
        return "Uses TMT 6-plex labeling"
    tissue = str(r.get("Tissue (short)") or "").strip().lower()
    if tissue in {"urine", "plasma", "saliva", "sperm", "fluid", "serum"}:
        return f"Biofluid ({tissue}) — not tissue/cell-line as required"
    exp = str(r.get("EXPERIMENTAL DESIGN") or "").lower()
    if re.search(r"phosphoproteom|phospho[- ]?proteom", exp, re.I):
        return "Phosphoproteomics — нужен protein-level proteome, не phospho-PTM"
    if any(x in exp for x in ("drug-treatment", "genetic perturbation", "time-course", "hypoxia")):
        return "Perturbation / treatment study — not baseline cohort"
    for c in r.index:
        if str(c).startswith("Unnamed"):
            val = str(r.get(c) or "").strip()
            if val and 8 < len(val) < 220 and any(
                x in val.lower()
                for x in (
                    "tmt 6",
                    "6-plex",
                    "paywall",
                    "closed-access",
                    "biofluid",
                    "perturbation",
                    "not accessible",
                    "removed",
                    "не подходит",
                    "исключ",
                )
            ):
                return val
    return ""


def _row_from_deleted(r: pd.Series) -> dict[str, str]:
    pid = str(r.get("Identifier") or r.get("Project ID") or "").strip()
    url = ""
    for c in r.index:
        if str(c).lower() in ("url", "link"):
            url = str(r.get(c) or "").strip()
            break
    reason = _infer_deleted_reason(r)
    return {
        "Project ID": pid,
        "PMID": str(r.get("PMID") or "").strip(),
        "DOI": "",
        "Title": str(r.get("Title") or "").strip(),
        "URL": url,
        "Reason": reason,
        "source_sheet": "deleted_from_general",
    }


def load_deleted_catalog(xlsx_path: str | Path) -> pd.DataFrame:
    """Лист «удалено из general» — read-only."""
    path = Path(xlsx_path)
    if not path.is_file():
        return pd.DataFrame(columns=["Project ID", "PMID", "DOI", "Title", "URL", "source_sheet"])
    xl = pd.ExcelFile(path, engine="openpyxl")
    sheet = find_deleted_sheet_name(xl)
    if not sheet:
        return pd.DataFrame(columns=["Project ID", "PMID", "DOI", "Title", "URL", "source_sheet"])
    df = pd.read_excel(path, sheet_name=sheet, engine="openpyxl")
    rows = []
    for _, r in df.iterrows():
        row = _row_from_deleted(r)
        if row["Project ID"] or row["PMID"] or row["Title"]:
            rows.append(row)
    return pd.DataFrame(rows)


def atlas_project_count(xlsx_path: str | Path) -> int:
    """Число проектов на листе TMT ATLAS."""
    return len(load_workbook_catalog(xlsx_path, include_atlas=True, include_cptac=False))


def known_accessions_from_workbook(xlsx_path: str | Path) -> set[str]:
    """Все PXD/PDC/MSV/IPX из TMT ATLAS + CPTAC."""
    df = load_workbook_catalog(xlsx_path)
    known: set[str] = set()
    for _, r in df.iterrows():
        known |= _all_ids_from_cell(r.get("Project ID"))
        pmid = re.sub(r"\D", "", str(r.get("PMID") or ""))
        if pmid:
            known.add(pmid)
    return known


def ids_from_discovery_item(item: dict) -> set[str]:
    """Собрать PXD/PDC/PMID из записи Discovery."""
    ids: set[str] = set()
    for key in ("accession", "project_accession", "title", "description"):
        ids |= _all_ids_from_cell(item.get(key))
    for id_list in (item.get("extracted_ids") or {}).values():
        for x in id_list:
            ids |= _all_ids_from_cell(x)
    pmid = re.sub(r"\D", "", str(item.get("pmid") or ""))
    if pmid:
        ids.add(pmid)
    return ids


def workbook_path_from_cfg(cfg: dict | None, *, root: Path | None = None) -> Path | None:
    """Путь к project of Proteomics.xlsx из config (read-only)."""
    wb = (cfg or {}).get("sheet", {}).get("proteomics_workbook")
    if not wb:
        return None
    path = Path(wb)
    if not path.is_absolute():
        base = root or Path(__file__).resolve().parents[2]
        path = base / wb
    return path if path.is_file() else None


def known_rejected_from_workbook(xlsx_path: str | Path) -> set[str]:
    """ID из листа «removed for general» / «удалено из general»."""
    df = load_deleted_catalog(xlsx_path)
    known: set[str] = set()
    for _, r in df.iterrows():
        known |= _all_ids_from_cell(r.get("Project ID"))
        known |= _all_ids_from_cell(r.get("Title"))
        pmid = re.sub(r"\D", "", str(r.get("PMID") or ""))
        if pmid:
            known.add(pmid)
    return known


def rejection_reasons_from_workbook(xlsx_path: str | Path) -> dict[str, str]:
    """PXD/PDC/MSV/IPX/PMID → Reason for exclusion (лист removed for general)."""
    df = load_deleted_catalog(xlsx_path)
    reasons: dict[str, str] = {}
    for _, r in df.iterrows():
        reason = str(r.get("Reason") or "").strip()
        if not reason:
            reason = "removed for general (лист removed for general)"
        keys = _all_ids_from_cell(r.get("Project ID"))
        keys |= _all_ids_from_cell(r.get("Title"))
        pmid = re.sub(r"\D", "", str(r.get("PMID") or ""))
        if pmid:
            keys.add(pmid)
        for key in keys:
            reasons.setdefault(key.upper() if not key.isdigit() else key, reason)
    return reasons


def item_in_known_set(item: dict, known: set[str]) -> bool:
    """True, если accession/PMID записи уже в каталоге или в removed for general."""
    return bool(ids_from_discovery_item(item) & known)


def filter_items_not_in_known(items: list[dict], known: set[str]) -> list[dict]:
    return [it for it in items if not item_in_known_set(it, known)]
