"""HTML Discovery: one unified table (projects + papers + cohorts)."""
from __future__ import annotations

import html
import json
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
    note_discovery_scope,
    page_hero,
    section_desc,
    section_head,
)
from atlas_agent.viz.i18n_defaults import BRAND_NAME
from atlas_agent.viz.site_theme import DEPLOY_DOCS_PORTAL, DEPLOY_TMT, page_wrap


def _pub_index(pubs: list[dict], extra: list[dict] | None = None) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for p in (extra or []) + pubs:
        pmid = re.sub(r"\D", "", str(p.get("pmid") or ""))
        if pmid:
            out[pmid] = p
    return out


def _methods_stat(key: str, value: object) -> str:
    return f'<li><span data-i18n="{key}"></span> <b>{html.escape(str(value))}</b></li>'


def _methods_panel(report: dict) -> str:
    m = report.get("methods_manifest") or {}
    s = report.get("summary") or {}
    st = s.get("source_stats") or {}
    qm = report.get("quality_metrics") or s.get("quality_metrics") or {}
    lit_b = qm.get("benchmark_literature") or {}
    proj_b = qm.get("benchmark_projects") or {}
    funnel = m.get("funnel") or {}
    lit = m.get("literature_screening") or {}
    gate = m.get("data_availability_gate") or {}
    cfg = m.get("search_config") or {}
    flt = m.get("filters_applied") or {}
    raw_repos = funnel.get("raw_novel_repos") or (st.get("pride_v3_search", 0) + st.get("pdc_uiStudySummary", 0))
    plex = ", ".join(str(x) for x in (flt.get("allowed_tmt_plexes") or []))
    dbs = ", ".join(flt.get("allowed_databases") or [])
    llm_key = "cfg_llm_on" if cfg.get("abstract_llm") else "cfg_llm_off"

    exc_items = "".join(f'<li data-i18n="exc_{i}"></li>' for i in range(1, 8))
    return f"""
<section class="section methods-panel" id="methods">
  <h2 class="section-title" data-i18n="sec_methods"></h2>
  <p class="section-desc" data-i18n="sec_methods_desc"></p>
  <div class="methods-meta">
    <span class="meta-pill"><span data-i18n="meta_pipeline"></span> <b>{html.escape(str(m.get("pipeline") or "Atlas Discovery Agent"))}</b></span>
    <span class="meta-pill"><span data-i18n="meta_version"></span> <b>{html.escape(str(m.get("pipeline_version") or "—"))}</b></span>
    <span class="meta-pill"><span data-i18n="meta_python"></span> <b>{html.escape(str(m.get("python") or "—"))}</b></span>
    <span class="meta-pill"><span data-i18n="meta_scan_date"></span> <b>{html.escape(str(m.get("generated_at") or report.get("generated_at") or "—"))}</b></span>
  </div>
  <div class="methods-grid">
    <div class="methods-card">
      <h3 data-i18n="methods_funnel"></h3>
      <ul class="methods-stats">
        {_methods_stat("funnel_raw_repos", raw_repos)}
        {_methods_stat("funnel_in_catalog", funnel.get("already_in_catalog", 0))}
        {_methods_stat("funnel_filtered", funnel.get("filtered_out", s.get("filtered_out", 0)))}
        {_methods_stat("funnel_candidates", funnel.get("candidates", s.get("candidates", 0)))}
        {_methods_stat("funnel_manual", funnel.get("manual_check", 0))}
        {_methods_stat("funnel_rejected", funnel.get("rejected_material", 0))}
      </ul>
    </div>
    <div class="methods-card">
      <h3 data-i18n="methods_literature"></h3>
      <ul class="methods-stats">
        {_methods_stat("lit_scanned", lit.get("publications_scanned", 0))}
        {_methods_stat("lit_llm_read", lit.get("abstract_llm_read", st.get("abstract_llm_read", 0)))}
        {_methods_stat("lit_regex_only", lit.get("abstract_regex_only", 0))}
        {_methods_stat("lit_fit_yes", lit.get("atlas_fit_yes", 0))}
        {_methods_stat("lit_fit_maybe", lit.get("atlas_fit_maybe", 0))}
        {_methods_stat("lit_resolved", lit.get("literature_resolved", st.get("literature_resolved", 0)))}
      </ul>
    </div>
    <div class="methods-card">
      <h3 data-i18n="methods_data_gate"></h3>
      <ul class="methods-stats">
        {_methods_stat("gate_quant_table", gate.get("quant_table", 0))}
        {_methods_stat("gate_omics_protein", gate.get("omics_protein", 0))}
        {_methods_stat("gate_raw_only", gate.get("raw_only", 0))}
        {_methods_stat("gate_no_files", gate.get("no_files", 0))}
        {_methods_stat("gate_unknown", gate.get("omics_unknown", 0))}
      </ul>
    </div>
    <div class="methods-card">
      <h3 data-i18n="methods_search_cfg"></h3>
      <ul class="methods-stats">
        {_methods_stat("cfg_years", f"{cfg.get('year_from', '?')}–{cfg.get('year_to', '?')}")}
        {_methods_stat("cfg_pride_max", cfg.get("pride_max", "—"))}
        {_methods_stat("cfg_pubs_max", cfg.get("publications_max", "—"))}
        <li><span data-i18n="cfg_llm"></span> <b data-i18n="{llm_key}"></b></li>
        {_methods_stat("cfg_mode", cfg.get("search_mode", "—"))}
        {_methods_stat("cfg_tmt_plex", plex or "—")}
        {_methods_stat("cfg_databases", dbs or "—")}
      </ul>
    </div>
    <div class="methods-card">
      <h3 data-i18n="methods_confidence"></h3>
      <p data-i18n="methods_tier_legend"></p>
      <ul class="methods-stats">
        {_methods_stat("bench_literature", f"{lit_b.get('correct', '?')}/{lit_b.get('n', '?')}")}
        {_methods_stat("bench_projects", f"{proj_b.get('correct', '?')}/{proj_b.get('n', '?')}")}
      </ul>
      <p class="methods-note" data-i18n="methods_confidence_note"></p>
    </div>
    <div class="methods-card">
      <h3 data-i18n="methods_inclusion"></h3>
      <ul class="methods-stats">
        <li data-i18n="inc_organism"></li>
        <li data-i18n="inc_quant"></li>
        <li data-i18n="inc_omics"></li>
        <li data-i18n="inc_material"></li>
        <li data-i18n="inc_literature"></li>
      </ul>
      <h4 data-i18n="methods_exclusion"></h4>
      <ul class="methods-stats">{exc_items}</ul>
    </div>
  </div>
</section>"""


def _guide_panel() -> str:
    cols = [
        ("th_type", "col_help_type"),
        ("th_project_id", "col_help_id"),
        ("th_year", "col_help_year"),
        ("th_title", "col_help_title"),
        ("th_source", "col_help_source"),
        ("th_design", "col_help_design"),
        ("th_omics", "col_help_omics"),
        ("th_patients", "col_help_patients"),
        ("th_n", "col_help_n"),
        ("th_verdict", "col_help_verdict"),
        ("th_confidence", "col_help_confidence"),
        ("th_similar", "col_help_similar"),
        ("th_fit", "col_help_fit"),
        ("th_analysis", "col_help_analysis"),
        ("th_data", "col_help_data"),
        ("th_links", "col_help_links"),
    ]
    rows = "".join(
        f'<div class="guide-row"><div class="guide-row-title" data-i18n="{k}"></div>'
        f'<div class="guide-row-desc" data-i18n="{d}"></div></div>'
        for k, d in cols
    )
    return f"""
<section class="section guide-section">
  <h2 class="section-title" data-i18n="guide_title"></h2>
  <p class="section-desc" data-i18n="guide_lead"></p>
  <h3 class="section-subtitle" data-i18n="guide_columns_title"></h3>
  <div class="guide-group">{rows}</div>
  <div class="guide-block">
    <h3 data-i18n="guide_filters_title"></h3>
    <ul>
      <li data-i18n="guide_filters_type"></li>
      <li data-i18n="guide_filters_source"></li>
      <li data-i18n="guide_filters_search"></li>
    </ul>
  </div>
  <div class="guide-block">
    <h3 data-i18n="guide_similarity_title"></h3>
    <p data-i18n="guide_similarity_desc"></p>
  </div>
</section>"""


def _technical_panel(report: dict) -> str:
    manifest = report.get("methods_manifest") or {}
    manifest_json = html.escape(json.dumps(manifest, ensure_ascii=False, indent=2)[:12000])
    return f"""
<section class="section">
  <h2 class="section-title" data-i18n="tech_title"></h2>
  <p class="section-desc" data-i18n="tech_lead"></p>
  <div class="guide-block">
    <h3 data-i18n="sec_methods"></h3>
    <ul>
      <li data-i18n="tech_step1"></li>
      <li data-i18n="tech_step2"></li>
      <li data-i18n="tech_step3"></li>
      <li data-i18n="tech_step4"></li>
      <li data-i18n="tech_step5"></li>
      <li data-i18n="tech_step6"></li>
    </ul>
  </div>
  {_methods_panel(report)}
  <div class="guide-block">
    <h3 data-i18n="tech_llm_title"></h3>
    <p data-i18n="tech_llm_desc"></p>
  </div>
  <details class="methods-collapse">
    <summary data-i18n="tech_manifest_title"></summary>
    <pre class="tech-pre">{manifest_json or "—"}</pre>
  </details>
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
  <nav class="page-tabs" aria-label="Sections">
    <button type="button" class="page-tab active" data-tab="projects" data-i18n="tab_projects"></button>
    <button type="button" class="page-tab" data-tab="guide" data-i18n="tab_guide"></button>
    <button type="button" class="page-tab" data-tab="technical" data-i18n="tab_technical"></button>
  </nav>

  <div id="panel-projects" class="tab-panel active">
  <section class="section" id="discovery">
    {section_head("sec_unified_discovery", total_rows)}
    {section_desc("sec_unified_discovery_desc")}
    {note_discovery_scope(new_projects=len(items), total_rows=total_rows)}
    <div class="toolbar" id="disc-toolbar">
      <input type="search" id="q" data-i18n-placeholder="search_unified"/>
      <span class="toolbar-label" data-i18n="toolbar_type"></span>
      <button type="button" class="chip" data-tfilter="all" data-i18n="filter_all"></button>
      <button type="button" class="chip active" data-tfilter="project" data-i18n="filter_projects"></button>
      <button type="button" class="chip" data-tfilter="paper" data-i18n="filter_papers"></button>
      <button type="button" class="chip" data-tfilter="cohort" data-i18n="filter_cohorts"></button>
      <span class="toolbar-divider" aria-hidden="true"></span>
      <span class="toolbar-label" data-i18n="toolbar_source"></span>
      <button type="button" class="chip active" data-sfilter="all" data-i18n="filter_all_src"></button>
      <button type="button" class="chip" data-sfilter="pride" data-i18n="filter_pride"></button>
      <button type="button" class="chip" data-sfilter="pdc" data-i18n="filter_pdc"></button>
      <button type="button" class="chip" data-sfilter="massive" data-i18n="filter_massive"></button>
      <button type="button" class="chip" data-sfilter="iprox" data-i18n="filter_iprox"></button>
      <button type="button" class="chip" data-sfilter="epmc" data-i18n="filter_epmc"></button>
      <span class="count-badge" id="count"></span>
    </div>
    <p class="table-scroll-hint" data-i18n="table_scroll_hint"></p>
    <div class="table-wrap table-standard table-unified">
      <table id="tbl-unified" class="data-table">
        <thead>
          <tr class="head-groups">
            <th colspan="4" class="th-group" data-i18n="th_group_record"></th>
            <th colspan="5" class="th-group col-split" data-i18n="th_group_context"></th>
            <th colspan="7" class="th-group col-split" data-i18n="th_group_details"></th>
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
          <th data-i18n="th_similar"></th>
          <th data-i18n="th_fit"></th>
          <th data-i18n="th_analysis"></th>
          <th data-i18n="th_data"></th>
          <th data-i18n="th_links"></th>
        </tr></thead>
        <tbody>{unified_rows}</tbody>
      </table>
    </div>
  </section>
  </div>

  <div id="panel-guide" class="tab-panel">{_guide_panel()}</div>
  <div id="panel-technical" class="tab-panel">{_technical_panel(report)}</div>

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
    if (count) {{
      const lang = window.AtlasI18n?.getLang?.() || 'ru';
      const tpl = window.AtlasI18n?.T?.[lang]?.count_rows || '{{n}} / {{total}}';
      count.textContent = tpl.replace('{{n}}', String(visible)).replace('{{total}}', '{total_rows}');
    }}
  }}
  q?.addEventListener('input', apply);
  function setTypeFilter(value) {{
    tFilter = value;
    document.querySelectorAll('#disc-toolbar .chip[data-tfilter]').forEach(b => {{
      b.classList.toggle('active', b.dataset.tfilter === value);
    }});
    apply();
  }}
  document.querySelectorAll('#disc-toolbar .chip[data-tfilter]').forEach(btn => {{
    btn.addEventListener('click', () => setTypeFilter(btn.dataset.tfilter));
  }});
  document.querySelectorAll('#disc-toolbar .chip[data-sfilter]').forEach(btn => {{
    btn.addEventListener('click', () => {{
      document.querySelectorAll('#disc-toolbar .chip[data-sfilter]').forEach(b => {{
        b.classList.toggle('active', b === btn);
      }});
      sFilter = btn.dataset.sfilter;
      apply();
    }});
  }});
  const hash = (location.hash || '').replace('#', '');
  if (hash === 'cohorts') setTypeFilter('cohort');
  else if (hash === 'papers') setTypeFilter('paper');
  else if (hash === 'projects') setTypeFilter('project');
  else apply();
  document.addEventListener('atlas:lang', apply);
}})();
</script>
"""
    )

    out = Path(out_path or "reports/discovery_index.html")
    out.parent.mkdir(parents=True, exist_ok=True)
    nav_active = "discovery"
    out.write_text(page_wrap(active=nav_active, body=body, title=BRAND_NAME, deploy=deploy), encoding="utf-8")
    return out
