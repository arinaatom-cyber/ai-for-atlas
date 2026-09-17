"""HTML Discovery: one unified table (projects + papers + cohorts)."""
from __future__ import annotations

import html
import re
from pathlib import Path

from atlas_agent.viz.discovery_table_shared import (
    _papers_without_accession,
    build_unified_discovery_rows,
)
from atlas_agent.viz.site_components import (
    ai_agents_panel,
    kpi_grid,
    meta_pill_text,
    meta_time,
    note_discovery_scope,
    page_hero,
    pipeline_steps_panel,
    scan_funnel_raw_stats,
    scan_funnel_viz,
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


def _methods_unlimited(key: str) -> str:
    return f'<li><span data-i18n="{key}"></span> <b data-i18n="cfg_unlimited"></b></li>'


def _search_config_rows(cfg: dict) -> str:
    rows = [_methods_stat("cfg_years", f"{cfg.get('year_from', '?')}–{cfg.get('year_to', '?')}")]
    if cfg.get("repo_unlimited"):
        rows.append(_methods_unlimited("cfg_repo_search"))
    else:
        for key, label in (
            ("pride_max", "cfg_pride_max"),
            ("massive_max", "cfg_massive_max"),
            ("iprox_max", "cfg_iprox_max"),
        ):
            cap = cfg.get(key)
            if cap:
                rows.append(_methods_stat(label, cap))
    pub = cfg.get("publications_max")
    if pub:
        rows.append(_methods_stat("cfg_pubs_max", pub))
    else:
        rows.append(_methods_unlimited("cfg_pubs_max"))
    return "".join(rows)


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
    <span class="meta-pill"><span data-i18n="meta_scan_date"></span> <b>{html.escape(str(m.get("generated_at") or report.get("generated_at") or "—")[:19].replace("T", " "))}</b></span>
  </div>
  {ai_agents_panel(m)}
  {pipeline_steps_panel(m)}
  {scan_funnel_viz(funnel=funnel, lit=lit, gate=gate, raw_repos=int(raw_repos or 0))}
  {scan_funnel_raw_stats(funnel=funnel, lit=lit, gate=gate, raw_repos=int(raw_repos or 0), st=st)}
  <div class="methods-grid">
    <div class="methods-card">
      <h3 data-i18n="methods_search_cfg"></h3>
      <ul class="methods-stats">
        {_search_config_rows(cfg)}
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
        ("th_design", "col_help_design"),
        ("th_verdict", "col_help_verdict"),
        ("th_confidence", "col_help_confidence"),
        ("th_similar", "col_help_similar"),
        ("th_fit", "col_help_fit"),
        ("th_analysis", "col_help_analysis"),
        ("th_data", "col_help_data"),
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
    return f"""
<section class="section">
  <h2 class="section-title" data-i18n="tech_title"></h2>
  <p class="section-desc" data-i18n="tech_lead"></p>
  {_methods_panel(report)}
</section>"""


def _project_accession_key(item: dict) -> str:
    return str(item.get("accession") or item.get("project_accession") or "").strip().upper()


def _merge_discovery_projects(report: dict) -> list[dict]:
    """Candidates plus PRIDE/PDC rows that need manual review (not already listed)."""
    items: list[dict] = []
    seen: set[str] = set()
    for it in report.get("candidates") or report.get("new_projects") or []:
        key = _project_accession_key(it)
        if not key or key in seen:
            continue
        seen.add(key)
        row = dict(it)
        row["_discovery_bucket"] = "candidate"
        items.append(row)
    for it in report.get("repository_manual") or []:
        key = _project_accession_key(it)
        if not key or key in seen:
            continue
        seen.add(key)
        row = dict(it)
        row["_discovery_bucket"] = "repository_manual"
        items.append(row)
    return _sort_discovery_projects(items)


def _sort_discovery_projects(items: list[dict]) -> list[dict]:
    """PDC tier A first, then PRIDE manual review, then other candidates."""
    from atlas_agent.discovery.fit_rules import project_verdict

    def sort_key(it: dict) -> tuple[int, str]:
        acc = _project_accession_key(it)
        bucket = str(it.get("_discovery_bucket") or "")
        verdict = project_verdict(it)[0]
        tier = str(
            it.get("confidence_tier")
            or (it.get("evaluation") or {}).get("confidence_tier")
            or ""
        )
        if acc.startswith("PDC") and verdict == "Candidate" and tier == "A":
            return (0, acc)
        if bucket == "repository_manual":
            pride_first = 0 if acc.startswith("PXD") else 1
            return (1, pride_first, acc)
        return (2, 0, acc)

    return sorted(items, key=sort_key)


def _count_primary_candidates(projects: list[dict]) -> int:
    """KPI: PDC repository rows with Candidate verdict and confidence tier A."""
    from atlas_agent.discovery.fit_rules import project_verdict

    n = 0
    for it in projects:
        acc = str(it.get("accession") or it.get("project_accession") or "").upper()
        if not acc.startswith("PDC"):
            continue
        if project_verdict(it)[0] != "Candidate":
            continue
        tier = str(
            it.get("confidence_tier")
            or (it.get("evaluation") or {}).get("confidence_tier")
            or ""
        )
        if tier == "A":
            n += 1
    return n


def generate_discovery_html(report: dict, out_path: str | Path | None = None, *, deploy: str = "docs_site") -> Path:
    s = report.get("summary") or {}
    candidates_only = list(report.get("candidates") or report.get("new_projects") or [])
    items = _merge_discovery_projects(report)
    candidate_kpi = _count_primary_candidates(candidates_only)
    pride_manual_kpi = len(report.get("repository_manual") or [])
    rejected_kpi = int(s.get("filtered_out") or 0) + int(s.get("rejected_material") or 0)
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

    unified_rows, total_rows = build_unified_discovery_rows(items, papers, cohorts, pubs_by_pmid)

    body = (
        page_hero(
            "disc_title",
            "disc_lead",
            meta_time(gen) + meta_pill_text(str(candidate_kpi), css="badge-ok"),
        )
        + kpi_grid(
            [
                (str(candidate_kpi), "kpi_new"),
                (str(pride_manual_kpi), "kpi_pride_manual"),
                (str(rejected_kpi), "kpi_rejected"),
                (str(len(papers)), "kpi_papers_no_id"),
            ]
        )
        + f"""
<div class="page-content page-content-wide">
  <section class="section" id="discovery">
    {section_head("sec_unified_discovery", total_rows)}
    {section_desc("sec_unified_discovery_desc")}
    {note_discovery_scope(new_projects=candidate_kpi, total_rows=total_rows)}
    <div class="toolbar" id="disc-toolbar">
      <input type="search" id="q" data-i18n-placeholder="search_unified"/>
      <span class="toolbar-label" data-i18n="toolbar_view"></span>
      <button type="button" class="chip active" data-vfilter="simple" data-i18n="filter_view_simple"></button>
      <button type="button" class="chip" data-vfilter="all" data-i18n="filter_view_all"></button>
      <span class="toolbar-divider" aria-hidden="true"></span>
      <span class="toolbar-label" data-i18n="toolbar_type"></span>
      <button type="button" class="chip active" data-tfilter="all" data-i18n="filter_all"></button>
      <button type="button" class="chip" data-tfilter="project" data-i18n="filter_projects"></button>
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
    <div class="table-wrap table-unified">
      <table id="tbl-unified" class="data-table">
        <thead>
          <tr class="head-groups">
            <th colspan="6" class="th-group" data-i18n="th_group_record"></th>
            <th colspan="2" class="th-group col-split" data-i18n="th_group_context"></th>
            <th colspan="7" class="th-group col-split" data-i18n="th_group_details"></th>
          </tr>
          <tr>
          <th class="col-num" data-i18n="th_num"></th>
          <th class="col-type" data-i18n="th_type"></th>
          <th class="col-id"><span class="th-main" data-i18n="th_project_id"></span><span class="th-hint" data-i18n="th_project_id_hint"></span></th>
          <th class="col-year" data-i18n="th_year"></th>
          <th class="col-title" data-i18n="th_title"></th>
          <th class="col-disease" data-i18n="th_disease"></th>
          <th class="col-organ" data-i18n="th_organ"></th>
          <th class="col-design col-split" data-i18n="th_design"></th>
          <th class="col-verdict col-split" data-i18n="th_verdict"></th>
          <th class="col-confidence" data-i18n="th_confidence"></th>
          <th class="col-similar" data-i18n="th_similar"></th>
          <th class="col-abstract" data-i18n="th_abstract"></th>
          <th class="col-weight" data-i18n="th_fit"></th>
          <th class="col-analysis" data-i18n="th_analysis"></th>
          <th class="col-data" data-i18n="th_data"></th>
        </tr></thead>
        <tbody>{unified_rows}</tbody>
      </table>
    </div>
  </section>

  <details class="site-fold" id="guide">
    <summary data-i18n="tab_guide"></summary>
    {_guide_panel()}
  </details>
  <details class="site-fold" id="technical">
    <summary data-i18n="tab_technical"></summary>
    {_technical_panel(report)}
  </details>
</div>

<script>
(function() {{
  const q = document.getElementById('q');
  const tbl = document.getElementById('tbl-unified');
  const rows = tbl ? [...tbl.querySelectorAll('tbody tr')] : [];
  const count = document.getElementById('count');
  let tFilter = 'all';
  let sFilter = 'all';
  let vFilter = 'simple';
  function apply() {{
    const term = (q?.value || '').toLowerCase().trim();
    let visible = 0;
    rows.forEach(r => {{
      const typ = (r.dataset.type || '');
      const src = (r.dataset.src || '');
      const search = (r.dataset.search || '');
      const simple = (r.dataset.simple || '0') === '1';
      const typeOk = tFilter === 'all' || typ === tFilter;
      const srcOk = sFilter === 'all' || src === sFilter;
      const viewOk = vFilter === 'all' || simple;
      const textOk = !term || search.includes(term);
      const show = typeOk && srcOk && viewOk && textOk;
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
  document.querySelectorAll('#disc-toolbar .chip[data-vfilter]').forEach(btn => {{
    btn.addEventListener('click', () => {{
      document.querySelectorAll('#disc-toolbar .chip[data-vfilter]').forEach(b => {{
        b.classList.toggle('active', b === btn);
      }});
      vFilter = btn.dataset.vfilter;
      apply();
    }});
  }});
  const hash = (location.hash || '').replace('#', '');
  if (hash === 'cohorts') setTypeFilter('cohort');
  else if (hash === 'papers') setTypeFilter('paper');
  else if (hash === 'projects') setTypeFilter('project');
  else apply();
  rows.forEach((r, i) => {{
    const num = r.querySelector('.col-num b');
    if (num) num.textContent = String(i + 1);
  }});
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
