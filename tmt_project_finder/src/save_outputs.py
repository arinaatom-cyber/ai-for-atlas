from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from src.utils import ensure_manual_fields, load_config, resolve_path

BUCKET_MAP = {
    "high_priority_check": "high",
    "medium_priority_check": "medium",
    "manual_check": "manual",
    "reject": "rejected",
    "duplicate": "duplicates",
    "rejected_previously_removed": "deleted",
}


def _record_to_row(record: dict[str, Any]) -> dict[str, Any]:
    row = ensure_manual_fields(record)
    org = record.get("organism_extract") or {}
    tmt = record.get("tmt_extract") or {}
    mat = record.get("material_extract") or {}
    ctx = record.get("context_extract") or {}

    return {
        "database": row.get("database", ""),
        "project_id": row.get("project_id", ""),
        "pmid": row.get("pmid", ""),
        "doi": row.get("doi", ""),
        "title": row.get("title", ""),
        "url": row.get("url", ""),
        "description": (row.get("description") or "")[:500],
        "organism": row.get("organism") or org.get("value", ""),
        "method": row.get("method", ""),
        "sample_type": row.get("sample_type") or mat.get("value", ""),
        "publication": row.get("publication", ""),
        "classification": row.get("classification", ""),
        "reasons": "; ".join(row.get("classification_reasons") or []),
        "organism_status": org.get("status", ""),
        "tmt_status": tmt.get("status", ""),
        "tmt_confirmed": ", ".join(tmt.get("allowed_hits") or []),
        "material_status": mat.get("status", ""),
        "context_design": ctx.get("design", ""),
        "Quantification_Format": row.get("Quantification_Format", "manual review required"),
        "TMT_Channels": row.get("TMT_Channels", "manual review required"),
        "Result_Files": row.get("Result_Files", "manual review required"),
        "evidence_url": row.get("evidence_url", ""),
        "source_type": row.get("source_type", ""),
    }


def save_outputs(
    records: list[dict],
    cfg: dict | None = None,
) -> dict[str, Path]:
    cfg = cfg or load_config()
    paths_cfg = cfg.get("outputs") or {}

    rows = [_record_to_row(r) for r in records]
    df_all = pd.DataFrame(rows)

    saved: dict[str, Path] = {}
    key_to_file = {
        "found": paths_cfg.get("found", "outputs/found_projects.xlsx"),
        "high": paths_cfg.get("high", "outputs/high_priority.xlsx"),
        "medium": paths_cfg.get("medium", "outputs/medium_priority.xlsx"),
        "manual": paths_cfg.get("manual", "outputs/manual_check.xlsx"),
        "rejected": paths_cfg.get("rejected", "outputs/rejected.xlsx"),
        "duplicates": paths_cfg.get("duplicates", "outputs/duplicates.xlsx"),
        "deleted": paths_cfg.get("deleted", "outputs/previously_removed.xlsx"),
    }

    for key, fpath in key_to_file.items():
        p = resolve_path(fpath)
        p.parent.mkdir(parents=True, exist_ok=True)
        saved[key] = p

    df_all.to_excel(saved["found"], index=False, engine="openpyxl")

    for classification, key in BUCKET_MAP.items():
        sub = df_all[df_all["classification"] == classification]
        sub.to_excel(saved[key], index=False, engine="openpyxl")

    return saved
