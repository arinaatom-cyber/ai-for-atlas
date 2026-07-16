from __future__ import annotations

import io
import re
from pathlib import Path
from typing import Any

import pandas as pd
import requests

PID_RE = re.compile(r"(PXD\d+|PDC\d+|IPX\d+|MSV\d+)", re.I)
DEFAULT_ATLAS_SHEET = "TMT ATLAS"
DEFAULT_GENERAL_SHEET = "General single and bulk v2"

# Лист TMT ATLAS — колонки, которые читаем как есть (ничего не дописываем).
SHEET_COLUMN_GROUPS = {
    "id": ["Database", "Project ID", "PMID", "Title", "URL"],
    "samples": [
        "Total Samples",
        "preCancer",
        "Case Cancer Untreated",
        "Case Cancer Treated",
        "Control Healthy",
        "Healthy Treated",
        "Healty trraeted",
        "Patients / donors",
        "Samples Original N",
        "Samples Used N",
    ],
    "design": [
        "Tissue Cell Type Detailed",
        "Sample Type",
        "Tissue",
        "Organ",
        "Tumor Type",
        "Cell Line Name",
        "Cell Line Cancer;Normal",
        "Cell Line Organ",
        "Tumor type for cell lines",
        "Tissue for cell lines",
        "Disease",
        "Disease Subtype",
        "Experimental Design",
        "Short Description",
    ],
    "ms_tmt": [
        "Platform MS (Unified)",
        "TMT Label (Unified)",
        "Proteins Quantified",
        "TMT Channels Used",
        "TMT Channels Comparison",
        "TMT Additional Channels",
        "Normalization Strategy",
        "Quantification_Format",
        "Result Files",
    ],
}


def catalog_path(sheet_cfg: dict[str, Any]) -> str | None:
    primary = sheet_cfg.get("projects_file") or sheet_cfg.get("projects_csv")
    if primary and Path(primary).is_file():
        return primary
    fallback = sheet_cfg.get("projects_csv")
    if fallback and Path(fallback).is_file():
        return fallback
    return primary


def catalog_sheet(sheet_cfg: dict[str, Any]) -> str | None:
    return sheet_cfg.get("projects_sheet")


def google_sheet_export_url(
    sheet_cfg: dict[str, Any],
    *,
    sheet_name: str | None = None,
) -> str | None:
    """Public CSV URL. Prefer sheet name (gviz) — надёжнее, чем gid."""
    direct = (sheet_cfg.get("google_sheet_csv") or "").strip()
    if direct:
        return direct
    sid = (sheet_cfg.get("google_sheet_id") or "").strip()
    if not sid:
        return None
    name = (
        sheet_name
        or sheet_cfg.get("google_sheet_name")
        or sheet_cfg.get("projects_sheet")
        or DEFAULT_ATLAS_SHEET
    )
    if name:
        from urllib.parse import quote

        return (
            f"https://docs.google.com/spreadsheets/d/{sid}/gviz/tq"
            f"?tqx=out:csv&sheet={quote(name)}"
        )
    gid = str(sheet_cfg.get("google_sheet_gid") or "").strip()
    if gid:
        return f"https://docs.google.com/spreadsheets/d/{sid}/export?format=csv&gid={gid}"
    return None


def load_google_sheet(
    sheet_cfg: dict[str, Any],
    *,
    sheet_name: str | None = None,
) -> pd.DataFrame:
    url = google_sheet_export_url(sheet_cfg, sheet_name=sheet_name)
    if not url:
        raise FileNotFoundError(
            "Укажите sheet.google_sheet_id (+ google_sheet_name) в config.yaml"
        )
    r = requests.get(url, timeout=90)
    r.raise_for_status()
    df = pd.read_csv(io.StringIO(r.text), encoding="utf-8", low_memory=False)
    return normalize_sheet_frame(df)


def load_general_sheet(cfg: dict[str, Any] | None = None, *, sheet_cfg: dict | None = None) -> pd.DataFrame:
    """Лист General single and bulk v2 — весь пул (не только TMT ATLAS)."""
    sc = dict(sheet_cfg or (cfg or {}).get("sheet") or {})
    name = sc.get("general_sheet_name") or DEFAULT_GENERAL_SHEET
    return load_google_sheet(sc, sheet_name=name)


def normalize_sheet_frame(df: pd.DataFrame) -> pd.DataFrame:
    """Trim whitespace only — never invent Disease, Organ, TMT, etc."""
    out = df.copy()
    # Legacy typo column on some sheet exports
    if "Healty trraeted" in out.columns:
        typo = out["Healty trraeted"]
        if "Healthy Treated" in out.columns:
            ht = out["Healthy Treated"]
            empty = ht.isna() | (ht.astype(str).str.strip().isin(["", "nan", "NaN"]))
            out.loc[empty, "Healthy Treated"] = typo.loc[empty]
        else:
            out = out.rename(columns={"Healty trraeted": "Healthy Treated"})
        out = out.drop(columns=["Healty trraeted"], errors="ignore")
    if "Project ID" in out.columns:
        pid = out["Project ID"].astype(str).str.strip()
        out = out[pid.notna() & (pid != "") & (~pid.isin(["nan", "NaN", "None"]))].copy()
    for col in out.columns:
        if out[col].dtype == object:
            out[col] = out[col].map(lambda x: x.strip() if isinstance(x, str) else x)
    return out.reset_index(drop=True)


def catalog_source(sheet_cfg: dict[str, Any]) -> str:
    return str(sheet_cfg.get("source") or "auto").lower().strip()


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
        df = pd.read_excel(path, sheet_name=sheet_name, engine="openpyxl")
    else:
        df = pd.read_csv(path, encoding="utf-8-sig", low_memory=False)
    return normalize_sheet_frame(df)


def load_catalog(cfg: dict[str, Any] | None = None, *, sheet_cfg: dict | None = None) -> pd.DataFrame:
    """Каталог: local Excel/CSV или Google Sheet (config sheet.source)."""
    sc = sheet_cfg or (cfg or {}).get("sheet") or {}
    mode = catalog_source(sc)
    if mode == "google":
        return load_google_sheet(sc, sheet_name=sc.get("projects_sheet") or DEFAULT_ATLAS_SHEET)

    path = catalog_path(sc)
    if path and Path(path).is_file():
        return load_projects_table(path, sheet=catalog_sheet(sc))

    if mode == "local":
        raise FileNotFoundError(f"Локальный каталог не найден: {path}")

    url = google_sheet_export_url(sc, sheet_name=sc.get("projects_sheet") or DEFAULT_ATLAS_SHEET)
    if url:
        return load_google_sheet(sc, sheet_name=sc.get("projects_sheet") or DEFAULT_ATLAS_SHEET)
    raise FileNotFoundError("Нет локального файла и не задан google_sheet_id")


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
