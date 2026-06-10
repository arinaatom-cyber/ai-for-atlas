"""Пакетный TMT-обзор по всем проектам каталога."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from atlas_agent.analysis.tmt_channels import build_tmt_view
from atlas_agent.sources.projects_table import primary_project_id
from atlas_agent.viz.tmt_view import save_tmt_view_html


def iter_tmt_projects(df: pd.DataFrame) -> list[tuple[str, pd.Series]]:
    """Уникальные TMT-проекты (первая строка на PXD)."""
    if "TMT Label (Unified)" not in df.columns:
        return []
    mask = df["TMT Label (Unified)"].astype(str).str.contains("TMT", case=False, na=False)
    seen: set[str] = set()
    out: list[tuple[str, pd.Series]] = []
    for _, row in df[mask].iterrows():
        pid = primary_project_id(str(row.get("Project ID", "")))
        if not pid or pid in seen:
            continue
        seen.add(pid)
        out.append((pid, row))
    return sorted(out, key=lambda x: x[0])


def summarize_view(pid: str, view: dict) -> dict[str, Any]:
    ch = view.get("channels") or []
    by = view.get("channels_by_role") or {}
    m = view.get("matrix") or {}
    return {
        "project_id": pid,
        "n_channels": len(ch),
        "n_reference": len(by.get("reference") or []),
        "n_control": len(by.get("control") or []),
        "n_case": len(by.get("case") or []),
        "n_unknown": len(by.get("unknown") or []),
        "normalization": (view.get("normalization") or {}).get("strategy_sheet", ""),
        "matrix_found": bool(m.get("found")),
        "raw_cols": len(m.get("raw_channel_columns") or []),
        "ratio_cols": len(m.get("ratio_columns") or []),
        "matrix_file": Path(m.get("path", "")).name if m.get("path") else "",
        "channels_short": "; ".join(f"{c['tag']}={c['label'][:25]}" for c in ch[:6]),
    }


def run_tmt_batch(
    df: pd.DataFrame,
    tmt_root: str,
    out_dir: Path,
    *,
    html: bool = True,
    limit: int = 0,
    only_with_matrix: bool = False,
) -> dict[str, Any]:
    projects = iter_tmt_projects(df)
    if limit > 0:
        projects = projects[:limit]

    rows: list[dict] = []
    html_links: list[dict] = []
    errors: list[dict] = []

    for pid, row in projects:
        try:
            view = build_tmt_view(row, tmt_root, quick=True)
            summary = summarize_view(pid, view)
            if only_with_matrix and not summary["matrix_found"]:
                continue
            rows.append(summary)
            if html:
                hp = save_tmt_view_html(pid, view, out_dir / "tmt_views")
                html_links.append({"project_id": pid, "html": str(hp)})
        except Exception as e:
            errors.append({"project_id": pid, "error": str(e)})

    summary_df = pd.DataFrame(rows)
    csv_path = out_dir / "tmt_channels_summary.csv"
    if not summary_df.empty:
        summary_df.to_csv(csv_path, index=False, encoding="utf-8-sig")

    index_path = out_dir / "tmt_index.html"
    if html:
        index_path.write_text(
            _render_index(html_links, summary_df, errors),
            encoding="utf-8",
        )

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_tmt_projects": len(projects),
        "processed": len(rows),
        "errors": len(errors),
        "csv": str(csv_path),
        "index_html": str(index_path) if html else None,
        "html_dir": str(out_dir / "tmt_views") if html else None,
        "error_samples": errors[:10],
    }


def _render_index(links: list[dict], df: pd.DataFrame, errors: list[dict]) -> str:
    rows = ""
    for link in links:
        pid = link["project_id"]
        sub = df[df["project_id"] == pid].iloc[0] if not df.empty and pid in df["project_id"].values else None
        mat = "да" if sub is not None and sub.get("matrix_found") else "нет"
        rel = Path(link["html"]).name
        n_ch = int(sub["n_channels"]) if sub is not None else 0
        rows += (
            f'<tr><td><a href="tmt_views/{rel}">{pid}</a></td>'
            f"<td>{n_ch}</td><td>{mat}</td>"
            f"<td>{(sub['channels_short'] if sub is not None else '')[:80]}</td></tr>"
        )
    err_block = ""
    if errors:
        err_block = "<h2>Ошибки</h2><ul>" + "".join(
            f"<li>{e['project_id']}: {e['error'][:80]}</li>" for e in errors[:20]
        ) + "</ul>"

    return f"""<!DOCTYPE html>
<html lang="ru"><head><meta charset="utf-8"/>
<title>Atlas — все TMT проекты</title>
<style>
body {{ font-family:Segoe UI,sans-serif; background:#0f1419; color:#e7ecf3; padding:24px; }}
table {{ width:100%; border-collapse:collapse; }}
th,td {{ padding:8px; border-bottom:1px solid #2a3548; text-align:left; }}
a {{ color:#6cb6ff; }}
</style></head><body>
<h1>TMT — ваши проекты ({len(links)})</h1>
<p>Сводка: <code>tmt_channels_summary.csv</code></p>
<table>
<tr><th>PXD</th><th>Каналов</th><th>Матрица</th><th>Каналы (начало)</th></tr>
{rows}
</table>
{err_block}
</body></html>"""
