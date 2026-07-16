#!/usr/bin/env python3
"""Скачать лист TMT ATLAS из Google Sheets → локальный CSV (без дописывания полей).

Источник (read-only export):
  https://docs.google.com/spreadsheets/d/1M6hc3vmk1bNchMvEwXsIyyO5iq3mAzP877HTXzhzg38
  gid=1072380314 (legacy; prefer --sheet name)

Пустые Disease / Organ / Subtype остаются пустыми — агент ничего не выдумывает.

  python scripts/pull_google_sheet.py              # → data/projects_from_google.csv
  python scripts/pull_google_sheet.py --compare    # diff с data/projects.csv
  python scripts/pull_google_sheet.py --apply      # перезаписать data/projects.csv (явно)
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from atlas_agent.config import load_config
from atlas_agent.sources.projects_table import (
    DEFAULT_ATLAS_SHEET,
    DEFAULT_GENERAL_SHEET,
    SHEET_COLUMN_GROUPS,
    google_sheet_export_url,
    load_general_sheet,
    load_google_sheet,
    normalize_sheet_frame,
    primary_project_id,
)


def _key_cols(df: pd.DataFrame) -> list[str]:
    preferred = [
        "Database",
        "Project ID",
        "PMID",
        "Title",
        "Total Samples",
        "Sample Type",
        "Organ",
        "Tumor Type",
        "Disease",
        "Disease Subtype",
        "Platform MS (Unified)",
        "TMT Label (Unified)",
        "Proteins Quantified",
        "Quantification_Format",
    ]
    return [c for c in preferred if c in df.columns]


def compare_frames(local: pd.DataFrame, remote: pd.DataFrame) -> None:
    lk = {primary_project_id(p): i for i, p in enumerate(local.get("Project ID", []))}
    rk = {primary_project_id(p): i for i, p in enumerate(remote.get("Project ID", []))}
    only_local = sorted(set(lk) - set(rk))
    only_remote = sorted(set(rk) - set(lk))
    print(f"Local rows: {len(lk)} | Google rows: {len(rk)}")
    if only_local:
        print(f"  Only local ({len(only_local)}): {', '.join(only_local[:8])}{'…' if len(only_local) > 8 else ''}")
    if only_remote:
        print(f"  Only Google ({len(only_remote)}): {', '.join(only_remote[:8])}{'…' if len(only_remote) > 8 else ''}")
    common = set(lk) & set(rk)
    cols = _key_cols(local)
    diffs = 0
    for pid in sorted(common):
        li, ri = lk[pid], rk[pid]
        for col in cols:
            lv = local.at[li, col] if col in local.columns else ""
            rv = remote.at[ri, col] if col in remote.columns else ""
            ls = "" if pd.isna(lv) else str(lv).strip()
            rs = "" if pd.isna(rv) else str(rv).strip()
            if ls != rs:
                diffs += 1
                if diffs <= 12:
                    print(f"  {pid} · {col}: local={ls[:40]!r} | google={rs[:40]!r}")
    if diffs > 12:
        print(f"  … and {diffs - 12} more cell diffs")
    elif diffs == 0 and not only_local and not only_remote:
        print("  Key columns match.")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--out",
        type=Path,
        default=ROOT / "data" / "projects_from_google.csv",
        help="Staging CSV (default: data/projects_from_google.csv)",
    )
    ap.add_argument(
        "--apply",
        action="store_true",
        help="Also write data/projects.csv (master mirror — only when you intend to)",
    )
    ap.add_argument("--compare", action="store_true", help="Compare with data/projects.csv")
    ap.add_argument("--preview", action="store_true", help="Print column list and 3 sample rows")
    ap.add_argument(
        "--sheet",
        default=None,
        help=f'Sheet tab name (default: config projects_sheet or "{DEFAULT_ATLAS_SHEET}")',
    )
    ap.add_argument("--general", action="store_true", help=f'Use "{DEFAULT_GENERAL_SHEET}"')
    args = ap.parse_args()

    cfg = load_config()
    sc = cfg.get("sheet") or {}

    sheet_name = args.sheet
    if args.general:
        sheet_name = sc.get("general_sheet_name") or DEFAULT_GENERAL_SHEET
    if not sheet_name:
        sheet_name = sc.get("projects_sheet") or DEFAULT_ATLAS_SHEET

    url = google_sheet_export_url(sc, sheet_name=sheet_name)
    if not url:
        print("Set sheet.google_sheet_id in config.yaml", file=sys.stderr)
        return 1

    df = load_google_sheet(sc, sheet_name=sheet_name)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(args.out, index=False, encoding="utf-8-sig")
    print(f"Google Sheet [{sheet_name}] -> {args.out} ({len(df)} rows, {len(df.columns)} cols)")
    print(f"  URL: {url}")

    missing_groups: list[str] = []
    all_expected = {c for group in SHEET_COLUMN_GROUPS.values() for c in group}
    for col in sorted(all_expected):
        if col not in df.columns:
            missing_groups.append(col)
    if missing_groups:
        print(f"  Missing expected columns ({len(missing_groups)}): {', '.join(missing_groups[:6])}…")

    if "Disease" in df.columns:
        d = df["Disease"]
        empty_disease = int(d.isna().sum() + ((d.astype(str).str.strip() == "") & d.notna()).sum())
        print(f"  Disease empty: {empty_disease} rows (left empty — OK)")

    if args.preview:
        print("\nColumns:", list(df.columns))
        show = _key_cols(df)
        print(df[show].head(3).to_string(index=False))

    if args.compare:
        local_path = ROOT / "data" / "projects.csv"
        if local_path.is_file():
            local = normalize_sheet_frame(pd.read_csv(local_path, encoding="utf-8-sig", low_memory=False))
            print("\nCompare vs data/projects.csv:")
            compare_frames(local, df)
        else:
            print("\nNo data/projects.csv to compare.")

    if args.apply:
        master = ROOT / "data" / "projects.csv"
        df.to_csv(master, index=False, encoding="utf-8-sig")
        print(f"Applied -> {master}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
