"""HTML Discovery: projects + papers w/o ID + large cohorts (one page)."""
from __future__ import annotations

import html
from pathlib import Path

from atlas_agent.viz.cohorts_html import build_cohort_table_rows
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
from atlas_agent.viz.portal_index import (
    europe_pmc_url,
    format_finding_note,
    pubmed_url,
    repository_url,
)
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


def _weight_badge(fit: str, score: object) -> str:
    fit_s = str(fit or "?").strip()
    score_s = str(score or "").strip()
    label = f"{fit_s} ({score_s})" if score_s else fit_s
    return f'<span class="badge {_fit_class(fit_s)}">{_esc(label)}</span>'


def _pub_index(pubs: list[dict]) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for p in pubs:
        pmid = str(p.get("pmid") or "").strip()
        if pmid:
            out[pmid] = p
    return out


def _analysis_cell(it: dict, pubs_by_pmid: dict[str, dict]) -> str:
    parts: list[str] = []
    note = it.get("finding_note") or format_finding_note(it)
    if note:
        parts.append(f'<span class="muted">{_esc(note[:420])}</span>')

    pmid = str(it.get("pmid") or "").strip()
    pub = pubs_by_pmid.get(pmid) if pmid else None
    if pub and pub.get("summary_en"):
        parts.append(f'<span class="muted llm-block">{_esc(pub["summary_en"][:300])}</span>')
    else:
        ai = it.get("abstract_ai") or {}
        if ai.get("summary_en"):
            parts.append(f'<span class="muted llm-block">{_esc(ai["summary_en"][:300])}</span>')

    return "<br/>".join(parts) if parts else '<span class="cell-empty">—</span>'


def _data_cell(it: dict) -> str:
    da = it.get("data_availability") or {}
    if not da:
        return '<span class="cell-empty">—</span>'
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
    fname = _esc(samples[0][:70]) if samples else ""
    body = f'<span class="badge {cls}">{label}</span>'
    if fname:
        body += f'<br/><span class="muted file-hint">{fname}</span>'
    return body


def _repo_link(acc: str, repo: str) -> str:
    if not repo:
        return '<span class="cell-empty">—</span>'
    return (
        f'<a href="{_esc(repo)}" target="_blank" rel="noopener" class="link-repo">Project</a>'
    )


def _pubmed_link(pmid: str, pub_url: str) -> str:
    if not pub_url:
        return ""
    label = f"PubMed {pmid}" if pmid else "PubMed"
    return (
        f'<a href="{_esc(pub_url)}" target="_blank" rel="noopener" class="link-pub">{_esc(label)}</a>'
    )


def _epmc_link(pmid: str) -> str:
    if not pmid:
        return ""
    url = europe_pmc_url(pmid)
    return f'<a href="{_esc(url)}" target="_blank" rel="noopener" class="link-epmc">Europe PMC</a>'


def _source_link_cell(it: dict) -> str:
    acc = (it.get("project_accession") or it.get("accession") or "").strip().upper()
    label = _source_label(it)
    repo = it.get("repository_url") or it.get("url") or repository_url(acc)
    if repo:
        return (
            f'<a href="{_esc(repo)}" target="_blank" rel="noopener" class="cell-src"><b>{_esc(label)}</b></a>'
        )
    return f'<span class="cell-src"><b>{_esc(label)}</b></span>'


def _project_rows(items: list[dict], pubs_by_pmid: dict[str, dict]) -> str:
    rows = []
    for it in items:
        raw_acc = (it.get("project_accession") or it.get("accession") or "").strip().upper()
        acc_esc = _esc(raw_acc or "—")
        title_raw = (it.get("title") or "")[:140]
        title = _esc(title_raw)
        design = _esc(str(it.get("sample_design") or "—").replace("_", "-"))
        analysis = _analysis_cell(it, pubs_by_pmid)
        data = _data_cell(it)
        repo = it.get("repository_url") or it.get("url") or repository_url(raw_acc)
        pub = it.get("pubmed_url") or pubmed_url(it.get("pmid"))
        pmid = str(it.get("pmid") or "").strip()
        src_key = _source_label(it).lower()

        id_cell = (
            f'<a href="{_esc(repo)}" target="_blank" rel="noopener" class="cell-mono"><b>{acc_esc}</b></a>'
            if repo
            else f'<span class="cell-mono"><b>{acc_esc}</b></span>'
        )
        if pub:
            title_cell = f'<a href="{_esc(pub)}" target="_blank" rel="noopener" class="cell-title">{title}</a>'
        elif repo:
            title_cell = f'<a href="{_esc(repo)}" target="_blank" rel="noopener" class="cell-title">{title}</a>'
        else:
            title_cell = f'<span class="cell-title">{title}</span>'

        links = " · ".join(
            x for x in [_repo_link(raw_acc, repo), _pubmed_link(pmid, pub), _epmc_link(pmid)] if x
        ) or '<span class="cell-empty">—</span>'

        program = _esc(str(it.get("program") or it.get("disease") or "")[:60])
        rows.append(
            f"<tr data-src='{src_key}' data-search='{acc_esc.lower()} {title.lower()} {program.lower()}'>"
            f"<td class='col-id'>{id_cell}</td>"
            f"<td class='col-title'>{title_cell}</td>"
            f"<td class='col-src'>{_source_link_cell(it)}</td>"
            f"<td class='col-design'>{design}</td>"
            f"<td class='col-analysis analysis-cell'>{analysis}</td>"
            f"<td class='col-data'>{data}</td>"
            f"<td class='col-links cell-links'>{links}</td></tr>"
        )
    return "\n".join(rows)


def _first_accession(it: dict) -> str:
    for key in ("accessions_mentioned", "pxd_mentioned"):
        for acc in it.get(key) or []:
            a = str(acc).strip().upper()
            if a:
                return a
    ai = it.get("abstract_ai") or {}
    for group in (ai.get("accessions") or {}).values():
        for acc in group or []:
            a = str(acc).strip().upper()
            if a:
                return a
    return ""


def _paper_rows(items: list[dict]) -> str:
    rows = []
    for it in items:
        pmid = str(it.get("pmid") or "").strip()
        title_raw = (it.get("title") or "")[:140]
        title = _esc(title_raw)
        pub = pubmed_url(pmid)
        fit = it.get("atlas_fit") or (it.get("abstract_ai") or {}).get("atlas_fit") or "?"
        score = it.get("atlas_fit_score") or (it.get("abstract_ai") or {}).get("atlas_fit_score") or ""
        ai = it.get("abstract_ai") or {}
        summary = _esc(ai.get("summary_en") or it.get("summary_en") or "")
        note = _esc(it.get("finding_note") or format_finding_note(it) or "")

        pmid_cell = (
            f'<a href="{_esc(pub)}" target="_blank" rel="noopener" class="cell-mono"><b>{_esc(pmid)}</b></a>'
            if pmid and pub
            else f'<span class="cell-mono"><b>{_esc(pmid or "—")}</b></span>'
        )
        title_cell = (
            f'<a href="{_esc(pub)}" target="_blank" rel="noopener" class="cell-title">{title}</a>'
            if pub
            else f'<span class="cell-title">{title}</span>'
        )

        acc = _first_accession(it)
        repo = repository_url(acc) if acc else ""
        src_cell = _epmc_link(pmid) or '<span class="cell-empty">—</span>'

        links = " · ".join(
            x
            for x in [
                _pubmed_link(pmid, pub),
                _epmc_link(pmid),
                _repo_link(acc, repo) if repo else "",
            ]
            if x
        ) or '<span class="cell-empty">—</span>'

        analysis = summary
        if note and note != summary:
            analysis = f"{summary}<br/><span class='muted'>{note}</span>" if summary else f"<span class='muted'>{note}</span>"
        if not analysis:
            analysis = '<span class="cell-empty">—</span>'

        rows.append(
            f"<tr data-search='{title.lower()} {note.lower()} {pmid}'>"
            f"<td class='col-pmid'>{pmid_cell}</td>"
            f"<td class='col-title'>{title_cell}</td>"
            f"<td class='col-weight'>{_weight_badge(fit, score)}</td>"
            f"<td class='col-src'>{src_cell}</td>"
            f"<td class='col-analysis analysis-cell'>{analysis}</td>"
            f"<td class='col-links cell-links'>{links}</td></tr>"
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
    cohorts = report.get("cohort_literature") or []
    gen = report.get("generated_at") or ""
    pubs_by_pmid = _pub_index(pubs)

    pride_n = sum(1 for x in items if _source_label(x) == "PRIDE")
    pdc_n = sum(1 for x in items if _source_label(x) == "PDC")
    table_n = sum(
        1 for x in items
        if (x.get("data_availability") or {}).get("status") == "quant_table"
    )

    proj_rows = _project_rows(items, pubs_by_pmid) or '<tr><td colspan="7" data-i18n="no_projects"></td></tr>'
    paper_rows = _paper_rows(papers) or '<tr><td colspan="6" data-i18n="no_literature"></td></tr>'
    cohort_rows = build_cohort_table_rows(cohorts)

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
          <th data-i18n="th_design"></th><th data-i18n="th_analysis"></th><th data-i18n="th_data"></th>
          <th data-i18n="th_links"></th>
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
          <th data-i18n="th_pmid"></th><th data-i18n="th_title"></th><th data-i18n="th_weight"></th>
          <th data-i18n="th_source"></th><th data-i18n="th_analysis"></th><th data-i18n="th_links"></th>
        </tr></thead>
        <tbody>{paper_rows}</tbody>
      </table>
    </div>
  </section>

  <section class="section" id="cohorts">
    {section_head("sec_cohorts_on_discovery", len(cohorts))}
    {section_desc("sec_cohorts_on_discovery_desc")}
    {note_i18n("cohorts_note")}
    <div class="toolbar" id="cohort-toolbar">
      <input type="search" id="q-cohort" data-i18n-placeholder="search_cohorts"/>
      <button type="button" class="chip active" data-pfilter="all" data-i18n="filter_all"></button>
      <button type="button" class="chip" data-pfilter="yes" data-i18n="filter_patients_yes"></button>
      <button type="button" class="chip" data-pfilter="maybe" data-i18n="filter_patients_maybe"></button>
      <span class="count-badge" id="cohort-count"></span>
    </div>
    <div class="table-wrap table-standard">
      <table id="tbl-cohort" class="data-table">
        <thead><tr>
          <th data-i18n="th_pmid"></th><th data-i18n="th_title"></th><th data-i18n="th_description"></th>
          <th data-i18n="th_patients"></th><th data-i18n="th_n"></th><th data-i18n="th_omics"></th>
          <th data-i18n="th_tmt"></th><th data-i18n="th_multi"></th><th data-i18n="th_journal"></th>
          <th data-i18n="th_score"></th>
        </tr></thead>
        <tbody>{cohort_rows}</tbody>
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

(function() {{
  const q = document.getElementById('q-cohort');
  const tbl = document.getElementById('tbl-cohort');
  const rows = tbl ? [...tbl.querySelectorAll('tbody tr')] : [];
  const count = document.getElementById('cohort-count');
  let pf = 'all';
  function apply() {{
    const term = (q?.value || '').toLowerCase().trim();
    let n = 0;
    rows.forEach(r => {{
      const pat = r.dataset.patients || '';
      const search = (r.dataset.search || '');
      const patOk = pf === 'all' || pat === pf;
      const textOk = !term || search.includes(term);
      const show = patOk && textOk;
      r.style.display = show ? '' : 'none';
      if (show) n++;
    }});
    if (count) count.textContent = n + ' / {len(cohorts)}';
  }}
  q?.addEventListener('input', apply);
  document.querySelectorAll('#cohort-toolbar .chip[data-pfilter]').forEach(btn => {{
    btn.addEventListener('click', () => {{
      document.querySelectorAll('#cohort-toolbar .chip').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      pf = btn.dataset.pfilter;
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
