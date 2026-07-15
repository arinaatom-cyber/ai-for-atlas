"""HTML QC report Discovery (bilingual UI)."""
from __future__ import annotations

import html
from pathlib import Path

from atlas_agent.viz.portal_index import format_finding_note
from atlas_agent.viz.site_sanitize import translate_legacy_text
from atlas_agent.viz.site_components import kpi_grid, meta_time, note_rules, page_hero, section_head
from atlas_agent.viz.site_theme import page_wrap


def _ai_cell(it: dict) -> str:
    ai = it.get("abstract_ai") or it
    parts = []
    if ai.get("summary_en") or ai.get("summary_ru"):
        parts.append(html.escape(str(ai.get("summary_en") or ai.get("summary_ru"))[:200]))
    fit = ai.get("atlas_fit") or it.get("atlas_fit")
    score = ai.get("atlas_fit_score") or it.get("atlas_fit_score")
    if fit:
        cls = {"yes": "fit-yes", "maybe": "fit-maybe", "no": "fit-no"}.get(str(fit).lower(), "fit-unk")
        parts.append(f'<span class="badge {cls}">{html.escape(str(fit))} {score or ""}</span>')
    ev = ai.get("semantic_evidence") or it.get("semantic_evidence") or []
    if ev:
        parts.append(f'<span class="muted">{html.escape("; ".join(ev[:3]))}</span>')
    return "<br/>".join(parts) if parts else '<span class="cell-empty" data-i18n="cell_empty"></span>'


def _rows(items: list[dict]) -> str:
    out = []
    for it in items:
        acc = html.escape(it.get("project_accession") or it.get("accession") or "—")
        title = html.escape((it.get("title") or "")[:120])
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
            f"<tr><td class='cell-mono'><b>{acc}</b></td><td class='cell-title'>{title}</td>"
            f"<td>{plex}</td><td>{inc}</td><td>{exc}</td>"
            f"<td class='analysis-cell'>{ai_col}</td><td>{da_col}</td><td>{reasons}</td></tr>"
        )
    return "\n".join(out) or '<tr><td colspan="8" data-i18n="no_rows"></td></tr>'


def _table_head(notes: bool = False) -> str:
    notes_th = '<th data-i18n="th_notes"></th>' if notes else '<th data-i18n="th_reason"></th>'
    return f"""<thead><tr>
      <th data-i18n="th_id"></th><th data-i18n="th_title"></th><th data-i18n="th_plex"></th>
      <th data-i18n="th_included"></th><th data-i18n="th_excluded"></th><th data-i18n="th_ai"></th>
      <th data-i18n="th_data"></th>{notes_th}
    </tr></thead>"""


def generate_qc_html(report: dict, out_path: str | Path, *, deploy: str = "docs_site") -> Path:
    s = report.get("summary") or {}
    cand = report.get("candidates") or report.get("new_projects") or []
    manual = report.get("manual_check") or []
    rejected = report.get("rejected_material") or []
    technical = report.get("filtered_out") or []
    pubs = report.get("publications_analyzed") or []
    stats = s.get("source_stats") or {}
    gen = report.get("generated_at") or ""

    meta = meta_time(gen) + ' <span class="meta-pill badge badge-muted" data-i18n="badge_readonly"></span>'
    body = (
        page_hero("qc_title", "qc_lead", meta)
        + kpi_grid(
            [
                (str(len(cand)), "qc_candidate"),
                (str(len(manual)), "qc_manual"),
                (str(len(rejected)), "qc_rejected"),
                (str(len(technical)), "qc_filtered"),
                (str(stats.get("abstract_llm_read", 0)), "kpi_abstracts_ai"),
                (str(len(pubs)), "qc_pubs"),
            ]
        )
        + f"""
<div class="page-content">
  {note_rules("qc_rules_title", "qc_rules")}

  <section class="section">
    {section_head("qc_candidate", len(cand))}
    <div class="table-wrap">
      <table>{_table_head(notes=True)}<tbody>{_rows(cand)}</tbody></table>
    </div>
  </section>

  <section class="section">
    {section_head("qc_manual", len(manual))}
    <div class="table-wrap">
      <table>{_table_head()}<tbody>{_rows(manual)}</tbody></table>
    </div>
  </section>

  <section class="section">
    {section_head("qc_rejected", len(rejected))}
    <div class="table-wrap">
      <table>{_table_head()}<tbody>{_rows(rejected)}</tbody></table>
    </div>
  </section>
  <section class="section">
    {section_head("qc_filtered", len(technical))}
    <div class="table-wrap">
      <table>{_table_head()}<tbody>{_rows(technical)}</tbody></table>
    </div>
  </section>
</div>"""
    )

    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page_wrap(active="qc", body=body, title="QC", deploy=deploy), encoding="utf-8")
    return out


def qc_markdown_summary(report: dict) -> str:
    s = report.get("summary") or {}
    lines = [
        "## QC материала образцов",
        "",
        f"- **Candidate:** {s.get('candidates', 0)}",
        f"- **Requires manual check:** {s.get('manual_check', 0)}",
        f"- **Rejected (material):** {s.get('rejected_material', 0)}",
        f"- **Filtered (technical):** {s.get('filtered_out', 0)}",
        "",
        "Правила: Homo sapiens; tumor/adjacent/plasma/blood/human cancer cell lines; "
        "исключить spheroids/organoids-only, PDX-only, xenograft-only, animal tissue.",
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
