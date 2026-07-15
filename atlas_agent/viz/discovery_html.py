"""HTML Discovery: one unified table (projects + papers + cohorts)."""
from __future__ import annotations

import html
import re
from pathlib import Path

from atlas_agent.viz.discovery_table_shared import (
    _papers_without_accession,
    build_unified_discovery_rows,
    source_label,
)
from atlas_agent.viz.site_components import (
    kpi_grid,
    meta_pill_i18n,
    meta_pill_text,
    meta_time,
    note_i18n,
    page_hero,
    section_desc,
    section_head,
)
from atlas_agent.viz.site_theme import page_wrap


def _pub_index(pubs: list[dict], extra: list[dict] | None = None) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for p in (extra or []) + pubs:
        pmid = re.sub(r"\D", "", str(p.get("pmid") or ""))
        if pmid:
            out[pmid] = p
    return out


def _methods_panel(report: dict) -> str:
    m = report.get("methods_manifest") or {}
    s = report.get("summary") or {}
    st = s.get("source_stats") or {}
    qm = report.get("quality_metrics") or s.get("quality_metrics") or {}
    lit_b = qm.get("benchmark_literature") or {}
    proj_b = qm.get("benchmark_projects") or {}
    funnel = m.get("funnel") or {}
    lit = m.get("literature_screening") or {}
    inc = m.get("inclusion_criteria") or {}
    exc = m.get("exclusion_criteria") or []

    exc_li = "".join(f"<li>{html.escape(str(x))}</li>" for x in exc[:6])
    return f"""
<section class="section methods-panel" id="methods">
  <h2 class="section-title" data-i18n="sec_methods"></h2>
  <p class="section-desc" data-i18n="sec_methods_desc"></p>
  <div class="methods-grid">
    <div class="methods-card">
      <h3 data-i18n="methods_funnel"></h3>
      <ul class="methods-stats">
        <li>Raw repos (PRIDE+PDC): <b>{st.get('pride_v3_search', 0) + st.get('pdc_uiStudySummary', 0)}</b></li>
        <li>Candidates: <b>{funnel.get('candidates', s.get('candidates', 0))}</b></li>
        <li>Technical filtered: <b>{funnel.get('filtered_out', s.get('filtered_out', 0))}</b></li>
        <li>Literature LLM-read: <b>{lit.get('abstract_llm_read', st.get('abstract_llm_read', 0))}</b></li>
        <li>IDs resolved (EPMC DA): <b>{lit.get('literature_resolved', st.get('literature_resolved', 0))}</b></li>
      </ul>
    </div>
    <div class="methods-card">
      <h3 data-i18n="methods_confidence"></h3>
      <p data-i18n="methods_tier_legend"></p>
      <ul class="methods-stats">
        <li>Benchmark literature: <b>{lit_b.get('correct', '?')}/{lit_b.get('n', '?')}</b></li>
        <li>Benchmark projects: <b>{proj_b.get('correct', '?')}/{proj_b.get('n', '?')}</b></li>
      </ul>
    </div>
    <div class="methods-card">
      <h3 data-i18n="methods_inclusion"></h3>
      <ul class="methods-stats">
        <li>{html.escape(str(inc.get('organism', '')))}</li>
        <li>{html.escape(str(inc.get('quantification', '')))}</li>
        <li>{html.escape(str(inc.get('omics_layer', '')))}</li>
      </ul>
      <h4 data-i18n="methods_exclusion"></h4>
      <ul class="methods-stats">{exc_li}</ul>
    </div>
  </div>
</section>"""


def generate_discovery_html(report: dict, out_path: str | Path | None = None, *, deploy: str = "docs_site") -> Path:
    s = report.get("summary") or {}
    items = report.get("candidates") or report.get("new_projects") or []
    pubs = report.get("publications_analyzed") or []
    manual = report.get("manual_check") or []
    literature = report.get("literature_semantic") or []
    papers = _papers_without_accession(manual, literature)
    cohorts = report.get("cohort_literature") or []
    gen = report.get("generated_at") or ""
    pubs_by_pmid = _pub_index(
        pubs,
        (report.get("manual_check") or []) + (report.get("literature_semantic") or []),
    )

    pride_n = sum(1 for x in items if source_label(x) == "PRIDE")
    pdc_n = sum(1 for x in items if source_label(x) == "PDC")
    table_n = sum(
        1 for x in items
        if (x.get("data_availability") or {}).get("status") == "quant_table"
    )

    unified_rows, total_rows = build_unified_discovery_rows(items, papers, cohorts, pubs_by_pmid)

    qc_link = '<p class="note-box"><a href="qc.html">QC report</a> — manual review &amp; rejected (separate page).</p>'

    body = (
        page_hero(
            "disc_title",
            "disc_lead",
            meta_time(gen)
            + meta_pill_i18n("disc_catalog_hidden", css="badge-ok")
            + meta_pill_text(f"{s.get('catalog_unique_ids', '?')}")
            + ' <span class="meta-pill badge badge-muted" data-i18n="disc_catalog_n"></span>',
        )
        + kpi_grid(
            [
                (str(len(items)), "kpi_new"),
                (str(table_n), "kpi_with_table"),
                (str(len(papers)), "kpi_papers_no_id"),
                (str(len(cohorts)), "kpi_cohorts"),
                (str(pride_n), "kpi_pride"),
                (str(pdc_n), "kpi_pdc"),
            ]
        )
        + f"""
<div class="page-content page-content-wide">
  <section class="section" id="discovery">
    {section_head("sec_unified_discovery", total_rows)}
    {section_desc("sec_unified_discovery_desc")}
    {note_i18n("note_unified_table")}
    {_methods_panel(report)}
    <div class="toolbar" id="disc-toolbar">
      <input type="search" id="q" data-i18n-placeholder="search_unified"/>
      <button type="button" class="chip" data-tfilter="all" data-i18n="filter_all"></button>
      <button type="button" class="chip active" data-tfilter="project" data-i18n="filter_projects"></button>
      <button type="button" class="chip" data-tfilter="paper" data-i18n="filter_papers"></button>
      <button type="button" class="chip" data-tfilter="cohort" data-i18n="filter_cohorts"></button>
      <button type="button" class="chip" data-sfilter="all" data-i18n="filter_all_src"></button>
      <button type="button" class="chip" data-sfilter="pride" data-i18n="filter_pride"></button>
      <button type="button" class="chip" data-sfilter="pdc" data-i18n="filter_pdc"></button>
      <button type="button" class="chip" data-sfilter="epmc" data-i18n="filter_epmc"></button>
      <span class="count-badge" id="count"></span>
    </div>
    <div class="table-wrap table-standard table-unified">
      <table id="tbl-unified" class="data-table">
        <thead>
          <tr class="head-groups">
            <th colspan="4" class="th-group" data-i18n="th_group_record"></th>
            <th colspan="5" class="th-group col-split" data-i18n="th_group_context"></th>
            <th colspan="6" class="th-group col-split" data-i18n="th_group_details"></th>
          </tr>
          <tr>
          <th class="col-type" data-i18n="th_type"></th>
          <th class="col-id"><span class="th-main" data-i18n="th_project_id"></span><span class="th-hint" data-i18n="th_project_id_hint"></span></th>
          <th data-i18n="th_year"></th>
          <th data-i18n="th_title"></th>
          <th data-i18n="th_source" class="col-split"></th>
          <th data-i18n="th_design"></th>
          <th data-i18n="th_omics"></th>
          <th data-i18n="th_patients"></th>
          <th data-i18n="th_n"></th>
          <th data-i18n="th_verdict" class="col-split"></th>
          <th data-i18n="th_confidence"></th>
          <th data-i18n="th_fit"></th>
          <th data-i18n="th_analysis"></th>
          <th data-i18n="th_data"></th>
          <th data-i18n="th_links"></th>
        </tr></thead>
        <tbody>{unified_rows}</tbody>
      </table>
    </div>
  </section>

  {qc_link}
</div>

<script>
(function() {{
  const q = document.getElementById('q');
  const tbl = document.getElementById('tbl-unified');
  const rows = tbl ? [...tbl.querySelectorAll('tbody tr')] : [];
  const count = document.getElementById('count');
  let tFilter = 'project';
  let sFilter = 'all';
  function apply() {{
    const term = (q?.value || '').toLowerCase().trim();
    let visible = 0;
    rows.forEach(r => {{
      const typ = (r.dataset.type || '');
      const src = (r.dataset.src || '');
      const search = (r.dataset.search || '');
      const typeOk = tFilter === 'all' || typ === tFilter;
      const srcOk = sFilter === 'all' || src === sFilter;
      const textOk = !term || search.includes(term);
      const show = typeOk && srcOk && textOk;
      r.style.display = show ? '' : 'none';
      if (show) visible++;
    }});
    if (count) count.textContent = visible + ' / {total_rows}';
  }}
  q?.addEventListener('input', apply);
  document.querySelectorAll('#disc-toolbar .chip[data-tfilter]').forEach(btn => {{
    btn.addEventListener('click', () => {{
      document.querySelectorAll('#disc-toolbar .chip[data-tfilter]').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      tFilter = btn.dataset.tfilter;
      apply();
    }});
  }});
  document.querySelectorAll('#disc-toolbar .chip[data-sfilter]').forEach(btn => {{
    btn.addEventListener('click', () => {{
      document.querySelectorAll('#disc-toolbar .chip[data-sfilter]').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      sFilter = btn.dataset.sfilter;
      apply();
    }});
  }});
  apply();
}})();
</script>
"""
    )

    out = Path(out_path or "reports/discovery_index.html")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page_wrap(active="discovery", body=body, title="Discovery", deploy=deploy), encoding="utf-8")
    return out
