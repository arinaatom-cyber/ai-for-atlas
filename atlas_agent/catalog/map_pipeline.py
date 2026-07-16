"""Load TMT ATLAS the same way the live organ map does (tmt-projects / Streamlit)."""
from __future__ import annotations

import importlib.util
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import pandas as pd

from atlas_agent.catalog.cell_read import (
    audit_sample_columns,
    audit_text_gaps,
    parse_count,
    strip_cell,
)
from atlas_agent.config import ROOT

TMT_DATA_CSV = "data/projects.csv"
TMT_STATS_JSON = "data/atlas_stats.json"


def tmt_projects_root(cfg: dict[str, Any] | None = None) -> Path:
    cfg = cfg or {}
    raw = (cfg.get("paths") or {}).get("tmt_projects_dir") or "../tmt-projects/Projects"
    p = Path(raw)
    if not p.is_absolute():
        p = (ROOT / p).resolve()
    return p.parent if p.name.lower() == "projects" else p


def _load_organ_atlas(cfg: dict[str, Any] | None = None):
    root = tmt_projects_root(cfg)
    mod_path = root / "organ_atlas.py"
    if not mod_path.is_file():
        raise FileNotFoundError(f"organ_atlas.py not found: {mod_path}")
    spec = importlib.util.spec_from_file_location("organ_atlas", mod_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load {mod_path}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["organ_atlas"] = mod
    spec.loader.exec_module(mod)
    return mod


def row_to_dict(row: pd.Series) -> dict[str, Any]:
    return {k: ("" if pd.isna(v) else v) for k, v in row.items()}


def prepare_map_frame(df: pd.DataFrame, cfg: dict[str, Any] | None = None) -> pd.DataFrame:
    """Same steps as streamlit_app.load_projects() — source for organ counts on the map."""
    oa = _load_organ_atlas(cfg)
    out = df.copy()
    pid = out["Project ID"].astype(str).str.strip()
    out = out[pid.notna() & ~pid.isin(["", "nan", "NaN", "None"])].copy()
    out = oa.enrich_projects(out)
    out = out.drop_duplicates(subset=["Project ID"], keep="first").reset_index(drop=True)
    return out


def compute_map_overview(df: pd.DataFrame) -> dict[str, int | float]:
    """KPI block matching Streamlit statistics fallback."""
    return {
        "datasets": len(df),
        "unique_pmids": int(df["PMID"].nunique()) if "PMID" in df.columns else 0,
        "total_samples": int(df["Total Samples"].map(parse_count).sum()) if "Total Samples" in df.columns else 0,
        "patients_donors": int(df["Patients / donors"].map(parse_count).sum()) if "Patients / donors" in df.columns else 0,
        "control_healthy": int(df["Control Healthy"].map(parse_count).sum()) if "Control Healthy" in df.columns else 0,
        "case_untreated": int(df["Case Cancer Untreated"].map(parse_count).sum()) if "Case Cancer Untreated" in df.columns else 0,
        "case_treated": int(df["Case Cancer Treated"].map(parse_count).sum()) if "Case Cancer Treated" in df.columns else 0,
        "precancer": int(df["preCancer"].map(parse_count).sum()) if "preCancer" in df.columns else 0,
    }


def organ_counts_for_map(df: pd.DataFrame, cfg: dict[str, Any] | None = None) -> Counter:
    oa = _load_organ_atlas(cfg)
    return oa.organ_project_counts(df)


def organ_label(key: str) -> str:
    return key.replace("_", " ")


def build_map_stats_sections(df: pd.DataFrame, cfg: dict[str, Any] | None = None) -> dict[str, Any]:
    """Overview + organ dataset counts from map logic (for atlas_stats.json)."""
    overview = compute_map_overview(df)
    ctr = organ_counts_for_map(df, cfg)
    top_organs_datasets = [
        {"organ": organ_label(k), "count": v}
        for k, v in ctr.most_common()
        if k not in ("Other", "Multiple_Organs")
    ]
    return {"overview": overview, "top_organs_datasets": top_organs_datasets}


def load_deployed_map_csv(cfg: dict[str, Any] | None = None) -> pd.DataFrame:
    path = tmt_projects_root(cfg) / TMT_DATA_CSV
    if not path.is_file():
        raise FileNotFoundError(f"Deployed map CSV missing: {path}")
    return pd.read_csv(path, encoding="utf-8-sig", low_memory=False)


def load_deployed_stats(cfg: dict[str, Any] | None = None) -> dict[str, Any]:
    path = tmt_projects_root(cfg) / TMT_STATS_JSON
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def patch_deployed_stats_from_sheet(
    sheet_df: pd.DataFrame,
    cfg: dict[str, Any] | None = None,
    *,
    write: bool = False,
) -> dict[str, Any]:
    """Refresh overview + top_organs_datasets in atlas_stats.json from TMT ATLAS."""
    path = tmt_projects_root(cfg) / TMT_STATS_JSON
    existing = load_deployed_stats(cfg) if path.is_file() else {}
    map_df = prepare_map_frame(sheet_df, cfg)
    fresh = build_map_stats_sections(map_df, cfg)
    merged = dict(existing)
    merged["overview"] = fresh["overview"]
    merged["top_organs_datasets"] = fresh["top_organs_datasets"]
    if write:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(merged, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return merged


def audit_row_for_map(row: dict[str, Any], *, row_index: int, cfg: dict[str, Any] | None = None) -> dict[str, Any]:
    oa = _load_organ_atlas(cfg)
    issues = audit_sample_columns(row) + audit_text_gaps(row)
    organs = list(oa.enrich_projects(pd.DataFrame([row])).iloc[0]["organs"])
    organ_col = strip_cell(row.get("Organ"))
    if not organ_col and "Other" in organs:
        issues.append({
            "field": "Organ",
            "code": "map_other",
            "severity": "warn",
            "msg": f"Map shows {organs} via fallback",
        })
    sev = "ok"
    if any(i.get("code") == "organ_empty" for i in issues):
        sev = "error"
    elif issues:
        sev = "warn"
    return {
        "row_index": row_index,
        "project_id": strip_cell(row.get("Project ID")),
        "pid": oa.normalize_pid(strip_cell(row.get("Project ID"))),
        "organ_column": organ_col,
        "map_organs": organs,
        "issues": issues,
        "status": sev,
    }


def compare_frames(
    sheet_df: pd.DataFrame,
    deployed_df: pd.DataFrame,
    cfg: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Sheet (TMT ATLAS) vs deployed map CSV — per Project ID."""
    sheet_map = prepare_map_frame(sheet_df, cfg)
    dep_map = prepare_map_frame(deployed_df, cfg)

    sheet_by_id = {r["Project ID"]: r for _, r in sheet_map.iterrows()}
    dep_by_id = {r["Project ID"]: r for _, r in dep_map.iterrows()}

    only_sheet = sorted(set(sheet_by_id) - set(dep_by_id))
    only_dep = sorted(set(dep_by_id) - set(sheet_by_id))
    organ_mismatches = []
    for pid in sorted(set(sheet_by_id) & set(dep_by_id)):
        so = set(sheet_by_id[pid]["organs"])
        do = set(dep_by_id[pid]["organs"])
        if so != do:
            organ_mismatches.append({
                "project_id": pid,
                "sheet_organs": sorted(so),
                "deployed_organs": sorted(do),
            })

    sheet_kpi = compute_map_overview(sheet_map)
    dep_kpi = compute_map_overview(dep_map)
    sheet_org = organ_counts_for_map(sheet_map, cfg)
    dep_org = organ_counts_for_map(dep_map, cfg)

    return {
        "sheet_rows": len(sheet_df),
        "sheet_map_rows": len(sheet_map),
        "deployed_rows": len(deployed_df),
        "deployed_map_rows": len(dep_map),
        "only_sheet": only_sheet,
        "only_deployed": only_dep,
        "organ_mismatches": organ_mismatches,
        "kpi_sheet": sheet_kpi,
        "kpi_deployed": dep_kpi,
        "kpi_diff": {k: sheet_kpi.get(k, 0) - dep_kpi.get(k, 0) for k in sheet_kpi},
        "organ_counts_sheet": dict(sheet_org.most_common()),
        "organ_counts_deployed": dict(dep_org.most_common()),
    }
