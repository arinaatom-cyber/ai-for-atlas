"""HTML Discovery: one unified table (projects + papers + cohorts)."""
from __future__ import annotations

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


def _pub_index(pubs: list[dict]) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for p in pubs:
        pmid = str(p.get("pmid") or "").strip()
        if pmid:
            out[pmid] = p
    return out


def generate_discovery_html(report: dict, out_path: str | Path | None = None, *, deploy: str = "docs_site") -> Path:
    s = report.get("summary") or {}
    items = report.get("candidates") or report.get("new_projects") or []
    pubs = report.get("publications_analyzed") or []
    manual = report.get("manual_check") or []
    literature = report.get("literature_semantic") or []
    papers = _papers_without_accession(manual, literature)
    cohorts = report.get("cohort_literature") or []
    gen = report.get("generated_at") or ""
    pubs_by_pmid = _pub_index(pubs)

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
    <div class="toolbar" id="disc-toolbar">
      <input type="search" id="q" data-i18n-placeholder="search_unified"/>
      <button type="button" class="chip active" data-tfilter="all" data-i18n="filter_all"></button>
      <button type="button" class="chip" data-tfilter="project" data-i18n="filter_projects"></button>
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
        <thead><tr>
          <th data-i18n="th_id"></th>
          <th data-i18n="th_year"></th>
          <th data-i18n="th_title"></th>
          <th data-i18n="th_source"></th>
          <th data-i18n="th_design"></th>
          <th data-i18n="th_omics"></th>
          <th data-i18n="th_patients"></th>
          <th data-i18n="th_n"></th>
          <th data-i18n="th_weight"></th>
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
  let tFilter = 'all';
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
