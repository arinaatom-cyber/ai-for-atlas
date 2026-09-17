"""HTML QC report Discovery (bilingual UI)."""
from __future__ import annotations

import html
import re
from pathlib import Path

from atlas_agent.discovery.fit_rules import project_verdict
from atlas_agent.viz.discovery_table_shared import _first_accession, _id_cell, _title_cell
from atlas_agent.viz.portal_index import article_description, format_finding_note, pubmed_url, repository_url, resolve_publication_links
from atlas_agent.viz.site_sanitize import translate_legacy_text
from atlas_agent.viz.site_components import kpi_grid, meta_time, note_rules, page_hero, section_head
from atlas_agent.viz.i18n_defaults import BRAND_NAME
from atlas_agent.viz.site_theme import page_wrap


def _ai_cell(it: dict) -> str:
    ai = it.get("abstract_ai") or it
    parts = []
    en = str(ai.get("summary_en") or it.get("abstract_snippet") or it.get("abstract") or it.get("description") or "").strip()
    ru = str(ai.get("summary_ru") or "").strip()
    if en:
        parts.append(f'<span class="lang-block lang-en">{html.escape(en[:280])}</span>')
    if ru and ru != en:
        parts.append(f'<span class="lang-block lang-ru">{html.escape(ru[:280])}</span>')
    elif ru and not en:
        parts.append(f'<span class="lang-block lang-en lang-ru">{html.escape(ru[:280])}</span>')
    return "<br/>".join(parts) if parts else '<span class="cell-empty" data-i18n="cell_empty"></span>'


def _rows(items: list[dict]) -> str:
    out = []
    for it in items:
        resolve_publication_links(it, fetch_pride_pmid=False)
        acc = _first_accession(it) or str(it.get("project_accession") or it.get("accession") or "").strip()
        repo = it.get("repository_url") or it.get("url") or repository_url(acc)
        pmid = re.sub(r"\D", "", str(it.get("pmid") or ""))
        title = (it.get("title") or "").strip()
        desc = article_description(it)
        pub = it.get("pubmed_url") or pubmed_url(pmid)
        note = it.get("finding_note") or format_finding_note(it)
        if not note:
            raw = (it.get("qc_reasons") or it.get("filter_reasons") or [])[:2]
            note = "; ".join(translate_legacy_text(str(x)) for x in raw)
        reasons = html.escape(note[:320])
        sig = it.get("material_signals") or {}
        inc = html.escape(", ".join(sig.get("included") or [])[:80]) or "—"
        exc = html.escape(", ".join(sig.get("excluded") or [])[:80]) or "—"
        plex = it.get("tmt_label") or it.get("inferred_plex") or "—"
        ai_col = _ai_cell(it)
        da = it.get("data_availability") or {}
        da_col = html.escape(da.get("label") or da.get("status") or "—")
        if da.get("quant_files"):
            da_col += "<br/><span class='muted'>" + html.escape(da["quant_files"][0][:60]) + "</span>"
        out.append(
            f"<tr><td class='col-id'>{_id_cell(acc=acc, repo=repo, pmid=pmid)}</td>"
            f"<td class='col-title'>{_title_cell(title, pub, repo, description=desc, acc=acc, pmid=pmid)}</td>"
            f"<td class='col-plex cell-mono'>{html.escape(str(plex))}</td>"
            f"<td class='col-included'>{inc}</td><td class='col-excluded'>{exc}</td>"
            f"<td class='col-analysis analysis-cell'>{ai_col}</td>"
            f"<td class='col-data'>{da_col}</td><td class='col-reason'>{reasons}</td></tr>"
        )
    return "\n".join(out) or '<tr><td colspan="8" data-i18n="no_rows"></td></tr>'


def _split_candidates(items: list[dict]) -> tuple[list[dict], list[dict]]:
    passed: list[dict] = []
    excluded: list[dict] = []
    for it in items:
        if project_verdict(it)[0] == "Candidate":
            passed.append(it)
        else:
            excluded.append(it)
    return passed, excluded


def _table_head(notes: bool = False) -> str:
    reason_key = "th_notes" if notes else "th_reason"
    return f"""<thead><tr>
      <th class="col-id" data-i18n="th_id"></th>
      <th class="col-title" data-i18n="th_title"></th>
      <th class="col-plex" data-i18n="th_plex"></th>
      <th class="col-included" data-i18n="th_included"></th>
      <th class="col-excluded" data-i18n="th_excluded"></th>
      <th class="col-analysis" data-i18n="th_finding"></th>
      <th class="col-data" data-i18n="th_data"></th>
      <th class="col-reason" data-i18n="{reason_key}"></th>
    </tr></thead>"""


def generate_qc_html(report: dict, out_path: str | Path, *, deploy: str = "docs_site") -> Path:
    s = report.get("summary") or {}
    cand = report.get("candidates") or report.get("new_projects") or []
    passed, excluded = _split_candidates(cand)
    manual = [
        it
        for it in (report.get("repository_manual") or [])
        if (it.get("qc_status") == "requires_manual_check")
        or any(
            "Mixed" in str(x) or "3D" in str(x) or "organoid" in str(x).lower()
            for x in (it.get("qc_reasons") or it.get("filter_reasons") or [])
        )
    ]
    rejected = report.get("rejected_material") or []
    technical = report.get("filtered_out") or []
    stats = s.get("source_stats") or {}
    gen = report.get("generated_at") or ""

    meta = meta_time(gen) + ' <span class="meta-pill badge badge-muted" data-i18n="badge_readonly"></span>'
    body = (
        page_hero("qc_title", "qc_lead", meta)
        + kpi_grid(
            [
                (str(len(passed)), "qc_candidate"),
                (str(len(manual)), "qc_manual"),
                (str(len(excluded)), "qc_exclude"),
                (str(len(rejected)), "qc_rejected"),
                (str(len(technical)), "qc_filtered"),
                (str(stats.get("abstract_llm_read", 0)), "kpi_abstracts_ai"),
            ]
        )
        + f"""
<div class="page-content">
  {note_rules("qc_rules_title", "qc_rules")}

  <section class="section">
    {section_head("qc_candidate", len(passed))}
    <p class="section-desc" data-i18n="qc_candidate_desc"></p>
    <div class="table-wrap table-unified table-qc">
      <table class="data-table">{_table_head(notes=True)}<tbody>{_rows(passed)}</tbody></table>
    </div>
  </section>

  <section class="section">
    {section_head("qc_manual", len(manual))}
    <p class="section-desc" data-i18n="qc_manual_desc"></p>
    <div class="table-wrap table-unified table-qc">
      <table class="data-table">{_table_head()}<tbody>{_rows(manual)}</tbody></table>
    </div>
  </section>

  <section class="section">
    {section_head("qc_exclude", len(excluded))}
    <p class="section-desc" data-i18n="qc_exclude_desc"></p>
    <div class="table-wrap table-unified table-qc">
      <table class="data-table">{_table_head()}<tbody>{_rows(excluded)}</tbody></table>
    </div>
  </section>

  <section class="section">
    {section_head("qc_rejected", len(rejected))}
    <div class="table-wrap table-unified table-qc">
      <table class="data-table">{_table_head()}<tbody>{_rows(rejected)}</tbody></table>
    </div>
  </section>
  <section class="section">
    {section_head("qc_filtered", len(technical))}
    <div class="table-wrap table-unified table-qc">
      <table class="data-table">{_table_head()}<tbody>{_rows(technical)}</tbody></table>
    </div>
  </section>
</div>"""
    )

    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page_wrap(active="qc", body=body, title=BRAND_NAME, deploy=deploy), encoding="utf-8")
    return out


def qc_markdown_summary(report: dict) -> str:
    s = report.get("summary") or {}
    lines = [
        "## QC материала образцов",
        "",
        f"- **Candidate (passed):** {s.get('candidates', 0)}",
        f"- **Requires manual check:** {s.get('manual_check', 0)} + repository_manual",
        f"- **Rejected (material):** {s.get('rejected_material', 0)}",
        f"- **Filtered (technical):** {s.get('filtered_out', 0)}",
        "",
        "Правила: Homo sapiens; ткань (tumor/adjacent) или cancer cell line должна быть прописана "
        "в метаданных или статье; иначе reject. Исключить plasma/serum-only, spheroids/organoids-only, "
        "PDX-only, xenograft-only, animal tissue.",
        "",
    ]
    for label, key in (
        ("Manual check", "manual_check"),
        ("Rejected", "rejected_material"),
    ):
        items = report.get(key) or []
        if not items:
            continue
        lines.append(f"### {label} (top 10)")
        lines.append("")
        for it in items[:10]:
            acc = it.get("project_accession") or it.get("accession") or "?"
            rs = "; ".join((it.get("qc_reasons") or [])[:1])
            lines.append(f"- **{acc}** {(it.get('title') or '')[:70]} — {rs}")
        lines.append("")
    return "\n".join(lines)
