"""HTML-дашборд платформы Atlas (без внешних зависимостей)."""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import pandas as pd

from atlas_agent.workflow.completeness import audit_table, row_completeness
from atlas_agent.sources.projects_table import load_projects_table, primary_project_id


def _latest_json(reports_dir: Path, prefix: str) -> dict | None:
    files = sorted(reports_dir.glob(f"{prefix}_*.json"), reverse=True)
    for f in files:
        try:
            return json.loads(f.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
    return None


def _bar_row(label: str, value: int, total: int, color: str) -> str:
    pct = (100 * value / total) if total else 0
    return f"""
    <div class="bar-row">
      <span class="lbl">{label}</span>
      <div class="track"><div class="fill" style="width:{pct:.1f}%;background:{color}"></div></div>
      <span class="num">{value}</span>
    </div>"""


def generate_dashboard(
    *,
    csv_path: str,
    reports_dir: str,
    out_path: str | None = None,
) -> Path:
    df = load_projects_table(csv_path)
    audit = audit_table(df)
    rep = Path(reports_dir)
    scan = _latest_json(rep, "revisor_scan") or {}
    audit_rep = _latest_json(rep, "revisor_audit") or {}
    discovery_hist = Path(reports_dir).parent / "data" / "discovery_history" / "latest.json"
    discovery = {}
    if discovery_hist.is_file():
        try:
            discovery = json.loads(discovery_hist.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            discovery = {}
    disc_summary = discovery.get("summary") or {}
    disc_projects = discovery.get("new_projects") or []

    status_counts = audit["status"].value_counts().to_dict()
    total = len(audit)
    complete = status_counts.get("complete", 0)
    partial = status_counts.get("partial", 0)
    todo = status_counts.get("todo", 0)

    norm_col = "Normalization Strategy"
    norm_top = []
    if norm_col in df.columns:
        s = df[norm_col].fillna("(пусто)").astype(str).str.strip()
        s = s.replace({"": "(пусто)", "Not specified": "(не указано)"})
        norm_top = list(s.value_counts().head(8).items())

    new_pride = scan.get("new_pride") or []
    new_pubs = scan.get("new_publications") or []

    rows_html = ""
    for _, r in audit[audit["status"] != "complete"].head(25).iterrows():
        rows_html += (
            f"<tr><td>{r['project_id']}</td><td>{r['status']}</td>"
            f"<td>{r['score_pct']}%</td><td>{r['missing'][:80]}</td></tr>"
        )

    pride_rows = ""
    for p in new_pride[:12]:
        sim = p.get("similar_in_catalog") or []
        sim_s = ", ".join(f"{s['project_id']}({s['score']})" for s in sim[:2]) or "—"
        pride_rows += (
            f"<tr><td>{p.get('accession','')}</td><td>{(p.get('title') or '')[:70]}</td>"
            f"<td>{p.get('submission_date','')}</td><td>{sim_s}</td></tr>"
        )

    pub_rows = ""
    for p in new_pubs[:12]:
        pxds = ", ".join(p.get("pxd_mentioned") or []) or "—"
        pub_rows += (
            f"<tr><td>{p.get('pmid','')}</td><td>{pxds}</td>"
            f"<td>{(p.get('title') or '')[:70]}</td></tr>"
        )

    disc_rows = ""
    for p in disc_projects[:20]:
        acc = p.get("project_accession") or p.get("accession") or ""
        src = p.get("source") or p.get("consortium") or ""
        sim = (p.get("similar_in_catalog") or [{}])[0]
        disc_rows += (
            f"<tr><td><b>{acc}</b></td><td>{src[:20]}</td>"
            f"<td>{(p.get('title') or '')[:65]}</td>"
            f"<td>{sim.get('project_id','')}</td></tr>"
        )
    disc_stats = disc_summary.get("source_stats") or {}
    disc_new = disc_summary.get("new_projects", len(disc_projects))

    err = (audit_rep.get("counts") or {}).get("error", "?")
    warn = (audit_rep.get("counts") or {}).get("warning", "?")

    html = f"""<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="utf-8"/>
  <title>Atlas TMT Platform</title>
  <style>
    :root {{ --bg:#0f1419; --card:#1a2332; --text:#e7ecf3; --muted:#8b9cb3; --ok:#3dd68c; --warn:#f0c14d; --bad:#f07178; --accent:#6cb6ff; }}
    * {{ box-sizing:border-box; }}
    body {{ margin:0; font-family:Segoe UI,system-ui,sans-serif; background:var(--bg); color:var(--text); }}
    header {{ padding:24px 32px; border-bottom:1px solid #2a3548; }}
    h1 {{ margin:0 0 8px; font-size:1.6rem; }}
    .sub {{ color:var(--muted); }}
    main {{ padding:24px 32px; display:grid; gap:20px; grid-template-columns:repeat(auto-fit,minmax(320px,1fr)); }}
    .card {{ background:var(--card); border-radius:12px; padding:20px; border:1px solid #2a3548; }}
    .card h2 {{ margin:0 0 16px; font-size:1.1rem; color:var(--accent); }}
    .kpis {{ display:flex; gap:16px; flex-wrap:wrap; }}
    .kpi {{ background:#121a24; padding:12px 16px; border-radius:8px; min-width:100px; }}
    .kpi b {{ display:block; font-size:1.5rem; }}
    .kpi span {{ color:var(--muted); font-size:.85rem; }}
    .bar-row {{ display:grid; grid-template-columns:120px 1fr 40px; gap:8px; align-items:center; margin:6px 0; font-size:.9rem; }}
    .track {{ height:10px; background:#121a24; border-radius:4px; overflow:hidden; }}
    .fill {{ height:100%; border-radius:4px; }}
    table {{ width:100%; border-collapse:collapse; font-size:.85rem; }}
    th,td {{ text-align:left; padding:8px; border-bottom:1px solid #2a3548; }}
    th {{ color:var(--muted); }}
    .full {{ grid-column:1/-1; }}
  </style>
</head>
<body>
  <header>
    <h1>Atlas TMT Proteomics Platform</h1>
    <p class="sub">Обновлено {datetime.now().strftime('%Y-%m-%d %H:%M')} · строк {len(df)} · уникальных PXD {audit['project_id'].nunique()}</p>
  </header>
  <main>
    <section class="card">
      <h2>Полнота каталога</h2>
      <div class="kpis">
        <div class="kpi"><b style="color:var(--ok)">{complete}</b><span>complete</span></div>
        <div class="kpi"><b style="color:var(--warn)">{partial}</b><span>partial</span></div>
        <div class="kpi"><b style="color:var(--bad)">{todo}</b><span>todo</span></div>
      </div>
      {_bar_row("complete", complete, total, "var(--ok)")}
      {_bar_row("partial", partial, total, "var(--warn)")}
      {_bar_row("todo", todo, total, "var(--bad)")}
    </section>
    <section class="card">
      <h2>Ревизор</h2>
      <div class="kpis">
        <div class="kpi"><b style="color:var(--bad)">{err}</b><span>ошибки</span></div>
        <div class="kpi"><b style="color:var(--warn)">{warn}</b><span>предупр.</span></div>
      </div>
      <p class="sub">Скан {scan.get('year_from', '?')}–{scan.get('year_to', '?')}: PRIDE JSON {len(new_pride)} · статьи {len(new_pubs)}</p>
    </section>
    <section class="card">
      <h2>Нормализация (топ)</h2>
      {"".join(_bar_row(str(k)[:40], int(v), len(df), "var(--accent)") for k, v in norm_top) or "<p class='sub'>Нет данных</p>"}
    </section>
    <section class="card full">
      <h2>Discovery Agent — новые проекты</h2>
      <p class="sub">Всего <b>{disc_new}</b> · PRIDE API {disc_stats.get('pride_v3_search', 0)} · PDC {disc_stats.get('pdc_uiStudySummary', 0)}
        · <a href="discovery_index.html" style="color:var(--accent)">полный список → discovery_index.html</a></p>
      <table><tr><th>ID</th><th>Source</th><th>Title</th><th>Похож на</th></tr>{disc_rows or "<tr><td colspan=4>Запустите python run_discovery.py scan</td></tr>"}</table>
    </section>
    <section class="card full">
      <h2>Revisor — новые PRIDE (JSON)</h2>
      <table><tr><th>PXD</th><th>Title</th><th>Date</th><th>Похожие в каталоге</th></tr>{pride_rows or "<tr><td colspan=4>Нет кандидатов — run_revisor.py scan</td></tr>"}</table>
    </section>
    <section class="card full">
      <h2>Новые публикации 2026</h2>
      <table><tr><th>PMID</th><th>PXD в тексте</th><th>Title</th></tr>{pub_rows or "<tr><td colspan=3>Нет данных</td></tr>"}</table>
    </section>
    <section class="card full">
      <h2>Требуют доработки (топ-25)</h2>
      <table><tr><th>PXD</th><th>Status</th><th>%</th><th>Missing</th></tr>{rows_html}</table>
    </section>
  </main>
</body>
</html>"""

    out = Path(out_path or Path(reports_dir) / "dashboard.html")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")
    return out
