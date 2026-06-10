"""Добавление новых PXD в projects.csv (черновые строки)."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

from atlas_agent.revisor.fixes import backup_csv, save_table


def _empty_row(columns: list[str]) -> dict:
    return {c: "" for c in columns}


def candidate_to_row(candidate: dict[str, Any], columns: list[str]) -> dict:
    row = _empty_row(columns)
    acc = (candidate.get("accession") or "").upper()
    row["Database"] = "PRIDE"
    row["Project ID"] = acc
    row["Title"] = candidate.get("title", "")
    row["URL"] = candidate.get("url") or f"https://www.ebi.ac.uk/pride/archive/projects/{acc}"
    if candidate.get("pmid"):
        row["PMID"] = str(candidate["pmid"])
    if candidate.get("tmt_detected") or candidate.get("tmt_label"):
        row["TMT Label (Unified)"] = candidate.get("tmt_label") or "TMT (auto-detected)"
    orgs = candidate.get("organisms") or []
    if orgs:
        row["Organ"] = "; ".join(str(o) for o in orgs[:3])
    note = f"[AUTO {datetime.now().strftime('%Y-%m-%d')}] добавлено ревизором"
    if candidate.get("similar_in_catalog"):
        tops = [s["project_id"] for s in candidate["similar_in_catalog"][:3]]
        note += f"; похоже на: {', '.join(tops)}"
    row["Short Description"] = note
    row["Experimental Design"] = (
        f"PRIDE submission {candidate.get('submission_date', '')}; "
        f"источник: {candidate.get('source', 'scan')}"
    )
    return row


def append_candidates(
    df: pd.DataFrame,
    candidates: list[dict],
    csv_path: Path,
    *,
    dry_run: bool = True,
    skip_similar: bool = True,
) -> dict[str, Any]:
    """
    Добавляет новые PXD. skip_similar=True — не добавлять при score>=0.35 к существующему.
    """
    from atlas_agent.sources.projects_table import primary_project_id

    known = {
        primary_project_id(str(x))
        for x in df["Project ID"].dropna()
        if str(x).strip()
    }

    to_add: list[dict] = []
    skipped = []
    for c in candidates:
        acc = (c.get("accession") or "").upper()
        if not acc or acc in known:
            skipped.append({"accession": acc, "reason": "already_in_table"})
            continue
        if skip_similar and c.get("has_close_match"):
            skipped.append(
                {
                    "accession": acc,
                    "reason": "similar_exists",
                    "similar": c.get("similar_in_catalog", [])[:2],
                }
            )
            continue
        to_add.append(candidate_to_row(c, list(df.columns)))

    result = {
        "dry_run": dry_run,
        "added": len(to_add),
        "skipped": skipped,
        "accessions": [r["Project ID"] for r in to_add],
    }
    if dry_run or not to_add:
        result["saved"] = False
        return result

    new_df = pd.concat([df, pd.DataFrame(to_add)], ignore_index=True)
    backup = backup_csv(csv_path)
    save_table(new_df, csv_path)
    result["saved"] = True
    result["backup"] = str(backup)
    result["total_rows"] = len(new_df)
    return result
