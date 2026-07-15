"""HTML Discovery: unified new-projects table + papers without accession."""
from __future__ import annotations

import html
from pathlib import Path

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
from atlas_agent.viz.portal_index import format_finding_note, pubmed_url, repository_url
from atlas_agent.viz.site_theme import page_wrap


def _esc(s: object) -> str:
    return html.escape(str(s or ""))


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


def _fit_class(fit: str) -> str:
    return {"yes": "fit-yes", "maybe": "fit-maybe", "no": "fit-no"}.get(str(fit).lower(), "fit-unk")


def _pub_index(pubs: list[dict]) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for p in pubs:
        pmid = str(p.get("pmid") or "").strip()
        if pmid:
            out[pmid] = p
    return out


def _analysis_cell(it: dict, pubs_by_pmid: dict[str, dict]) -> str:
    """Finding + optional LLM abstract summary for linked PMID."""
    parts: list[str] = []
    note = it.get("finding_note") or format_finding_note(it)
    if note:
        parts.append(f'<span class="muted">{_esc(note[:380])}</span>')

    ai = it.get("abstract_ai") or {}
    pmid = str(it.get("pmid") or "").strip()
    pub = pubs_by_pmid.get(pmid) if pmid else None
    if pub:
        summary = pub.get("summary_en") or ""
        fit = pub.get("atlas_fit")
        score = pub.get("atlas_fit_score")
        if summary:
            parts.append(f'<span class="muted llm-block">{_esc(summary[:280])}</span>')
        if fit:
            parts.append(f'<span class="badge {_fit_class(fit)}">{_esc(fit)} {score or ""}</span>')
    elif ai.get("summary_en"):
        parts.append(f'<span class="muted llm-block">{_esc(ai["summary_en"][:280])}</span>')
        fit = ai.get("atlas_fit")
        if fit:
            parts.append(f'<span class="badge {_fit_class(fit)}">{_esc(fit)}</span>')

    return "<br/>".join(parts) if parts else "—"


def _data_cell(it: dict) -> str:
    da = it.get("data_availability") or {}
    if not da:
        return "—"
    status = da.get("status") or "unknown"
    label = _esc(da.get("label") or status)
    cls = {
        "quant_table": "badge-ok",
        "local_mirror": "badge-ok",
        "maybe_table": "badge-warn",
        "processed_psm": "badge-warn",
        "phospho_table": "badge-bad",
        "raw_only": "badge-bad",
        "no_files": "badge-bad",
    }.get(status, "badge-muted")
    samples = da.get("proteome_files") or da.get("quant_files") or da.get("sample_files") or []
    hint = ""
    if samples:
        hint = f'<br/><span class="muted">{_esc(samples[0][:55])}</span>'
    guidance = _esc(da.get("guidance") or "")
    if guidance:
        hint += f'<br/><span class="muted">{guidance[:90]}</span>'
    return f'<span class="badge {cls}">{label}</span>{hint}'


def _links_cell(it: dict) -> str:
    acc = (it.get("project_accession") or it.get("accession") or "").strip().upper()
    repo = it.get("repository_url") or it.get("url") or repository_url(acc)
    pub = it.get("pubmed_url") or pubmed_url(it.get("pmid"))
    parts: list[str] = []
    if repo:
        parts.append(
            f'<a href="{_esc(repo)}" target="_blank" rel="noopener" class="link-repo">Project</a>'
        )
    if pub:
        parts.append(
            f'<a href="{_esc(pub)}" target="_blank" rel="noopener" class="link-pub">PubMed</a>'
        )
    return " · ".join(parts) if parts else '<span class="cell-empty">—</span>'


def _project_rows(items: list[dict], pubs_by_pmid: dict[str, dict]) -> str:
    rows = []
    for it in items:
        raw_acc = (it.get("project_accession") or it.get("accession") or "").strip().upper()
        acc_esc = _esc(raw_acc or "—")
        title_raw = (it.get("title") or "")[:120]
        title = _esc(title_raw)
        src = _esc(_source_label(it))
        plex = _esc(str(it.get("tmt_label") or it.get("inferred_plex") or "—"))
        design = _esc(str(it.get("sample_design") or "—").replace("_", "-"))
        sim = (it.get("similar_in_catalog") or [{}])[0]
        sim_txt = _esc(f"{sim.get('project_id') or '—'} ({sim.get('score', '—')})")
        analysis = _analysis_cell(it, pubs_by_pmid)
        data = _data_cell(it)
        links = _links_cell(it)
        repo = it.get("repository_url") or it.get("url") or repository_url(raw_acc)
        pub = it.get("pubmed_url") or pubmed_url(it.get("pmid"))
        if repo:
            id_cell = f'<a href="{_esc(repo)}" target="_blank" rel="noopener" class="cell-mono"><b>{acc_esc}</b></a>'
        else:
            id_cell = f'<span class="cell-mono"><b>{acc_esc}</b></span>'
        if pub:
            title_cell = f'<a href="{_esc(pub)}" target="_blank" rel="noopener" class="cell-title">{title}</a>'
        elif repo:
            title_cell = f'<a href="{_esc(repo)}" target="_blank" rel="noopener" class="cell-title">{title}</a>'
        else:
            title_cell = f'<span class="cell-title">{title}</span>'
        program = _esc(str(it.get("program") or it.get("disease") or "")[:60])
        rows.append(
            f"<tr data-src='{src.lower()}' data-search='{acc_esc.lower()} {title.lower()} {program.lower()}'>"
            f"<td class='col-id'>{id_cell}</td>"
            f"<td class='col-title'>{title_cell}</td>"
            f"<td class='col-src'>{src}</td>"
            f"<td class='col-plex'>{plex}</td>"
            f"<td class='col-design'>{design}</td>"
            f"<td class='col-sim'>{sim_txt}</td>"
            f"<td class='col-analysis analysis-cell'>{analysis}</td>"
            f"<td class='col-data'>{data}</td>"
            f"<td class='col-links cell-links'>{links}</td></tr>"
        )
    return "\n".join(rows)


def _paper_rows(items: list[dict]) -> str:
    rows = []
    for it in items:
        pmid = str(it.get("pmid") or "").strip()
        label = _esc(f"PMID:{pmid}" if pmid else (it.get("project_accession") or "—"))
        title = _esc((it.get("title") or "")[:120])
        fit = it.get("atlas_fit") or (it.get("abstract_ai") or {}).get("atlas_fit") or "?"
        score = it.get("atlas_fit_score") or (it.get("abstract_ai") or {}).get("atlas_fit_score") or ""
        ai = it.get("abstract_ai") or {}
        summary = _esc(ai.get("summary_en") or it.get("summary_en") or "")
        note = _esc(it.get("finding_note") or format_finding_note(it) or "")
        link = (
            f'<a href="https://pubmed.ncbi.nlm.nih.gov/{_esc(pmid)}/" target="_blank" rel="noopener">PubMed</a>'
            if pmid
            else ""
        )
        rows.append(
            f"<tr data-search='{title.lower()} {note.lower()}'>"
            f"<td class='col-id'><b>{label}</b></td>"
            f"<td class='col-title'>{title}</td>"
            f"<td class='col-fit'><span class='badge {_fit_class(fit)}'>{_esc(fit)} {score}</span></td>"
            f"<td class='col-analysis analysis-cell'>{summary}<br/><span class='muted'>{note}</span></td>"
            f"<td class='col-links cell-links'>{link}</td></tr>"
        )
    return "\n".join(rows)


def _papers_without_accession(manual: list[dict], literature: list[dict]) -> list[dict]:
    seen: set[str] = set()
    out: list[dict] = []
    for item in manual + literature:
        pmid = str(item.get("pmid") or "").strip()
        key = pmid or str(item.get("title") or "")[:80]
        if key in seen:
            continue
        seen.add(key)
        out.append(item)
    return out


def generate_discovery_html(report: dict, out_path: str | Path | None = None, *, deploy: str = "docs_site") -> Path:
    s = report.get("summary") or {}
    items = report.get("candidates") or report.get("new_projects") or []
    pubs = report.get("publications_analyzed") or []
    manual = report.get("manual_check") or []
    literature = report.get("literature_semantic") or []
    papers = _papers_without_accession(manual, literature)
    stats = s.get("source_stats") or {}
    gen = report.get("generated_at") or ""
    pubs_by_pmid = _pub_index(pubs)

    pride_n = sum(1 for x in items if _source_label(x) == "PRIDE")
    pdc_n = sum(1 for x in items if _source_label(x) == "PDC")
    table_n = sum(
        1 for x in items
        if (x.get("data_availability") or {}).get("status") == "quant_table"
    )

    proj_rows = _project_rows(items, pubs_by_pmid) or '<tr><td colspan="9" data-i18n="no_projects"></td></tr>'
    paper_rows = _paper_rows(papers) or '<tr><td colspan="5" data-i18n="no_literature"></td></tr>'

    qc_link = '<p class="note-box"><a href="qc.html">QC report</a> — manual review &amp; rejected material (separate page).</p>'

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
                (str(pride_n), "kpi_pride"),
                (str(pdc_n), "kpi_pdc"),
                (str(len(papers)), "kpi_papers_no_id"),
            ]
        )
        + f"""
<div class="page-content">
  <section class="section" id="projects">
    {section_head("sec_projects", len(items))}
    {section_desc("sec_projects_desc")}
    {note_i18n("note_projects_unified")}
    <div class="toolbar" id="proj-toolbar">
      <input type="search" id="q" data-i18n-placeholder="search_projects"/>
      <button type="button" class="chip active" data-filter="all" data-i18n="filter_all"></button>
      <button type="button" class="chip" data-filter="pride" data-i18n="filter_pride"></button>
      <button type="button" class="chip" data-filter="pdc" data-i18n="filter_pdc"></button>
      <span class="count-badge" id="count"></span>
    </div>
    <div class="table-wrap table-standard">
      <table id="tbl" class="data-table">
        <thead><tr>
          <th data-i18n="th_id"></th><th data-i18n="th_title"></th><th data-i18n="th_source"></th>
          <th data-i18n="th_plex"></th><th data-i18n="th_design"></th><th data-i18n="th_similar"></th>
          <th data-i18n="th_analysis"></th><th data-i18n="th_data"></th><th data-i18n="th_links"></th>
        </tr></thead>
        <tbody>{proj_rows}</tbody>
      </table>
    </div>
  </section>

  <section class="section" id="literature">
    {section_head("sec_literature", len(papers))}
    {section_desc("sec_literature_desc")}
    <div class="table-wrap table-standard">
      <table id="tbl-papers" class="data-table">
        <thead><tr>
          <th data-i18n="th_pmid"></th><th data-i18n="th_title"></th><th data-i18n="th_fit"></th>
          <th data-i18n="th_analysis"></th><th data-i18n="th_links"></th>
        </tr></thead>
        <tbody>{paper_rows}</tbody>
      </table>
    </div>
  </section>

  {qc_link}
</div>

<script>
(function() {{
  const q = document.getElementById('q');
  const tbl = document.getElementById('tbl');
  const rows = tbl ? [...tbl.querySelectorAll('tbody tr')] : [];
  const count = document.getElementById('count');
  let filter = 'all';
  function applyProjects() {{
    const term = (q?.value || '').toLowerCase().trim();
    let visible = 0;
    rows.forEach(r => {{
      const src = (r.dataset.src || '');
      const search = (r.dataset.search || '');
      const srcOk = filter === 'all' || (filter === 'pride' && src === 'pride') || (filter === 'pdc' && src === 'pdc');
      const textOk = !term || search.includes(term);
      const show = srcOk && textOk;
      r.style.display = show ? '' : 'none';
      if (show) visible++;
    }});
    if (count) count.textContent = visible + ' / {len(items)}';
  }}
  q?.addEventListener('input', applyProjects);
  document.querySelectorAll('#proj-toolbar .chip[data-filter]').forEach(btn => {{
    btn.addEventListener('click', () => {{
      document.querySelectorAll('#proj-toolbar .chip').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      filter = btn.dataset.filter;
      applyProjects();
    }});
  }});
  applyProjects();
}})();
</script>
"""
    )

    out = Path(out_path or "reports/discovery_index.html")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page_wrap(active="discovery", body=body, title="Discovery", deploy=deploy), encoding="utf-8")
    return out
