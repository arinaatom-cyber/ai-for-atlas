"""HTML-страница: TMT-каналы + матрица + нормализация."""
from __future__ import annotations

from pathlib import Path


def render_tmt_html(project_id: str, view: dict) -> str:
    ch = view.get("channels") or []
    by_role = view.get("channels_by_role") or {}
    norm = view.get("normalization") or {}
    matrix = view.get("matrix") or {}
    design = view.get("sample_design") or {}

    def rows_channel(items):
        if not items:
            return "<tr><td colspan='4'>—</td></tr>"
        return "".join(
            f"<tr><td><b>{c.get('tag')}</b></td><td>{c.get('label')}</td>"
            f"<td>{c.get('role_ru')}</td><td>{c.get('from_column','')}</td></tr>"
            for c in items
        )

    raw_cols = matrix.get("raw_channel_columns") or []
    ratio_cols = matrix.get("ratio_columns") or []
    preview = matrix.get("protein_preview") or []

    preview_html = ""
    if preview and raw_cols:
        hdr = "".join(f"<th>{c[:20]}</th>" for c in raw_cols[:8])
        body = ""
        id_key = matrix.get("protein_id_column") or list(preview[0].keys())[0]
        for row in preview[:12]:
            pid = str(row.get("_id") or row.get(id_key, ""))[:30]
            cells = "".join(
                f"<td>{row.get(c, '')}</td>" for c in raw_cols[:8] if c in row
            )
            body += f"<tr><td>{pid}</td>{cells}</tr>"
        preview_html = f"<table class='matrix'><tr><th>Protein</th>{hdr}</tr>{body}</table>"

    hints = "".join(f"<li>{h}</li>" for h in norm.get("matrix_hints") or [])
    stats = matrix.get("column_stats") or {}
    stats_html = "".join(
        f"<li><code>{k}</code>: min={v.get('min')} med={v.get('median')} max={v.get('max')}</li>"
        for k, v in list(stats.items())[:10]
    )

    return f"""<!DOCTYPE html>
<html lang="ru"><head>
<meta charset="utf-8"/>
<title>TMT {project_id}</title>
<style>
body {{ font-family:Segoe UI,sans-serif; background:#0f1419; color:#e7ecf3; margin:0; padding:24px; }}
h1 {{ color:#6cb6ff; }}
.card {{ background:#1a2332; border-radius:10px; padding:16px; margin:16px 0; border:1px solid #2a3548; }}
table {{ width:100%; border-collapse:collapse; font-size:.85rem; }}
th,td {{ padding:8px; border-bottom:1px solid #2a3548; text-align:left; }}
th {{ color:#8b9cb3; }}
.ref {{ color:#3dd68c; }} .ctrl {{ color:#6cb6ff; }} .case {{ color:#f07178; }}
.matrix {{ overflow-x:auto; }}
code {{ background:#121a24; padding:2px 6px; border-radius:4px; }}
</style></head>
<body>
<h1>TMT: {project_id}</h1>
<div class="card">
  <h2>Дизайн образцов (таблица)</h2>
  <ul>
    <li>Control Healthy: {design.get('control_healthy','—')}</li>
    <li>Case untreated: {design.get('case_untreated','—')}</li>
    <li>Case treated: {design.get('case_treated','—')}</li>
    <li>Patients: {design.get('patients','—')}</li>
    <li>Samples used: {design.get('samples_used','—')}</li>
  </ul>
</div>
<div class="card">
  <h2>Каналы по роли</h2>
  <h3 class="ref">Reference</h3>
  <table><tr><th>Tag</th><th>Label</th><th>Role</th><th>CSV column</th></tr>{rows_channel(by_role.get('reference'))}</table>
  <h3 class="ctrl">Control / здоровый</h3>
  <table><tr><th>Tag</th><th>Label</th><th>Role</th><th>CSV column</th></tr>{rows_channel(by_role.get('control'))}</table>
  <h3 class="case">Case / воздействие</h3>
  <table><tr><th>Tag</th><th>Label</th><th>Role</th><th>CSV column</th></tr>{rows_channel(by_role.get('case'))}</table>
  <h3>Не классифицировано</h3>
  <table><tr><th>Tag</th><th>Label</th><th>Role</th><th>CSV column</th></tr>{rows_channel(by_role.get('unknown'))}</table>
</div>
<div class="card">
  <h2>Нормализация</h2>
  <p><b>Из CSV:</b> {norm.get('strategy_sheet','')}</p>
  <p><b>Quantification_Format:</b> {norm.get('quantification_format','')}</p>
  <p>{norm.get('interpretation','')}</p>
  <ul>{hints}</ul>
</div>
<div class="card">
  <h2>Матрица белков</h2>
  <p>Файл: <code>{matrix.get('path', 'не найден')}</code></p>
  <p>Сырые каналы: {len(raw_cols)} · ratio-колонки: {len(ratio_cols)}</p>
  <ul>{stats_html}</ul>
  {preview_html or '<p>Нет превью (файл не найден или не распознан)</p>'}
</div>
</body></html>"""


def save_tmt_view_html(project_id: str, view: dict, out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"tmt_view_{project_id}.html"
    path.write_text(render_tmt_html(project_id, view), encoding="utf-8")
    return path
