"""
Сбор аннотаций канал→пациент из таблицы, диска, GitHub (read-only).
Обучение простых правил на «зелёных» (complete) проектах Protomix.
"""
from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from atlas_agent.analysis.channel_map_parser import (
    extract_patient_from_label,
    parse_excel_mapping,
    parse_freeform_channel_text,
)
from atlas_agent.analysis.tmt_channels import (
    ChannelRole,
    channels_summary_table,
    parse_channels_from_row,
)
from atlas_agent.sources.github_client import GitHubClient, parse_repo_url
from atlas_agent.sources.projects_table import primary_project_id
from atlas_agent.workflow.completeness import audit_table, row_completeness

ANNOT_FILE_RE = re.compile(
    r"channel|mapping|sample.?info|sdrf|design|metadata|annot|experimental",
    re.I,
)
ROLE_TO_CONDITION = {
    ChannelRole.CONTROL.value: "control",
    ChannelRole.CASE.value: "case",
    ChannelRole.REFERENCE.value: "reference",
}


def green_project_ids(df: pd.DataFrame) -> set[str]:
    audit = audit_table(df)
    return set(audit[audit["status"] == "complete"]["project_id"])


def _records_from_table_row(row: pd.Series, pid: str) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for ch in parse_channels_from_row(row):
        pid_hint = extract_patient_from_label(ch.label)
        records.append(
            {
                "project_id": pid,
                "channel_tag": ch.tag,
                "label": ch.label,
                "patient_id": pid_hint or "",
                "condition": ch.label,
                "role": ch.role.value,
                "source": f"csv:{ch.source_field}",
                "confidence": 0.7 if pid_hint else 0.55,
            }
        )

    tag_role = {r["channel_tag"]: r.get("role", "") for r in records}
    for col in (
        "TMT Channels Used",
        "TMT Channels Comparison",
        "TMT Additional Channels",
        "Short Description",
        "Experimental Design",
    ):
        if col not in row.index:
            continue
        for r in parse_freeform_channel_text(str(row.get(col, "")), source=f"csv:{col}"):
            r["project_id"] = pid
            r["role"] = tag_role.get(r["channel_tag"], "")
            if r.get("patient_id"):
                r["confidence"] = max(float(r.get("confidence", 0)), 0.82)
            records.append(r)
    return _dedupe_records(records)


def _dedupe_records(records: list[dict]) -> list[dict]:
    best: dict[tuple, dict] = {}
    for r in records:
        key = (r.get("project_id"), r.get("channel_tag"))
        if not key[1]:
            continue
        prev = best.get(key)
        if prev is None or float(r.get("confidence", 0)) > float(prev.get("confidence", 0)):
            best[key] = r
    return list(best.values())


def scan_local_annotation_files(project_dir: Path) -> list[dict[str, Any]]:
    if not project_dir.is_dir():
        return []
    out: list[dict[str, Any]] = []
    for p in project_dir.rglob("*"):
        if not p.is_file() or p.stat().st_size > 8_000_000:
            continue
        if not ANNOT_FILE_RE.search(p.name):
            continue
        if p.suffix.lower() in (".xlsx", ".xls"):
            for r in parse_excel_mapping(p):
                r["source"] = f"local:{p.name}"
                out.append(r)
        elif p.suffix.lower() in (".csv", ".tsv", ".txt"):
            try:
                sep = "\t" if p.suffix.lower() == ".tsv" else ","
                df = pd.read_csv(p, sep=sep, nrows=300, encoding="latin-1", on_bad_lines="skip")
                blob = df.head(20).to_string()
                if re.search(r"\b12[6-9]\b", blob):
                    out.extend(parse_freeform_channel_text(blob, source=f"local:{p.name}"))
            except Exception:
                pass
    return out


_github_ok: bool | None = None


def scan_github_annotations(cfg: dict, pid: str) -> list[dict[str, Any]]:
    global _github_ok
    gh = cfg.get("github") or {}
    data_repo = gh.get("data_repo")
    if not data_repo:
        return []
    if _github_ok is False:
        return []
    try:
        ref = parse_repo_url(data_repo, default_branch=gh.get("raw_branch") or "main")
    except ValueError:
        return []
    client = GitHubClient()
    try:
        if _github_ok is None:
            _github_ok = client.repo_meta(ref) is not None
        if not _github_ok:
            return []
    except Exception:
        _github_ok = False
        return []
    sub = gh.get("data_projects_path") or "Projects"
    out: list[dict[str, Any]] = []
    for item in client.list_contents(ref, f"{sub}/{pid}"):
        name = (item.get("name") or "").lower()
        if item.get("type") != "file" or not ANNOT_FILE_RE.search(name):
            continue
        if not name.endswith((".xlsx", ".csv", ".tsv", ".txt")):
            continue
        path = item.get("path", "")
        if name.endswith((".csv", ".tsv", ".txt")):
            text = client.get_file_text(ref, path, max_bytes=150_000).get("text") or ""
            out.extend(parse_freeform_channel_text(text, source=f"github:{path}"))
    return out


def build_project_channel_map(
    row: pd.Series,
    pid: str,
    *,
    tmt_root: str | Path,
    cfg: dict | None = None,
) -> list[dict[str, Any]]:
    records = _records_from_table_row(row, pid)
    folder = Path(tmt_root) / pid
    if not folder.is_dir():
        for p in Path(tmt_root).iterdir():
            if p.is_dir() and pid in p.name:
                folder = p
                break
    records.extend({**r, "project_id": pid} for r in scan_local_annotation_files(folder))
    if cfg:
        records.extend({**r, "project_id": pid} for r in scan_github_annotations(cfg, pid))
    return _dedupe_records(records)


def _matches_database(row: pd.Series, pid: str, database: str | None) -> bool:
    if not database:
        return True
    db = database.strip().upper()
    if db == "PDC":
        return pid.upper().startswith("PDC") or str(row.get("Database", "")).strip().upper() == "PDC"
    if db == "PRIDE":
        return pid.upper().startswith("PXD") or str(row.get("Database", "")).strip().upper() == "PRIDE"
    return str(row.get("Database", "")).strip().upper() == db or pid.upper().startswith(db)


def build_full_dataset(
    df: pd.DataFrame,
    *,
    tmt_root: str,
    cfg: dict | None = None,
    only_green: bool = True,
    database: str | None = None,
) -> pd.DataFrame:
    green = green_project_ids(df) if only_green else None
    all_records: list[dict] = []

    seen_pid: set[str] = set()
    for _, row in df.iterrows():
        pid = primary_project_id(str(row.get("Project ID", "")))
        if not pid or pid in seen_pid:
            continue
        if not _matches_database(row, pid, database):
            continue
        if "TMT" not in str(row.get("TMT Label (Unified)", "")).upper():
            continue
        if green is not None and pid not in green:
            continue
        seen_pid.add(pid)
        comp = row_completeness(row)
        recs = build_project_channel_map(row, pid, tmt_root=tmt_root, cfg=cfg)
        for r in recs:
            r["protomix_status"] = comp["status"]  # complete = green
            r["database"] = str(row.get("Database", "") or "")
            r["organ"] = str(row.get("Organ", "") or "")
            r["disease"] = str(row.get("Disease", "") or "")
            if r.get("role") == "reference":
                r["patient_id"] = r.get("patient_id") or "reference_pool"
                r["condition"] = r.get("condition") or "pooled reference"
            if not r.get("patient_id") and r.get("role"):
                r["patient_id"] = f"{ROLE_TO_CONDITION.get(r['role'], 'unknown')}_{r['channel_tag']}"
                r["confidence"] = min(float(r.get("confidence", 0.5)), 0.5)
        all_records.extend(recs)

    if not all_records:
        return pd.DataFrame()
    return pd.DataFrame(all_records)


def learn_label_rules(dataset: pd.DataFrame, min_count: int = 3) -> dict[str, Any]:
    """Частые слова в label → patient_id / condition (для подсказок)."""
    labeled = dataset[dataset["patient_id"].astype(str).str.len() > 0]
    token_to_patients: dict[str, Counter] = defaultdict(Counter)
    token_to_cond: dict[str, Counter] = defaultdict(Counter)

    for _, row in labeled.iterrows():
        label = str(row.get("label", "")).lower()
        pid = str(row.get("patient_id", ""))
        cond = str(row.get("condition", ""))
        for tok in re.findall(r"[a-z]{4,}", label):
            if tok in ("control", "normal", "healthy", "tumor", "cancer", "patient", "sample"):
                token_to_patients[tok][pid] += 1
                if cond:
                    token_to_cond[tok][cond] += 1

    rules = []
    for tok, cnt in token_to_patients.items():
        best, n = cnt.most_common(1)[0]
        if n >= min_count:
            rules.append(
                {
                    "token": tok,
                    "predict_patient_id": best,
                    "support": n,
                    "condition": token_to_cond[tok].most_common(1)[0][0] if tok in token_to_cond else "",
                }
            )
    rules.sort(key=lambda x: -x["support"])
    return {
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "n_labeled_channels": int(len(labeled)),
        "n_rules": len(rules),
        "rules": rules[:200],
    }


def apply_learned_rules(dataset: pd.DataFrame, model: dict) -> pd.DataFrame:
    df = dataset.copy()
    rules = model.get("rules") or []
    for idx, row in df.iterrows():
        if str(row.get("patient_id", "")).strip():
            continue
        label = str(row.get("label", "")).lower()
        for rule in rules:
            if rule["token"] in label:
                df.at[idx, "patient_id"] = rule["predict_patient_id"]
                df.at[idx, "condition"] = rule.get("condition") or row.get("condition", "")
                df.at[idx, "confidence"] = 0.45
                df.at[idx, "source"] = str(row.get("source", "")) + "+learned"
                break
    return df


def save_channel_dataset(
    df: pd.DataFrame,
    dataset: pd.DataFrame,
    model: dict,
    out_dir: Path,
    *,
    tag: str = "",
) -> dict[str, str]:
    out_dir.mkdir(parents=True, exist_ok=True)
    suffix = f"_{tag}" if tag else ""
    paths = {}
    p1 = out_dir / f"channel_patient_dataset{suffix}.csv"
    dataset.to_csv(p1, index=False, encoding="utf-8-sig")
    paths["dataset"] = str(p1)

    green_only = dataset[dataset["protomix_status"] == "complete"]
    p2 = out_dir / f"channel_patient_training_green{suffix}.csv"
    green_only.to_csv(p2, index=False, encoding="utf-8-sig")
    paths["training_green"] = str(p2)

    p3 = out_dir / f"channel_patient_model{suffix}.json"
    p3.write_text(json.dumps(model, ensure_ascii=False, indent=2), encoding="utf-8")
    paths["model"] = str(p3)

    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "green_projects": int(dataset["project_id"].nunique()) if not dataset.empty else 0,
        "total_channel_rows": int(len(dataset)),
        "with_patient_id": int((dataset["patient_id"].astype(str).str.len() > 0).sum()) if not dataset.empty else 0,
        "paths": paths,
    }
    p4 = out_dir / f"channel_patient_summary{suffix}.json"
    p4.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    paths["summary"] = str(p4)
    return paths
