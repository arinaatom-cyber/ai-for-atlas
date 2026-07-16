#!/usr/bin/env python3
"""Export TMT ATLAS sheet → projects.csv (Excel is source of truth).

Writes:
  - human-proteome-atlas/data/projects.csv (live map site)
  - data/projects.csv (local mirror for revisor / legacy tools)
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from atlas_agent.config import load_config  # noqa: E402


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--out",
        type=Path,
        action="append",
        dest="outs",
        help="Extra target CSV (default: atlas_data_dir + data/projects.csv)",
    )
    p.add_argument(
        "--from-google",
        action="store_true",
        help="Read TMT ATLAS from Google Sheet instead of local xlsx",
    )
    args = p.parse_args()
    cfg = load_config()
    sheet = cfg["sheet"].get("projects_sheet", "TMT ATLAS")
    targets: list[Path] = list(args.outs or [])
    if not targets:
        targets.append(Path(cfg["paths"]["atlas_data_dir"]) / "projects.csv")
        targets.append(ROOT / "data" / "projects.csv")

    if args.from_google:
        from atlas_agent.sources.projects_table import load_google_sheet

        df = load_google_sheet(cfg["sheet"])
        print(f"Loaded {len(df)} rows from Google Sheet")
    else:
        xlsx = Path(cfg["sheet"]["proteomics_workbook"])
        if not xlsx.is_file():
            print(f"Missing workbook: {xlsx}", file=sys.stderr)
            return 1
        df = pd.read_excel(xlsx, sheet_name=sheet, engine="openpyxl")
    for out in targets:
        out.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(out, index=False, encoding="utf-8-sig")
        print(f"Wrote {len(df)} rows -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
