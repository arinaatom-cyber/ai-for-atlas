"""HTML: крупные когортные статьи по протеомике / мульти-омике."""
from __future__ import annotations

import html
from pathlib import Path

from atlas_agent.viz.site_components import kpi_grid, meta_time, note_i18n, page_hero, section_head
from atlas_agent.viz.site_theme import page_wrap


def _esc(s: object) -> str:
    return html.escape(str(s or ""))


def _patient_badge(item: dict) -> str:
    hp = item.get("has_patients") or "no"
    n = item.get("patient_n")
    if hp == "yes":
        extra = f" (~{n})" if n else ""
        return f'<span class="badge badge-ok"><span data-i18n="pat_yes"></span>{_esc(extra)}</span>'
    if hp == "maybe":
        return '<span class="badge badge-warn" data-i18n="pat_maybe"></span>'
    return '<span class="badge badge-bad" data-i18n="pat_no"></span>'


def _omics_cell(item: dict) -> str:
    omics = item.get("omics") or []
    if not omics:
        return '<span class="cell-empty" data-i18n="cell_empty"></span>'
    labels = {
        "proteomics": "proteomics",
        "phosphoproteomics": "phospho",
        "transcriptomics": "transcript",
        "genomics": "genomics",
        "metabolomics": "metabol",
        "lipidomics": "lipid",
        "glycoproteomics": "glyco",
        "multi_omics": "multi-omics",
    }
    return ", ".join(_esc(labels.get(o, o)) for o in omics[:6])


def _cohort_rows(items: list[dict]) -> str:
    rows = []
    for it in items:
        pmid = it.get("pmid") or ""
        title = _esc((it.get("title") or "")[:160])
        desc = _esc(it.get("description_ru") or "")
        n = it.get("patient_n") or "—"
        score = it.get("cohort_score") or 0
        tmt = '<span class="badge badge-ok">TMT</span>' if it.get("tmt_detected") else '<span class="cell-empty" data-i18n="cell_empty"></span>'
        multi = '<span class="badge badge-ok">✓</span>' if it.get("multi_omics") else '<span class="cell-empty" data-i18n="cell_empty"></span>'
        journal = _esc(f"{it.get('journal') or ''} {it.get('year') or ''}".strip()) or "—"
        pmid_link = (
            f'<a href="https://pubmed.ncbi.nlm.nih.gov/{_esc(pmid)}/" '
            f'target="_blank" rel="noopener" class="cell-mono">{_esc(pmid)}</a>'
            if pmid
            else "—"
        )
        search = f"{title.lower()} {desc.lower()} {n}"
        rows.append(
            f"<tr data-search='{search}' data-patients='{_esc(it.get('has_patients') or '')}'>"
            f"<td>{pmid_link}</td><td class='cell-title'>{title}</td>"
            f"<td class='analysis-cell'>{desc}</td><td>{_patient_badge(it)}</td>"
            f"<td class='cell-mono'><b>{_esc(n)}</b></td><td>{_omics_cell(it)}</td>"
            f"<td>{tmt}</td><td>{multi}</td><td class='text-secondary'>{journal}</td>"
            f"<td class='cell-mono'>{score}</td></tr>"
        )
    return "\n".join(rows) or '<tr><td colspan="10" data-i18n="no_cohorts"></td></tr>'


def generate_cohorts_html(report: dict, out_path: str | Path, *, deploy: str = "docs_site") -> Path:
    s = report.get("summary") or {}
    cohort_stats = s.get("cohort_literature") or {}
    items = report.get("cohort_literature") or []
    gen = report.get("generated_at") or ""
    with_n = sum(1 for x in items if x.get("patient_n"))
    multi = sum(1 for x in items if x.get("multi_omics"))

    meta = meta_time(gen) + ' <span class="meta-pill badge badge-muted" data-i18n="cohorts_method"></span>'
    body = (
        page_hero("cohorts_title", "cohorts_lead", meta)
        + kpi_grid(
            [
                (str(len(items)), "kpi_cohorts"),
                (str(with_n), "kpi_with_n"),
                (str(multi), "kpi_multi_omics"),
                (str(cohort_stats.get("scanned", "—")), "kpi_scanned"),
            ]
        )
        + f"""
<div class="page-content">
  {note_i18n("cohorts_note")}

  <section class="section">
    {section_head("sec_cohorts_table", len(items))}
    <div class="toolbar">
      <input type="search" id="q-cohort" data-i18n-placeholder="search_cohorts"/>
      <button type="button" class="chip active" data-pfilter="all" data-i18n="filter_all"></button>
      <button type="button" class="chip" data-pfilter="yes" data-i18n="filter_patients_yes"></button>
      <button type="button" class="chip" data-pfilter="maybe" data-i18n="filter_patients_maybe"></button>
      <span class="count-badge" id="cohort-count"></span>
    </div>
    <div class="table-wrap">
      <table id="tbl-cohort">
        <thead><tr>
          <th data-i18n="th_pmid"></th>
          <th data-i18n="th_title"></th>
          <th data-i18n="th_description"></th>
          <th data-i18n="th_patients"></th>
          <th data-i18n="th_n"></th>
          <th data-i18n="th_omics"></th>
          <th data-i18n="th_tmt"></th>
          <th data-i18n="th_multi"></th>
          <th data-i18n="th_journal"></th>
          <th data-i18n="th_score"></th>
        </tr></thead>
        <tbody>{_cohort_rows(items)}</tbody>
      </table>
    </div>
  </section>
</div>

<script>
(function() {{
  const q = document.getElementById('q-cohort');
  const rows = [...document.querySelectorAll('#tbl-cohort tbody tr')];
  const count = document.getElementById('cohort-count');
  let pFilter = 'all';
  function apply() {{
    const term = (q?.value || '').toLowerCase().trim();
    let visible = 0;
    rows.forEach(r => {{
      const search = (r.dataset.search || '');
      const pat = (r.dataset.patients || '');
      const patOk = pFilter === 'all' || pat === pFilter;
      const textOk = !term || search.includes(term);
      const show = patOk && textOk;
      r.style.display = show ? '' : 'none';
      if (show) visible++;
    }});
    if (count) count.textContent = visible + ' / {len(items)}';
  }}
  q?.addEventListener('input', apply);
  document.querySelectorAll('[data-pfilter]').forEach(btn => {{
    btn.addEventListener('click', () => {{
      document.querySelectorAll('[data-pfilter]').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      pFilter = btn.dataset.pfilter;
      apply();
    }});
  }});
  apply();
}})();
</script>"""
    )

    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page_wrap(active="cohorts", body=body, title="Cohorts", deploy=deploy), encoding="utf-8")
    return out
