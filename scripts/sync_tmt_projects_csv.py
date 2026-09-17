#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from atlas_agent.config import load_config
from atlas_agent.sources.catalog_sync import (
    compare_from_config,
    format_compare_report,
)
from atlas_agent.sources.projects_table import curator_workbook_path


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--out",
        type=Path,
        action="append",
        dest="outs",
        help="CSV targets used only with --apply (default: atlas_data_dir + data/projects.csv)",
    )
    p.add_argument(
        "--from-google",
        action="store_true",
        help="Read TMT ATLAS from Google Sheet instead of local xlsx (only with --apply)",
    )
    p.add_argument(
        "--apply",
        action="store_true",
        help="Write CSV from the workbook. Without this flag nothing is written.",
    )
    p.add_argument("--json", action="store_true", help="Print compare result as JSON")
    args = p.parse_args()
    cfg = load_config()
    sheet = cfg["sheet"].get("projects_sheet", "TMT ATLAS")

    if not args.apply:
        result = compare_from_config(cfg)
        if args.json:
            slim = dict(result)
            diffs = slim.get("cell_diffs") or []
            slim["cell_diffs"] = diffs[:40]
            slim["cell_diff_count"] = len(diffs)
            print(json.dumps(slim, ensure_ascii=False, indent=2))
        else:
            print(format_compare_report(result))
            if result.get("in_sync"):
                print("No write. Runtime catalog remains data/projects.csv.")
            else:
                print(
                    "Drift detected. Runtime index stays CSV until you run "
                    "`python scripts/sync_tmt_projects_csv.py --apply` after checking the workbook."
                )
        if result.get("error"):
            return 1
        return 0 if result.get("in_sync") else 2

    import pandas as pd

    targets: list[Path] = list(args.outs or [])
    if not targets:
        atlas_dir = (cfg.get("paths") or {}).get("atlas_data_dir")
        if atlas_dir:
            targets.append(Path(atlas_dir) / "projects.csv")
        targets.append(ROOT / "data" / "projects.csv")

    if args.from_google:
        from atlas_agent.sources.projects_table import load_google_sheet

        df = load_google_sheet(cfg["sheet"])
        print(f"Loaded {len(df)} rows from Google Sheet")
    else:
        xlsx = curator_workbook_path(cfg["sheet"])
        if not xlsx or not Path(xlsx).is_file():
            print(f"Missing workbook: {xlsx}", file=sys.stderr)
            return 1
        df = pd.read_excel(xlsx, sheet_name=sheet, engine="openpyxl")
        print(f"Loaded {len(df)} rows from {xlsx} [{sheet}]")
    for out in targets:
        out.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(out, index=False, encoding="utf-8-sig")
        print(f"Wrote {len(df)} rows -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
