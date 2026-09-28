from __future__ import annotations

import html
import re
from pathlib import Path

from atlas_agent.viz.discovery_stats import (
    classify_accepted_material,
    passed_candidates,
    summarize_report,
)
from atlas_agent.viz.discovery_table_shared import _first_accession, _id_cell, _title_cell
from atlas_agent.viz.display_format import clean_taxonomy_value
from atlas_agent.viz.i18n_defaults import BRAND_NAME
from atlas_agent.viz.portal_index import article_description, pubmed_url, repository_url, resolve_publication_links
from atlas_agent.viz.site_components import cadence_pills, dashboard_kpis, meta_time, page_hero, section_head
from atlas_agent.viz.site_theme import page_wrap


def _material_label(kind: str) -> tuple[str, str]:
    keys = {
        "cell_line": "kpi_cell_line",
        "tissue": "kpi_tissue",
        "primary_site": "kpi_primary_site",
    }
    return keys.get(kind, "kpi_tissue"), kind


def _site_cell(it: dict) -> str:
    site = clean_taxonomy_value(it.get("primary_site"))
    if site:
        return html.escape(site)
    return '<span class="cell-empty">—</span>'


def _ai_cell(it: dict) -> str:
    ai = it.get("abstract_ai") or {}
    en = str(
        ai.get("summary_en")
        or it.get("abstract_snippet")
        or it.get("abstract")
        or it.get("description")
        or ""
    ).strip()
    if not en:
        return '<span class="cell-empty" data-i18n="cell_empty"></span>'
    return f'<span class="cell-finding-block">{html.escape(en[:260])}</span>'


def _accepted_rows(items: list[dict]) -> str:
    out = []
    for it in items:
        resolve_publication_links(it, fetch_pride_pmid=False)
        acc = _first_accession(it) or str(it.get("project_accession") or it.get("accession") or "").strip()
        repo = it.get("repository_url") or it.get("url") or repository_url(acc)
        pmid = re.sub(r"\D", "", str(it.get("pmid") or ""))
        title = (it.get("title") or "").strip()
        desc = article_description(it)
        pub = it.get("pubmed_url") or pubmed_url(pmid)
        plex = it.get("tmt_label") or it.get("inferred_plex") or "—"
        kind = classify_accepted_material(it)
        mat_key, _ = _material_label(kind)
        da = it.get("data_availability") or {}
        da_col = html.escape(da.get("label") or da.get("status") or "—")
        if da.get("quant_files"):
            da_col += "<br/><span class='muted'>" + html.escape(str(da["quant_files"][0])[:72]) + "</span>"
        out.append(
            f"<tr data-material='{html.escape(kind)}'>"
            f"<td class='col-id'>{_id_cell(acc=acc, repo=repo, pmid=pmid, title=title)}</td>"
            f"<td class='col-title'>{_title_cell(title, pub, repo, description=desc, acc=acc, pmid=pmid, show_desc=False)}</td>"
            f"<td class='col-material'><span class='badge badge-ok' data-i18n='{mat_key}'></span></td>"
            f"<td class='col-site'>{_site_cell(it)}</td>"
            f"<td class='col-plex cell-mono'>{html.escape(str(plex))}</td>"
            f"<td class='col-finding'>{_ai_cell(it)}</td>"
            f"</tr>"
        )
    return "\n".join(out) or '<tr><td colspan="6" data-i18n="no_rows"></td></tr>'


def generate_qc_html(report: dict, out_path: str | Path, *, deploy: str = "docs_site") -> Path:
    from atlas_agent.viz.site_sanitize import sanitize_report_for_site

    report = sanitize_report_for_site(dict(report))
    stats = summarize_report(report)
    passed = passed_candidates(report)
    gen = report.get("generated_at") or ""
    meta = meta_time(gen) + " " + cadence_pills()
    body = (
        page_hero("qc_title", "qc_lead", meta)
        + dashboard_kpis(stats)
        + f"""
<div class="page-content page-content-wide">
  <section class="section">
    {section_head("qc_candidate", stats["accepted"])}
    <p class="section-desc" data-i18n="qc_candidate_desc"></p>
    <div class="table-wrap table-unified table-qc">
      <table class="data-table">
        <thead><tr>
          <th class="col-id" data-i18n="th_id"></th>
          <th class="col-title" data-i18n="th_title"></th>
          <th class="col-material" data-i18n="th_material"></th>
          <th class="col-site" data-i18n="th_primary_site"></th>
          <th class="col-plex" data-i18n="th_plex"></th>
          <th class="col-finding" data-i18n="th_finding"></th>
        </tr></thead>
        <tbody>{_accepted_rows(passed)}</tbody>
      </table>
    </div>
  </section>
</div>"""
    )

    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page_wrap(active="qc", body=body, title=BRAND_NAME, deploy=deploy), encoding="utf-8")
    return out


def qc_markdown_summary(report: dict) -> str:
    stats = summarize_report(report)
    return "\n".join(
        [
            "## Контроль качества материала",
            "",
            f"- **Проверено:** {stats['checked']}",
            f"- **Принято:** {stats['accepted']}",
            f"- **Клеточная линия:** {stats['cell_line']}",
            f"- **Ткань:** {stats['tissue']}",
            f"- **Primary site:** {stats['primary_site']}",
            "",
            "Каждый понедельник локальная нейросеть проверяет кандидатов. "
            "На сайте — только принятые: ткань, клеточная линия или primary site.",
            "",
        ]
    )
