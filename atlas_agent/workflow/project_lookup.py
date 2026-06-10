from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import pandas as pd

from atlas_agent.analysis.result_files import audit_local_files, first_result_file
from atlas_agent.analysis.stats_plan import build_stats_plan
from atlas_agent.sources.projects_table import primary_project_id
from atlas_agent.workflow.completeness import patient_summary, row_completeness


def find_project_row(df: pd.DataFrame, project_id: str) -> pd.Series | None:
    pid = primary_project_id(project_id)
    for _, row in df.iterrows():
        if primary_project_id(str(row.get("Project ID", ""))) == pid:
            return row
    return None


def project_card(
    df: pd.DataFrame,
    project_id: str,
    tmt_projects_root: str,
) -> dict[str, Any]:
    row = find_project_row(df, project_id)
    if row is None:
        return {"found": False, "project_id": primary_project_id(project_id)}

    pid = primary_project_id(str(row["Project ID"]))
    comp = row_completeness(row)
    pat = patient_summary(row)
    plan = build_stats_plan(row)

    folder = Path(tmt_projects_root) / pid
    rf = first_result_file(str(row.get("Result Files", "")))

    paths = {
        "projects_csv_row": "data/projects.csv",
        "github_folder": f"tmt-projects/Projects/{pid}/",
        "local_folder": str(folder) if folder.is_dir() else None,
        "pride_url": f"https://www.ebi.ac.uk/pride/archive/projects/{pid}" if pid.startswith("PXD") else None,
        "pubmed_url": f"https://pubmed.ncbi.nlm.nih.gov/{str(row.get('PMID', '')).split('.')[0]}/"
        if not pd.isna(row.get("PMID"))
        else None,
    }

    local_files: list[str] = []
    if folder.is_dir():
        local_files = sorted(os.listdir(folder))[:20]

    mask = df["Project ID"].apply(lambda x: primary_project_id(x) == pid)
    file_audit = audit_local_files(df[mask], tmt_projects_root, limit=1)

    tmt_view = None
    if folder.is_dir() or str(row.get("TMT Label (Unified)", "")).lower().find("tmt") >= 0:
        try:
            from atlas_agent.analysis.tmt_channels import build_tmt_view

            tmt_view = build_tmt_view(row, tmt_projects_root)
        except Exception:
            tmt_view = None

    return {
        "found": True,
        "project_id": pid,
        "title": str(row.get("Title", "")),
        "database": str(row.get("Database", "")),
        "organ": str(row.get("Organ", "")),
        "disease": str(row.get("Disease", "")),
        "completeness": comp,
        "patient_summary": pat,
        "unified_fields": {
            "platform_ms": str(row.get("Platform MS (Unified)", "")),
            "tmt_label": str(row.get("TMT Label (Unified)", "")),
            "normalization": str(row.get("Normalization Strategy", "")),
            "z_score": str(row.get("Z-Score Level", "")),
            "fasta": str(row.get("FASTA (Unified)", "")),
            "quant_format": str(row.get("Quantification_Format", "")),
            "result_file_sheet": rf,
        },
        "paths": paths,
        "local_files": local_files,
        "file_audit": file_audit[0] if file_audit else None,
        "tmt_view": tmt_view,
        "stats_plan": plan,
        "what_to_do_next": _next_actions(comp, pat, plan),
    }


def _next_actions(comp: dict, pat: dict, plan: dict) -> list[str]:
    actions = []
    if comp["status"] != "complete":
        for col in comp["missing_unified"]:
            actions.append(f"Заполнить колонку: {col}")
    if pat["level"] == "patient" and not pat.get("fields", {}).get("Patients / donors"):
        actions.append("Уточнить число пациентов (Patients / donors)")
    if plan.get("warnings"):
        actions.extend(plan["warnings"][:3])
    if not actions:
        actions.append("Строка заполнена — можно запускать stats_plan и сверять с Result File")
    return actions
