#!/usr/bin/env python3
"""
Поштучный аудит каталога: каждая из 123 строк Excel, каждое поле.

  python scripts/audit_project_organs.py              # полный отчёт (deep)
  python scripts/audit_project_organs.py --pid PXD012173   # один проект
  python scripts/audit_project_organs.py --organ Blood     # все проекты органа
  python scripts/audit_project_organs.py --shallow         # быстрый режим
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from atlas_agent.catalog.organ_classify import map_project
from atlas_agent.catalog.project_audit import audit_one, summarize_audits
from atlas_agent.catalog.row_deep_audit import (
    audit_row_deep,
    format_row_markdown,
    summarize_row_audits,
)
from atlas_agent.config import load_config
from atlas_agent.sources.projects_table import load_catalog, primary_project_id


def _row_dict(row) -> dict:
    return {k: ("" if v != v else v) for k, v in row.items()}


def _cross_row_duplicates(records: list[dict]) -> None:
    """Один PID в нескольких строках — сверить Organ между строками."""
    by_pid: dict[str, list[dict]] = {}
    for rec in records:
        by_pid.setdefault(rec["pid"], []).append(rec)
    for pid, group in by_pid.items():
        if len(group) < 2:
            continue
        organs_sets = [tuple(r["mapped"]["organs"]) for r in group]
        if len(set(organs_sets)) > 1:
            for r in group:
                r["issues"].append({
                    "code": "dup_pid_diff_organ",
                    "field": "Project ID",
                    "severity": "warn",
                    "msg": f"PID {pid} в {len(group)} строках с разным Organ/картой: "
                    f"строки {[x['row_index'] for x in group]}",
                })
                if r["status"] == "ok":
                    r["status"] = "warn"


def write_deep_markdown(records: list[dict], summary: dict, path: Path) -> None:
    lines = [
        "# Поштучный аудит строк TMT ATLAS",
        "",
        f"Сгенерировано: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        "",
        "## Сводка",
        "",
        f"- **Строк в листе:** {summary['rows']}",
        f"- **Уникальных Project ID:** {summary['unique_pids']}",
        f"- **OK:** {summary['by_status'].get('ok', 0)}",
        f"- **Warn:** {summary['by_status'].get('warn', 0)}",
        f"- **Error:** {summary['by_status'].get('error', 0)}",
        "",
        "### Material (по строкам)",
        "",
    ]
    labels = {
        "clC": "Cell lines · cancer",
        "clN": "Cell lines · normal",
        "tisC": "Tissue · cancer",
        "tisN": "Tissue · normal",
    }
    for k, lbl in labels.items():
        lines.append(f"- {lbl}: {summary['material_buckets'].get(k, 0)}")
    lines.append("")
    if summary.get("duplicate_pid_rows"):
        lines.append("### Дубли PID (несколько строк)")
        lines.append("")
        for pid, rows in sorted(summary["duplicate_pid_rows"].items()):
            lines.append(f"- **{pid}** — строки {rows}")
        lines.append("")
    lines.append("### Коды замечаний")
    lines.append("")
    for code, n in summary.get("issue_codes", {}).items():
        lines.append(f"- `{code}`: {n}")
    lines.append("")
    lines.append("# Все строки (поштучно)")
    lines.append("")
    for rec in records:
        lines.extend(format_row_markdown(rec))
    path.write_text("\n".join(lines), encoding="utf-8")


def _organ_column(rec: dict) -> str:
    for col, val in rec.get("fields", []):
        if col == "Organ":
            return str(val)
    return "—"


def print_one_project(records: list[dict], pid_query: str) -> int:
    """Point check: one Project ID vs map organs."""
    q = primary_project_id(pid_query.strip()).upper()
    hits = [r for r in records if primary_project_id(r.get("pid", "")).upper() == q]
    if not hits:
        print(f"Not in catalog: {pid_query}")
        return 1
    for rec in hits:
        text = "\n".join(format_row_markdown(rec))
        try:
            print(text)
        except UnicodeEncodeError:
            import sys
            sys.stdout.buffer.write((text + "\n").encode("utf-8", errors="replace"))
        print("")
    if len(hits) > 1:
        print(f"Note: {len(hits)} rows share PID {q} — compare Organ columns above.")
    return 0


def print_organ_filter(records: list[dict], organ: str) -> int:
    """List catalog rows mapped to a map organ key (e.g. Blood, Lung)."""
    organ_key = organ.strip().replace(" ", "_")
    hits = [r for r in records if organ_key in (r.get("mapped") or {}).get("organs", [])]
    if not hits:
        print(f"No projects on map for organ: {organ_key}")
        return 0
    print(f"Organ **{organ_key}** — {len(hits)} row(s)\n")
    print(f"{'PID':<22} {'Status':<6} {'Material':<8} Organ column (truncated)")
    print("-" * 90)
    for rec in sorted(hits, key=lambda x: x.get("pid", "")):
        col = _organ_column(rec)
        col = (col[:48] + "…") if len(col) > 48 else col
        mat = (rec.get("mapped") or {}).get("material", "")
        print(f"{rec['pid']:<22} {rec['status']:<6} {mat:<8} {col}")
    warn = sum(1 for r in hits if r["status"] != "ok")
    if warn:
        print(f"\n{warn} row(s) with warnings — run: python scripts/audit_project_organs.py --pid <PXD>")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Row-by-row catalog audit")
    ap.add_argument("--shallow", action="store_true", help="Old heuristic-only audit")
    ap.add_argument("--sync-maps", action="store_true", help="Refresh organ_maps.json from app.js")
    ap.add_argument("--pid", metavar="PXD", help="Check one project (print organ audit to stdout)")
    ap.add_argument("--organ", metavar="Organ", help="List projects on map for organ (e.g. Blood, Stomach)")
    args = ap.parse_args()

    if args.sync_maps:
        import subprocess

        subprocess.run([sys.executable, str(ROOT / "scripts" / "extract_organ_maps.py")], check=True)

    cfg = load_config()
    df = load_catalog(cfg)
    out_dir = ROOT / "reports"
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    if args.shallow:
        records = []
        for _, row in df.iterrows():
            d = _row_dict(row)
            mapped = map_project(d)
            if not mapped["pid"]:
                continue
            records.append(audit_one(d, mapped))
        summary = summarize_audits(records)
        md_path = out_dir / "project_organ_audit.md"
        json_path = out_dir / f"project_organ_audit_{stamp}.json"
        payload = {"summary": summary, "projects": records}
    else:
        records = []
        for i, row in df.iterrows():
            d = _row_dict(row)
            rec = audit_row_deep(d, row_index=int(i) + 2)  # Excel: row 1 = header
            if not rec["pid"]:
                rec["issues"].append({
                    "code": "missing_pid",
                    "field": "Project ID",
                    "severity": "error",
                    "msg": "Пустой Project ID",
                })
                rec["status"] = "error"
            records.append(rec)
        _cross_row_duplicates(records)
        summary = summarize_row_audits(records)
        md_path = out_dir / "project_row_audit.md"
        json_path = out_dir / f"project_row_audit_{stamp}.json"
        payload = {
            "generated": datetime.now(timezone.utc).isoformat(),
            "mode": "deep_row",
            "summary": summary,
            "rows": [
                {
                    "row_index": r["row_index"],
                    "pid": r["pid"],
                    "status": r["status"],
                    "issues": r["issues"],
                    "mapped": r["mapped"],
                    "field_organs": {k: v["organs"] for k, v in r["field_organs"].items()},
                }
                for r in records
            ],
        }
        write_deep_markdown(records, summary, md_path)

    if args.pid:
        return print_one_project(records, args.pid)
    if args.organ:
        return print_organ_filter(records, args.organ)

    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    print("Catalog audit", "(deep)" if not args.shallow else "(shallow)")
    print(f"  Rows: {summary.get('rows', summary.get('projects', '?'))}")
    print(f"  Status: {summary.get('by_status', {})}")
    if not args.shallow:
        print(f"  MD: {md_path} ({md_path.stat().st_size // 1024} KB)")
    print(f"  JSON: {json_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
