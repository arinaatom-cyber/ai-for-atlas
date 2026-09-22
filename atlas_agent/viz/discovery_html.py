from __future__ import annotations

import html
import re
from pathlib import Path

from atlas_agent.viz.discovery_table_shared import (
    _first_accession,
    _norm_pmid,
    _papers_without_accession,
    build_pmid_repo_index,
    build_unified_discovery_rows,
)
from atlas_agent.viz.site_components import (
    ai_agents_panel,
    kpi_grid,
    meta_pill_text,
    meta_time,
    page_hero,
    pipeline_steps_panel,
    scan_funnel_raw_stats,
    scan_funnel_viz,
    section_head,
)
from atlas_agent.viz.i18n_defaults import BRAND_NAME
from atlas_agent.viz.site_theme import DEPLOY_TMT, page_wrap


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
        ("th_disease", "col_help_disease"),
        ("th_organ", "col_help_organ"),
        ("th_design", "col_help_design"),
        ("th_verdict", "col_help_verdict"),
        ("th_similar", "col_help_similar"),
        ("th_finding", "col_help_finding"),
        ("th_data", "col_help_data"),
    ]
    rows = "".join(
        f'<div class="guide-row"><div class="guide-row-title" data-i18n="{k}"></div>'
        f'<div class="guide-row-desc" data-i18n="{d}"></div></div>'
        for k, d in cols
    )
    return f"""
<section class="section guide-section">
  <h3 class="section-subtitle" data-i18n="guide_columns_title"></h3>
  <div class="guide-group">{rows}</div>
  <div class="guide-block">
    <h3 data-i18n="guide_filters_title"></h3>
    <p data-i18n="guide_filters_search"></p>
  </div>
  <div class="guide-block">
    <h3 data-i18n="guide_similarity_title"></h3>
    <p data-i18n="guide_similarity_desc"></p>
  </div>
</section>"""


def _project_accession_key(item: dict) -> str:
    return str(item.get("accession") or item.get("project_accession") or "").strip().upper()


def _merge_discovery_projects(report: dict) -> list[dict]:
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
    from atlas_agent.discovery.fit_rules import project_verdict

    def sort_key(it: dict) -> tuple:
        acc = _project_accession_key(it)
        bucket = str(it.get("_discovery_bucket") or "")
        verdict = project_verdict(it)[0]
        year_n = 0
        for key in ("publication_date", "submission_date", "pub_date", "published", "year"):
            m = re.search(r"(19|20)\d{2}", str(it.get(key) or ""))
            if m:
                year_n = -int(m.group(0))
                break
        if bucket == "candidate" and verdict == "Candidate":
            return (0, year_n, acc)
        if bucket == "candidate":
            return (1, year_n, acc)
        if bucket == "repository_manual":
            return (2, year_n, acc)
        return (3, year_n, acc)

    return sorted(items, key=sort_key)


def _count_passed_candidates(projects: list[dict]) -> int:
    from atlas_agent.discovery.fit_rules import project_verdict

    return sum(1 for it in projects if project_verdict(it)[0] == "Candidate")


def generate_discovery_html(report: dict, out_path: str | Path | None = None, *, deploy: str = "docs_site") -> Path:
    from atlas_agent.viz.site_sanitize import sanitize_report_for_site

    report = sanitize_report_for_site(dict(report))
    s = report.get("summary") or {}
    candidates_only = list(report.get("candidates") or report.get("new_projects") or [])
    items = _merge_discovery_projects(report)
    candidate_kpi = _count_passed_candidates(candidates_only)
    pride_manual_kpi = len(report.get("repository_manual") or [])
    rejected_kpi = int(s.get("filtered_out") or 0) + int(s.get("rejected_material") or 0)
    pubs = report.get("publications_analyzed") or []
    manual = report.get("manual_check") or []
    literature = report.get("literature_semantic") or []
    cohorts = report.get("cohort_literature") or []
    gen = report.get("generated_at") or ""
    profile = report.get("catalog_profile") or {}
    pmid_index = build_pmid_repo_index(items)
    papers_raw = _papers_without_accession(manual, literature)
    linked_pmids = set(pmid_index.keys())
    papers = [
        p
        for p in papers_raw
        if _norm_pmid(p) not in linked_pmids and (_norm_pmid(p) or _first_accession(p))
    ]
    cohorts = [c for c in cohorts if _norm_pmid(c) or _first_accession(c)]
    pubs_by_pmid = _pub_index(
        pubs,
        (report.get("manual_check") or []) + (report.get("literature_semantic") or []),
    )

    unified_rows, total_rows, _disease_filters = build_unified_discovery_rows(
        items,
        papers,
        cohorts,
        pubs_by_pmid,
        catalog_profile=profile,
        pmid_index=pmid_index,
        fetch_pride_pmid=False,
        resolve_literature_remote=False,
    )

    body = (
        page_hero(
            "disc_title",
            None,
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
    <p class="catalog-banner" data-i18n="disc_catalog_banner"></p>
    <ul class="verdict-legend" aria-label="Verdict legend">
      <li><span class="badge badge-ok" data-i18n="verdict_candidate"></span> <span data-i18n="legend_candidate"></span></li>
      <li><span class="badge badge-warn" data-i18n="verdict_review"></span> <span data-i18n="legend_review"></span></li>
      <li><span class="badge badge-muted" data-i18n="verdict_watch"></span> <span data-i18n="legend_watch"></span></li>
      <li><span class="badge badge-bad" data-i18n="verdict_exclude"></span> <span data-i18n="legend_exclude"></span></li>
    </ul>
    <div class="toolbar" id="disc-toolbar">
      <input type="search" id="q" data-i18n-placeholder="search_unified"/>
      <select id="f-type" aria-label="Type">
        <option value="" data-i18n="filter_all">All</option>
        <option value="project" data-i18n="badge_project">Project</option>
        <option value="paper" data-i18n="badge_paper">Paper</option>
        <option value="cohort" data-i18n="badge_cohort">Cohort</option>
      </select>
      <select id="f-verdict" aria-label="Verdict">
        <option value="" data-i18n="filter_all">All</option>
        <option value="Candidate" data-i18n="verdict_candidate">Candidate</option>
        <option value="Review" data-i18n="verdict_review">Review</option>
        <option value="Watch" data-i18n="verdict_watch">Watch</option>
        <option value="Exclude" data-i18n="verdict_exclude">Exclude</option>
      </select>
      <select id="f-year" aria-label="Year"><option value="" data-i18n="filter_all">All</option></select>
      <span class="count-badge" id="count"></span>
    </div>
    <p class="table-scroll-hint" data-i18n="table_scroll_hint"></p>
    <div class="table-wrap table-unified">
      <table id="tbl-unified" class="data-table">
        <thead>
          <tr class="head-groups">
            <th colspan="6" class="th-group" data-i18n="th_group_record"></th>
            <th colspan="2" class="th-group col-split" data-i18n="th_group_context"></th>
            <th colspan="4" class="th-group col-split" data-i18n="th_group_details"></th>
          </tr>
          <tr>
          <th class="col-num" data-i18n="th_num"></th>
          <th class="col-type" data-i18n="th_type"></th>
          <th class="col-id"><span class="th-main" data-i18n="th_project_id"></span><span class="th-hint" data-i18n="th_project_id_hint"></span></th>
          <th class="col-year sort-th" data-sort="year" data-i18n="th_year"></th>
          <th class="col-title" data-i18n="th_title"></th>
          <th class="col-disease" data-i18n="th_disease"></th>
          <th class="col-organ" data-i18n="th_organ"></th>
          <th class="col-design col-split" data-i18n="th_design"></th>
          <th class="col-verdict col-split sort-th" data-sort="verdict" data-i18n="th_verdict"></th>
          <th class="col-similar" data-i18n="th_similar" data-i18n-title="th_similar_hint"></th>
          <th class="col-finding" data-i18n="th_finding"></th>
          <th class="col-data" data-i18n="th_data"></th>
        </tr></thead>
        <tbody>{unified_rows}</tbody>
      </table>
    </div>
  </section>
</div>

<script>
(function() {{
  const q = document.getElementById('q');
  const tbl = document.getElementById('tbl-unified');
  const tbody = tbl ? tbl.querySelector('tbody') : null;
  const rows = tbody ? [...tbody.querySelectorAll('tr')] : [];
  const count = document.getElementById('count');
  const fType = document.getElementById('f-type');
  const fVerdict = document.getElementById('f-verdict');
  const fYear = document.getElementById('f-year');
  if (fYear) {{
    const years = [...new Set(rows.map(r => r.dataset.year).filter(y => y && y !== '—'))].sort().reverse();
    years.forEach(y => {{
      const o = document.createElement('option');
      o.value = y; o.textContent = y;
      fYear.appendChild(o);
    }});
  }}
  function apply() {{
    const term = (q?.value || '').toLowerCase().trim();
    const type = fType?.value || '';
    const verdict = fVerdict?.value || '';
    const year = fYear?.value || '';
    let visible = 0;
    rows.forEach(r => {{
      const search = (r.dataset.search || '');
      const show = (!term || search.includes(term))
        && (!type || r.dataset.type === type)
        && (!verdict || r.dataset.verdict === verdict)
        && (!year || r.dataset.year === year);
      r.style.display = show ? '' : 'none';
      if (show) {{
        visible++;
        const num = r.querySelector('.col-num b');
        if (num) num.textContent = String(visible);
      }}
    }});
    if (count) {{
      const lang = window.AtlasI18n?.getLang?.() || 'ru';
      const tpl = window.AtlasI18n?.T?.[lang]?.count_rows || '{{n}} / {{total}}';
      count.textContent = tpl.replace('{{n}}', String(visible)).replace('{{total}}', '{total_rows}');
    }}
  }}
  q?.addEventListener('input', apply);
  fType?.addEventListener('change', apply);
  fVerdict?.addEventListener('change', apply);
  fYear?.addEventListener('change', apply);
  tbl?.querySelectorAll('th.sort-th').forEach(th => {{
    th.style.cursor = 'pointer';
    th.addEventListener('click', () => {{
      const key = th.dataset.sort;
      const dir = th.dataset.dir === 'asc' ? 'desc' : 'asc';
      th.dataset.dir = dir;
      rows.sort((a, b) => {{
        const av = (a.dataset[key] || '');
        const bv = (b.dataset[key] || '');
        return dir === 'asc' ? av.localeCompare(bv) : bv.localeCompare(av);
      }});
      rows.forEach(r => tbody.appendChild(r));
      apply();
    }});
  }});
  apply();
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


def generate_guide_html(out_path: str | Path, *, deploy: str = "docs_site") -> Path:
    body = page_hero("guide_title", "guide_lead", "") + f"""
<div class="page-content">
  {_guide_panel()}
</div>"""
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page_wrap(active="guide", body=body, title=BRAND_NAME, deploy=deploy), encoding="utf-8")
    return out


def generate_methods_html(report: dict, out_path: str | Path, *, deploy: str = "docs_site") -> Path:
    gen = report.get("generated_at") or ""
    body = (
        page_hero("sec_methods", "sec_methods_desc", meta_time(gen))
        + f"""
<div class="page-content">
  {_methods_panel(report)}
</div>"""
    )
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page_wrap(active="methods", body=body, title=BRAND_NAME, deploy=deploy), encoding="utf-8")
    return out
