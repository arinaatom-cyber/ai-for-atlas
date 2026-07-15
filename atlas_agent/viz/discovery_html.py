"""HTML Discovery: new projects + LLM abstract analysis (bilingual UI)."""
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


def _ai_summary(item: dict) -> str:
    ai = item.get("abstract_ai") or {}
    parts = []
    summary = ai.get("summary_en") or ai.get("summary_ru") or item.get("summary_en") or ""
    if summary:
        parts.append(_esc(summary))
    fit = ai.get("atlas_fit") or item.get("atlas_fit")
    score = ai.get("atlas_fit_score") or item.get("atlas_fit_score")
    if fit:
        parts.append(f'<span class="badge {_fit_class(fit)}">{_esc(fit)} {score or ""}</span>')
    ev = ai.get("semantic_evidence") or item.get("semantic_evidence") or []
    if ev:
        parts.append(f'<span class="muted">→ {_esc("; ".join(ev[:3]))}</span>')
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
    samples = (
        da.get("proteome_files")
        or da.get("quant_files")
        or da.get("phospho_files")
        or da.get("sample_files")
        or []
    )
    hint = ""
    if samples:
        hint = f'<br/><span class="muted">{_esc(samples[0][:50])}</span>'
    if da.get("local_mirror"):
        hint += '<br/><span class="muted">local</span>'
    guidance = _esc(da.get("guidance") or "")
    if guidance:
        hint += f'<br/><span class="muted">{guidance}</span>'
    return f'<span class="badge {cls}">{label}</span>{hint}'


def _finding_cell(it: dict) -> str:
    note = it.get("finding_note") or format_finding_note(it)
    if note:
        return f'<span class="muted">{_esc(note[:420])}</span>'
    return _ai_summary(it)


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


def _project_rows(items: list[dict]) -> str:
    rows = []
    for it in items:
        raw_acc = (it.get("project_accession") or it.get("accession") or "").strip().upper()
        acc_esc = _esc(raw_acc or "—")
        title_raw = (it.get("title") or "")[:140]
        title = _esc(title_raw)
        src = _esc(_source_label(it))
        plex = it.get("inferred_plex") or it.get("tmt_label") or ""
        design = _esc(str(it.get("sample_design") or ""))
        sim = (it.get("similar_in_catalog") or [{}])[0]
        sim_id = _esc(str(sim.get("project_id") or ""))
        sim_score = sim.get("score", "")
        analysis = _ai_summary(it)
        finding = _finding_cell(it)
        data = _data_cell(it)
        links = _links_cell(it)
        repo = it.get("repository_url") or it.get("url") or repository_url(raw_acc)
        pub = it.get("pubmed_url") or pubmed_url(it.get("pmid"))
        if repo:
            id_cell = f'<a href="{_esc(repo)}" target="_blank" rel="noopener" class="cell-mono"><b>{acc_esc}</b></a>'
        else:
            id_cell = f'<span class="cell-mono"><b>{acc_esc}</b></span>'
        if pub:
            title_cell = (
                f'<a href="{_esc(pub)}" target="_blank" rel="noopener" class="cell-title">{title}</a>'
            )
        elif repo:
            title_cell = (
                f'<a href="{_esc(repo)}" target="_blank" rel="noopener" class="cell-title">{title}</a>'
            )
        else:
            title_cell = f'<span class="cell-title">{title}</span>'
        program = _esc(str(it.get("program") or it.get("disease") or "")[:60])
        rows.append(
            f"<tr data-src='{src.lower()}' data-search='{acc_esc.lower()} {title.lower()} {program.lower()}'>"
            f"<td>{id_cell}</td><td>{title_cell}</td><td>{src}</td>"
            f"<td>{plex}</td><td>{design}</td><td>{sim_id} ({sim_score})</td>"
            f"<td class='analysis-cell'>{analysis}</td><td class='analysis-cell'>{finding}</td>"
            f"<td>{data}</td><td class='cell-links'>{links}</td></tr>"
        )
    return "\n".join(rows) or '<tr><td colspan="10" data-i18n="no_projects"></td></tr>'


def _publication_rows(pubs: list[dict]) -> str:
    rows = []
    for p in pubs:
        pmid = _esc(p.get("pmid") or "—")
        title = _esc((p.get("title") or "")[:120])
        fit = p.get("atlas_fit") or "?"
        score = p.get("atlas_fit_score", "")
        reader = _esc(p.get("abstract_reader") or "")
        org = _esc(p.get("organism") or "")
        tmt = _esc(p.get("tmt") or "")
        mat = _esc(p.get("material") or "")
        theme = _esc(p.get("similar_atlas_theme") or "")
        search = _esc(p.get("pride_search_terms") or "")
        summary = _esc(p.get("summary_en") or p.get("summary_ru") or "")
        data_hint = _esc(p.get("data_hint") or "")
        ev = _esc("; ".join(p.get("semantic_evidence") or [])[:4])
        acc = p.get("accessions") or {}
        ids = ", ".join(x for k in ("PXD", "PDC", "MSV", "IPX") for x in (acc.get(k) or [])) or "—"
        pmid_link = (
            f'<a href="https://pubmed.ncbi.nlm.nih.gov/{_esc(p["pmid"])}/" '
            f'target="_blank" rel="noopener">{pmid}</a>'
            if p.get("pmid")
            else pmid
        )
        rows.append(
            f"<tr data-fit='{_esc(fit)}' data-search='{title.lower()} {summary.lower()}'>"
            f"<td>{pmid_link}</td><td>{title}</td>"
            f"<td><span class='badge {_fit_class(fit)}'>{_esc(fit)} {score}</span></td>"
            f"<td>{org}</td><td>{tmt}</td><td>{mat}</td>"
            f"<td>{ids}</td><td>{theme}</td><td>{search}</td>"
            f"<td class='analysis-cell'>{summary}<br/><span class='muted'>{ev}</span></td>"
            f"<td class='muted'>{data_hint}</td>"
            f"<td class='muted'>{reader}</td></tr>"
        )
    return "\n".join(rows)


def _literature_rows(items: list[dict]) -> str:
    rows = []
    for it in items:
        pmid = it.get("pmid") or ""
        label = _esc(it.get("project_accession") or f"PMID:{pmid}")
        title = _esc((it.get("title") or "")[:120])
        fit = it.get("atlas_fit") or "?"
        score = it.get("atlas_fit_score", "")
        search = _esc(it.get("pride_search_terms") or (it.get("abstract_ai") or {}).get("pride_search_terms", ""))
        summary = _ai_summary(it)
        note = _esc(it.get("finding_note") or format_finding_note(it) or "; ".join((it.get("filter_reasons") or [])[:2]))
        link = (
            f'<a href="https://pubmed.ncbi.nlm.nih.gov/{_esc(pmid)}/" target="_blank" rel="noopener">PubMed</a>'
            if pmid
            else ""
        )
        rows.append(
            f"<tr><td><b>{label}</b></td><td>{title}</td>"
            f"<td><span class='badge {_fit_class(fit)}'>{_esc(fit)} {score}</span></td>"
            f"<td>{search}</td><td class='analysis-cell'>{summary}</td>"
            f"<td>{note}</td><td>{link}</td></tr>"
        )
    return "\n".join(rows)


def _qc_rows(items: list[dict]) -> str:
    rows = []
    for it in items:
        acc = _esc(it.get("project_accession") or it.get("accession") or "—")
        title = _esc((it.get("title") or "")[:100])
        reasons = _esc("; ".join((it.get("qc_reasons") or it.get("filter_reasons") or [])[:2]))
        sig = it.get("material_signals") or {}
        inc = _esc(", ".join(sig.get("included") or [])[:60])
        exc = _esc(", ".join(sig.get("excluded") or [])[:60])
        rows.append(
            f"<tr><td><b>{acc}</b></td><td>{title}</td>"
            f"<td>{inc}</td><td>{exc}</td><td>{reasons}</td></tr>"
        )
    return "\n".join(rows)


def generate_discovery_html(report: dict, out_path: str | Path | None = None, *, deploy: str = "docs_site") -> Path:
    s = report.get("summary") or {}
    items = report.get("candidates") or report.get("new_projects") or []
    pubs = report.get("publications_analyzed") or []
    literature = report.get("literature_semantic") or []
    manual = report.get("manual_check") or []
    rejected = report.get("rejected_material") or []
    stats = s.get("source_stats") or {}
    gen = report.get("generated_at") or ""

    pride_n = sum(1 for x in items if _source_label(x) == "PRIDE")
    pdc_n = sum(1 for x in items if _source_label(x) == "PDC")
    fit_yes = sum(1 for p in pubs if p.get("atlas_fit") == "yes")
    fit_maybe = sum(1 for p in pubs if p.get("atlas_fit") == "maybe")

    proj_rows = _project_rows(items) or '<tr><td colspan="10" data-i18n="no_projects"></td></tr>'
    pub_rows = _publication_rows(pubs) or '<tr><td colspan="12" data-i18n="no_pubs"></td></tr>'
    lit_rows = _literature_rows(literature) or '<tr><td colspan="7" data-i18n="no_literature"></td></tr>'

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
                (str(pride_n), "kpi_pride"),
                (str(pdc_n), "kpi_pdc"),
                (str(stats.get("abstract_llm_read", 0)), "kpi_abstracts_ai"),
                (f"{fit_yes}/{fit_maybe}", "kpi_yes_maybe"),
                (str(len(manual)), "kpi_manual"),
                (str(len(rejected)), "kpi_rejected"),
            ]
        )
        + f"""
<div class="page-content">
  <section class="section" id="projects">
    {section_head("sec_projects", len(items))}
    {section_desc("sec_projects_desc")}
    <div class="toolbar" id="proj-toolbar">
      <input type="search" id="q" data-i18n-placeholder="search_projects"/>
      <button type="button" class="chip active" data-filter="all" data-i18n="filter_all"></button>
      <button type="button" class="chip" data-filter="pride" data-i18n="filter_pride"></button>
      <button type="button" class="chip" data-filter="pdc" data-i18n="filter_pdc"></button>
      <span class="count-badge" id="count"></span>
    </div>
    <div class="table-wrap">
      <table id="tbl">
        <thead><tr>
          <th data-i18n="th_id"></th><th data-i18n="th_title"></th><th data-i18n="th_source"></th>
          <th data-i18n="th_plex"></th><th data-i18n="th_design"></th><th data-i18n="th_similar"></th>
          <th data-i18n="th_ai"></th><th data-i18n="th_finding"></th><th data-i18n="th_data"></th><th data-i18n="th_links"></th>
        </tr></thead>
        <tbody>{proj_rows}</tbody>
      </table>
    </div>
  </section>

  <section class="section" id="abstracts">
    {section_head("sec_abstracts")}
    {note_i18n("note_abstracts")}
    <p class="stats-line">{_esc(f"PRIDE {stats.get('pride_v3_search', 0)} · PDC {stats.get('pdc_uiStudySummary', 0)} · MassIVE {stats.get('massive_json', 0)} · {stats.get('publications_scanned', 0)} pubs")}</p>
    <div class="toolbar">
      <input type="search" id="q-abs" data-i18n-placeholder="search_abstracts"/>
      <button type="button" class="chip active" data-afilter="all" data-i18n="filter_all"></button>
      <button type="button" class="chip" data-afilter="yes" data-i18n="filter_yes"></button>
      <button type="button" class="chip" data-afilter="maybe" data-i18n="filter_maybe"></button>
      <button type="button" class="chip" data-afilter="no" data-i18n="filter_no"></button>
    </div>
    <div class="table-wrap">
      <table id="tbl-abs">
        <thead><tr>
          <th data-i18n="th_pmid"></th><th data-i18n="th_title"></th><th data-i18n="th_fit"></th>
          <th data-i18n="th_organism"></th><th data-i18n="th_tmt"></th><th data-i18n="th_material"></th>
          <th data-i18n="th_ids"></th><th data-i18n="th_theme"></th><th data-i18n="th_pride"></th>
          <th data-i18n="th_analysis"></th><th data-i18n="th_supplementary"></th><th data-i18n="th_reader"></th>
        </tr></thead>
        <tbody>{pub_rows}</tbody>
      </table>
    </div>
  </section>

  <section class="section" id="literature">
    {section_head("sec_literature", len(literature))}
    {section_desc("sec_literature_desc")}
    <div class="table-wrap">
      <table>
        <thead><tr>
          <th data-i18n="th_pmid"></th><th data-i18n="th_title"></th><th data-i18n="th_fit"></th>
          <th data-i18n="th_pride"></th><th data-i18n="th_ai"></th><th data-i18n="th_reason"></th>
          <th data-i18n="th_link"></th>
        </tr></thead>
        <tbody>{lit_rows}</tbody>
      </table>
    </div>
  </section>

  <section class="section" id="qc">
    {section_head("sec_qc")}
    <h3 class="text-secondary"><span data-i18n="qc_manual"></span> <span class="section-count">{len(manual)}</span></h3>
    <div class="table-wrap">
      <table><thead><tr>
        <th data-i18n="th_id"></th><th data-i18n="th_title"></th>
        <th data-i18n="th_included"></th><th data-i18n="th_excluded"></th><th data-i18n="th_reason"></th>
      </tr></thead><tbody>{_qc_rows(manual)}</tbody></table>
    </div>
    <h3 class="text-secondary"><span data-i18n="qc_rejected"></span> <span class="section-count">{len(rejected)}</span></h3>
    <div class="table-wrap">
      <table><thead><tr>
        <th data-i18n="th_id"></th><th data-i18n="th_title"></th>
        <th data-i18n="th_included"></th><th data-i18n="th_excluded"></th><th data-i18n="th_reason"></th>
      </tr></thead><tbody>{_qc_rows(rejected)}</tbody></table>
    </div>
  </section>
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

  const qAbs = document.getElementById('q-abs');
  const absRows = [...document.querySelectorAll('#tbl-abs tbody tr')];
  let aFilter = 'all';
  function applyAbs() {{
    const term = (qAbs?.value || '').toLowerCase().trim();
    absRows.forEach(r => {{
      const fit = (r.dataset.fit || '').toLowerCase();
      const search = (r.dataset.search || '');
      const fitOk = aFilter === 'all' || fit === aFilter;
      const textOk = !term || search.includes(term);
      r.style.display = fitOk && textOk ? '' : 'none';
    }});
  }}
  qAbs?.addEventListener('input', applyAbs);
  document.querySelectorAll('[data-afilter]').forEach(btn => {{
    btn.addEventListener('click', () => {{
      document.querySelectorAll('[data-afilter]').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      aFilter = btn.dataset.afilter;
      applyAbs();
    }});
  }});
  applyAbs();
}})();
</script>
"""
    )

    out = Path(out_path or "reports/discovery_index.html")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page_wrap(active="discovery", body=body, title="Discovery", deploy=deploy), encoding="utf-8")
    return out
