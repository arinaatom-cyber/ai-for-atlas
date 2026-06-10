"""HTML-страница новых проектов Discovery (без Streamlit)."""
from __future__ import annotations

import html
import json
from datetime import datetime
from pathlib import Path


def _source_label(item: dict) -> str:
    acc = (item.get("project_accession") or item.get("accession") or "").upper()
    src = item.get("source") or item.get("consortium") or ""
    if acc.startswith("PDC") or src == "pdc_api":
        return "PDC"
    if acc.startswith("PXD") or "pride" in str(src).lower():
        return "PRIDE"
    if acc.startswith("MSV"):
        return "MassIVE"
    if acc.startswith("IPX"):
        return "iProX"
    return str(src) or "other"


def _project_rows(items: list[dict]) -> str:
    rows = []
    for it in items:
        acc = html.escape(it.get("project_accession") or it.get("accession") or "—")
        title = html.escape((it.get("title") or "")[:140])
        src = html.escape(_source_label(it))
        plex = it.get("inferred_plex") or ""
        design = html.escape(str(it.get("sample_design") or ""))
        sim = (it.get("similar_in_catalog") or [{}])[0]
        sim_id = html.escape(str(sim.get("project_id") or ""))
        sim_score = sim.get("score", "")
        url = it.get("url") or ""
        if not url and acc.startswith("PXD"):
            url = f"https://www.ebi.ac.uk/pride/archive/projects/{acc}"
        elif not url and acc.startswith("PDC"):
            url = f"https://proteomic.datacommons.cancer.gov/pdc/study/{acc}"
        link = f'<a href="{html.escape(url)}" target="_blank" rel="noopener">open</a>' if url else ""
        program = html.escape(str(it.get("program") or it.get("disease") or "")[:60])
        rows.append(
            f"<tr data-src='{src.lower()}' data-search='{acc.lower()} {title.lower()} {program.lower()}'>"
            f"<td><b>{acc}</b></td><td>{title}</td><td>{src}</td>"
            f"<td>{plex}</td><td>{design}</td><td>{sim_id} ({sim_score})</td>"
            f"<td>{program}</td><td>{link}</td></tr>"
        )
    return "\n".join(rows) or "<tr><td colspan='8'>Нет новых проектов</td></tr>"


def generate_discovery_html(report: dict, out_path: str | Path | None = None) -> Path:
    s = report.get("summary") or {}
    # Только новые candidates — никогда каталог projects.csv
    items = report.get("candidates") or report.get("new_projects") or []
    stats = s.get("source_stats") or {}
    gen = (report.get("generated_at") or "")[:19].replace("T", " ")

    pride_n = sum(1 for x in items if _source_label(x) == "PRIDE")
    pdc_n = sum(1 for x in items if _source_label(x) == "PDC")
    other_n = len(items) - pride_n - pdc_n

    out = Path(out_path or "reports/discovery_index.html")
    out.parent.mkdir(parents=True, exist_ok=True)

    page = f"""<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>Atlas Discovery — новые проекты</title>
  <style>
    :root {{ --bg:#0f1419; --card:#1a2332; --text:#e7ecf3; --muted:#8b9cb3; --ok:#3dd68c; --accent:#6cb6ff; --warn:#f0c14d; }}
    * {{ box-sizing:border-box; }}
    body {{ margin:0; font-family:Segoe UI,system-ui,sans-serif; background:var(--bg); color:var(--text); }}
    header {{ padding:24px 32px; border-bottom:1px solid #2a3548; }}
    h1 {{ margin:0 0 6px; font-size:1.7rem; color:var(--accent); }}
    .sub {{ color:var(--muted); margin:0; }}
    .toolbar {{ padding:16px 32px; display:flex; flex-wrap:wrap; gap:12px; align-items:center; border-bottom:1px solid #2a3548; }}
    input[type=search] {{ flex:1; min-width:220px; padding:10px 14px; border-radius:8px; border:1px solid #2a3548; background:#121a24; color:var(--text); }}
    .chip {{ padding:8px 14px; border-radius:20px; border:1px solid #2a3548; background:#121a24; cursor:pointer; color:var(--muted); }}
    .chip.active {{ border-color:var(--accent); color:var(--accent); }}
    .kpis {{ display:flex; gap:14px; flex-wrap:wrap; padding:20px 32px; }}
    .kpi {{ background:var(--card); border:1px solid #2a3548; border-radius:10px; padding:14px 18px; min-width:120px; }}
    .kpi b {{ display:block; font-size:1.6rem; color:var(--accent); }}
    .kpi span {{ color:var(--muted); font-size:.85rem; }}
    main {{ padding:0 32px 32px; }}
    .table-wrap {{ overflow-x:auto; background:var(--card); border-radius:12px; border:1px solid #2a3548; }}
    table {{ width:100%; border-collapse:collapse; font-size:.88rem; }}
    th,td {{ text-align:left; padding:10px 12px; border-bottom:1px solid #2a3548; vertical-align:top; }}
    th {{ color:var(--muted); position:sticky; top:0; background:#1e2838; }}
    tr:hover td {{ background:#121a24; }}
    a {{ color:var(--accent); }}
    .badge {{ display:inline-block; background:#1e3a2f; color:var(--ok); padding:3px 10px; border-radius:12px; font-size:.75rem; }}
    #count {{ color:var(--muted); margin-left:auto; }}
  </style>
</head>
<body>
  <header>
    <h1>Atlas Discovery — новые проекты</h1>
    <p class="sub">PXD · PDC · MSV · IPX · <b>только НЕ в каталоге</b> · обновлено {gen} UTC</p>
    <p class="sub"><span class="badge">projects.csv не на сайте</span> <span class="badge">каталог: {s.get('catalog_unique_ids', '?')} ID (скрыт)</span></p>
  </header>
  <div class="kpis">
    <div class="kpi"><b>{len(items)}</b><span>всего новых</span></div>
    <div class="kpi"><b>{pride_n}</b><span>PRIDE (PXD)</span></div>
    <div class="kpi"><b>{pdc_n}</b><span>PDC</span></div>
    <div class="kpi"><b>{other_n}</b><span>другие</span></div>
    <div class="kpi"><b>{stats.get('pride_v3_search', 0)}</b><span>PRIDE API</span></div>
    <div class="kpi"><b>{stats.get('pdc_uiStudySummary', 0)}</b><span>PDC API</span></div>
  </div>
  <div class="toolbar">
    <input type="search" id="q" placeholder="Поиск по ID, названию, болезни…"/>
    <button class="chip active" data-filter="all">Все</button>
    <button class="chip" data-filter="pride">PRIDE</button>
    <button class="chip" data-filter="pdc">PDC</button>
    <button class="chip" data-filter="other">Другие</button>
    <span id="count"></span>
  </div>
  <main>
    <div class="table-wrap">
      <table id="tbl">
        <thead>
          <tr>
            <th>ID</th><th>Название</th><th>Источник</th><th>Plex</th>
            <th>Дизайн</th><th>Похож на</th><th>Программа/болезнь</th><th></th>
          </tr>
        </thead>
        <tbody>
          {_project_rows(items)}
        </tbody>
      </table>
    </div>
  </main>
  <script>
    const q = document.getElementById('q');
    const tbl = document.getElementById('tbl');
    const rows = [...tbl.querySelectorAll('tbody tr')];
    const count = document.getElementById('count');
    let filter = 'all';
    function apply() {{
      const term = (q.value || '').toLowerCase().trim();
      let visible = 0;
      rows.forEach(r => {{
        const src = (r.dataset.src || '');
        const search = (r.dataset.search || '');
        const srcOk = filter === 'all'
          || (filter === 'pride' && src === 'pride')
          || (filter === 'pdc' && src === 'pdc')
          || (filter === 'other' && src !== 'pride' && src !== 'pdc');
        const textOk = !term || search.includes(term);
        const show = srcOk && textOk;
        r.style.display = show ? '' : 'none';
        if (show) visible++;
      }});
      count.textContent = visible + ' / {len(items)}';
    }}
    q.addEventListener('input', apply);
    document.querySelectorAll('.chip').forEach(btn => {{
      btn.addEventListener('click', () => {{
        document.querySelectorAll('.chip').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        filter = btn.dataset.filter;
        apply();
      }});
    }});
    apply();
  </script>
</body>
</html>"""
    out.write_text(page, encoding="utf-8")
    return out
