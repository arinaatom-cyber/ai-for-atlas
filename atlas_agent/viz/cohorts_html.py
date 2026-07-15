"""HTML: large proteomics / multi-omics cohort literature (dedicated page)."""
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
        return f'<span class="badge badge-ok">yes{_esc(extra)}</span>'
    if hp == "maybe":
        return '<span class="badge badge-warn">maybe</span>'
    return '<span class="badge badge-bad">no</span>'


def _omics_cell(item: dict) -> str:
    omics = item.get("omics") or []
    if not omics:
        return '<span class="cell-empty">—</span>'
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


def build_cohort_table_rows(items: list[dict]) -> str:
    rows = []
    for it in items:
        pmid = it.get("pmid") or ""
        title = _esc((it.get("title") or "")[:160])
        desc = _esc((it.get("description_en") or it.get("description_ru") or "")[:220])
        n = it.get("patient_n") or "—"
        score = it.get("cohort_score") or 0
        tmt = '<span class="badge badge-ok">TMT</span>' if it.get("tmt_detected") else '<span class="cell-empty">—</span>'
        multi = '<span class="badge badge-ok">✓</span>' if it.get("multi_omics") else '<span class="cell-empty">—</span>'
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
            f"<td>{pmid_link}</td><td class='col-title cell-clip'>{title}</td>"
            f"<td class='analysis-cell cell-clip'>{desc}</td><td>{_patient_badge(it)}</td>"
            f"<td class='cell-mono'><b>{_esc(n)}</b></td><td>{_omics_cell(it)}</td>"
            f"<td>{tmt}</td><td>{multi}</td><td class='text-secondary cell-clip'>{journal}</td>"
            f"<td class='cell-mono'>{score}</td></tr>"
        )
    return "\n".join(rows) or '<tr><td colspan="10" data-i18n="no_cohorts"></td></tr>'


def generate_cohorts_html(report: dict, out_path: str | Path, *, deploy: str = "docs_site") -> Path:
    """Legacy URL — redirect to unified Discovery table."""
    _ = report
    if deploy == "docs_portal":
        target = "site/discovery.html"
    else:
        target = "discovery.html"
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <meta http-equiv="refresh" content="0;url={target}"/>
  <title>Discovery</title>
  <script>location.replace("{target}");</script>
</head>
<body><p><a href="{target}">Discovery</a></p></body>
</html>""",
        encoding="utf-8",
    )
    return out
