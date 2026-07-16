#!/usr/bin/env python3
"""Verify TMT ATLAS sheet vs live organ map (tmt-projects/data/projects.csv).

Uses the same pipeline as Streamlit: organ_atlas.enrich_projects + dedup by Project ID.

  python scripts/verify_atlas_map.py
  python scripts/verify_atlas_map.py --from-google
  python scripts/verify_atlas_map.py --pid PXD021265_CL
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from atlas_agent.catalog.cell_read import cell_state, strip_cell
from atlas_agent.catalog.map_pipeline import (
    audit_row_for_map,
    compare_frames,
    compute_map_overview,
    load_deployed_map_csv,
    load_deployed_stats,
    organ_counts_for_map,
    patch_deployed_stats_from_sheet,
    prepare_map_frame,
    row_to_dict,
    tmt_projects_root,
)
from atlas_agent.config import load_config
from atlas_agent.sources.projects_table import load_catalog, load_google_sheet, normalize_sheet_frame


def _load_sheet(cfg: dict, *, from_google: bool) -> "pd.DataFrame":
    import pandas as pd

    sc = cfg.get("sheet") or {}
    if from_google:
        return load_google_sheet(sc, sheet_name=sc.get("projects_sheet") or "TMT ATLAS")
    return load_catalog(cfg)


def _cell_summary(records: list[dict]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for rec in records:
        for iss in rec.get("issues", []):
            code = iss.get("code", "?")
            counts[code] = counts.get(code, 0) + 1
    return dict(sorted(counts.items(), key=lambda x: -x[1]))


def write_markdown(
    path: Path,
    *,
    cmp: dict,
    records: list[dict],
    stats_json: dict,
    sheet_kpi: dict,
) -> None:
    by_status = {"ok": 0, "warn": 0, "error": 0}
    for r in records:
        by_status[r["status"]] = by_status.get(r["status"], 0) + 1

    lines = [
        "# TMT ATLAS vs organ map",
        "",
        f"Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        "",
        "Data flow: **Google/local TMT ATLAS** -> `organ_atlas.enrich_projects` -> "
        f"**{tmt_projects_root()}** map CSV",
        "",
        "## Row counts",
        "",
        f"| Source | Raw rows | Map rows (after dedup) |",
        f"|--------|----------|------------------------|",
        f"| Sheet | {cmp['sheet_rows']} | {cmp['sheet_map_rows']} |",
        f"| Deployed map CSV | {cmp['deployed_rows']} | {cmp['deployed_map_rows']} |",
        "",
    ]

    if cmp["only_sheet"] or cmp["only_deployed"]:
        lines += ["## Project ID drift", ""]
        if cmp["only_sheet"]:
            lines.append(f"- Only in sheet: `{', '.join(cmp['only_sheet'][:12])}`"
                         + (" …" if len(cmp["only_sheet"]) > 12 else ""))
        if cmp["only_deployed"]:
            lines.append(f"- Only in deployed CSV: `{', '.join(cmp['only_deployed'][:12])}`"
                         + (" …" if len(cmp["only_deployed"]) > 12 else ""))
        lines.append("")

    lines += [
        "## KPI (map logic)",
        "",
        "| Metric | Sheet | Deployed CSV | Diff |",
        "|--------|------:|-------------:|-----:|",
    ]
    for k, v in cmp["kpi_sheet"].items():
        d = cmp["kpi_deployed"].get(k, 0)
        diff = v - d
        flag = " **" if diff else ""
        lines.append(f"| {k} | {v:,} | {d:,} | {diff:+,}{flag}|")

    if stats_json.get("overview"):
        ov = stats_json["overview"]
        lines += [
            "",
            "### atlas_stats.json (published on Streamlit)",
            "",
            f"- datasets: {ov.get('datasets', '?')}",
            f"- total_samples: {ov.get('total_samples', '?')}",
            f"- patients_donors: {ov.get('patients_donors', '?')}",
        ]
        sk = sheet_kpi
        for key, label in (
            ("datasets", "datasets"),
            ("total_samples", "total_samples"),
            ("patients_donors", "patients_donors"),
        ):
            pub = ov.get(key)
            live = sk.get(key)
            if pub is not None and live is not None and int(pub) != int(live):
                lines.append(f"- **MISMATCH** {label}: stats.json={pub:,} vs sheet+map={live:,}")

    lines += [
        "",
        "## Row audit (empty / zero / gaps)",
        "",
        f"- OK: {by_status.get('ok', 0)}",
        f"- Warn: {by_status.get('warn', 0)}",
        f"- Error: {by_status.get('error', 0)}",
        "",
        "### Issue codes",
        "",
    ]
    for code, n in _cell_summary(records).items():
        lines.append(f"- `{code}`: {n}")

    bad = [r for r in records if r["status"] != "ok"]
    if bad:
        lines += ["", "## Rows needing attention", "", "| Row | Project ID | Status | Issue |", "|----:|------------|--------|-------|"]
        for r in bad[:40]:
            msg = "; ".join(i["msg"][:70] for i in r["issues"][:2])
            lines.append(f"| {r['row_index']} | {r['project_id']} | {r['status']} | {msg} |")
        if len(bad) > 40:
            lines.append(f"| … | +{len(bad) - 40} more | | |")

    if cmp["organ_mismatches"]:
        lines += ["", "## Organ mismatch sheet vs deployed", ""]
        for m in cmp["organ_mismatches"][:15]:
            lines.append(
                f"- `{m['project_id']}`: sheet {m['sheet_organs']} vs deployed {m['deployed_organs']}"
            )

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def print_pid(records: list[dict], pid_query: str) -> int:
    q = pid_query.strip().upper()
    hits = [r for r in records if q in r["project_id"].upper() or q in r["pid"].upper()]
    if not hits:
        print(f"No row for {pid_query}")
        return 1
    for r in hits:
        print(f"\nRow {r['row_index']}  {r['project_id']}")
        print(f"  Organ column: {r['organ_column'] or '(empty)'}")
        print(f"  Map organs:     {r['map_organs']}")
        print(f"  Status:         {r['status']}")
        for i in r["issues"]:
            print(f"  - [{i.get('code')}] {i['msg']}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--from-google", action="store_true", help="Read TMT ATLAS from Google Sheet")
    ap.add_argument("--pid", help="Inspect one project row")
    ap.add_argument("--json", action="store_true", help="Print JSON summary to stdout")
    ap.add_argument(
        "--sync-stats",
        action="store_true",
        help="Update tmt-projects/data/atlas_stats.json overview from sheet (map logic)",
    )
    args = ap.parse_args()

    cfg = load_config()
    sheet_df = _load_sheet(cfg, from_google=args.from_google)
    sheet_df = normalize_sheet_frame(sheet_df)

    try:
        deployed_df = load_deployed_map_csv(cfg)
    except FileNotFoundError as e:
        print(e, file=sys.stderr)
        print("Tip: clone tmt-projects next to this repo or set paths.tmt_projects_dir", file=sys.stderr)
        return 1

    cmp = compare_frames(sheet_df, deployed_df, cfg)
    map_df = prepare_map_frame(sheet_df, cfg)
    sheet_kpi = compute_map_overview(map_df)
    stats_json = load_deployed_stats(cfg)

    records: list[dict] = []
    for i, row in sheet_df.iterrows():
        d = row_to_dict(row)
        if not strip_cell(d.get("Project ID")):
            continue
        rec = audit_row_for_map(d, row_index=int(i) + 2, cfg=cfg)
        records.append(rec)

    if args.pid:
        return print_pid(records, args.pid)

    out_dir = ROOT / "reports"
    out_dir.mkdir(parents=True, exist_ok=True)
    md_path = out_dir / "map_verify.md"
    json_path = out_dir / "map_verify.json"
    write_markdown(md_path, cmp=cmp, records=records, stats_json=stats_json, sheet_kpi=sheet_kpi)
    json_path.write_text(
        json.dumps(
            {
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "compare": cmp,
                "sheet_kpi": sheet_kpi,
                "stats_json_overview": stats_json.get("overview"),
                "by_status": {
                    s: sum(1 for r in records if r["status"] == s) for s in ("ok", "warn", "error")
                },
                "issue_codes": _cell_summary(records),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    print(f"Sheet -> map: {cmp['sheet_map_rows']} rows | Deployed CSV: {cmp['deployed_map_rows']}")
    print(f"KPI datasets: sheet={sheet_kpi['datasets']} deployed={cmp['kpi_deployed']['datasets']}")
    if stats_json.get("overview"):
        pub = stats_json["overview"].get("datasets")
        if pub and int(pub) != sheet_kpi["datasets"]:
            print(f"  atlas_stats.json datasets={pub} — STALE, rebuild stats from sheet")
    ok = sum(1 for r in records if r["status"] == "ok")
    warn = sum(1 for r in records if r["status"] == "warn")
    err = sum(1 for r in records if r["status"] == "error")
    print(f"Row audit: OK={ok} warn={warn} error={err}")
    print(f"Report: {md_path}")
    if args.sync_stats:
        patch_deployed_stats_from_sheet(sheet_df, cfg, write=True)
        print(f"Updated {tmt_projects_root(cfg) / 'data' / 'atlas_stats.json'} overview from sheet")
    if args.json:
        print(json_path.read_text(encoding="utf-8"))
    return 0 if err == 0 and not cmp["only_sheet"] and not cmp["only_deployed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
