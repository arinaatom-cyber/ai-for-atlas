from __future__ import annotations

import html

from atlas_agent.viz.i18n_defaults import en as i18n_default
from atlas_agent.viz.i18n_loader import ru_project_count, ru_row_count


def esc(s: object) -> str:
    return html.escape(str(s or ""))


def _t(key: str) -> str:
    return esc(i18n_default(key))


def i18n_el(key: str, *, tag: str = "span", cls: str = "") -> str:
    text = esc(i18n_default(key))
    extra = f' class="{cls}"' if cls else ""
    return f"<{tag}{extra} data-i18n=\"{key}\">{text}</{tag}>"


def meta_time(generated_at: str) -> str:
    gen = (generated_at or "")[:19].replace("T", " ")
    return (
        f'<span class="meta-pill badge badge-muted">'
        f'<span data-i18n="meta_updated">{esc(i18n_default("meta_updated"))}</span> {esc(gen)} UTC</span>'
    )


def meta_pill_i18n(key: str, *, css: str = "badge-muted") -> str:
    return (
        f'<span class="meta-pill badge {css}" data-i18n="{key}">{esc(i18n_default(key))}</span>'
    )


def meta_pill_text(text: str, *, css: str = "badge-muted") -> str:
    return f'<span class="meta-pill badge {css}">{esc(text)}</span>'


def page_hero(title_key: str, lead_key: str | None, meta_html: str) -> str:
    lead = i18n_el(lead_key, tag="p", cls="lead") if lead_key else ""
    return f"""
<div class="page-hero">
  {i18n_el(title_key, tag="h1")}
  {lead}
  <div class="page-meta">{meta_html}</div>
</div>"""


def kpi_grid(items: list[tuple[str, str]]) -> str:
    cells = "".join(
        f'<div class="kpi"><span class="kpi-value">{esc(v)}</span>'
        f'<span class="kpi-label" data-i18n="{k}">{_t(k)}</span></div>'
        for v, k in items
    )
    return f'<div class="kpi-grid">{cells}</div>'


def section_head(
    title_key: str,
    count: int | str | None = None,
    *,
    count_hint_key: str = "sec_unified_count_hint",
) -> str:
    cnt = ""
    if count is not None:
        cnt = (
            f'<span class="section-count" data-i18n-title="{count_hint_key}" '
            f'title="{_t(count_hint_key)}">'
            f"{esc(count)}</span>"
        )
    return (
        f'<div class="section-head">'
        f'<h2 data-i18n="{title_key}">{_t(title_key)}</h2>{cnt}</div>'
    )


def section_desc(key: str) -> str:
    return f'<p class="section-desc" data-i18n="{key}">{_t(key)}</p>'


def note_i18n(key: str) -> str:
    return f'<div class="note" data-i18n="{key}">{_t(key)}</div>'


def note_discovery_scope(*, new_projects: int, total_rows: int) -> str:
    stat_new = f"{ru_project_count(new_projects)} (KPI)"
    stat_total = f"{ru_row_count(total_rows)} в таблице"
    return f"""<aside class="note note-science" aria-label="Table scope">
  <p class="note-science-lead" data-i18n="note_scope_lead">{_t("note_scope_lead")}</p>
  <ul class="note-science-list">
    <li data-i18n="note_scope_row_types">{_t("note_scope_row_types")}</li>
    <li data-i18n="note_scope_kpi">{_t("note_scope_kpi")}</li>
    <li data-i18n="note_scope_filter">{_t("note_scope_filter")}</li>
  </ul>
  <p class="note-science-stats">
    <span class="note-stat">{esc(stat_new)}</span>
    <span class="note-stat-sep" aria-hidden="true">·</span>
    <span class="note-stat">{esc(stat_total)}</span>
  </p>
</aside>"""


def ai_agents_panel(manifest: dict) -> str:
    block = manifest.get("ai_agents") or {}
    pipeline_rows = "".join(
        f"<li>"
        f"<span class='lang-block lang-ru'><b>{esc(a.get('role_ru') or a.get('id'))}</b> — {esc(a.get('detail_ru') or '')}</span>"
        f"<span class='lang-block lang-en'><b>{esc(a.get('role_en') or a.get('id'))}</b> — {esc(a.get('detail_en') or '')}</span>"
        f"</li>"
        for a in (block.get("pipeline_agents") or [])
    )
    return f"""<div class="agents-panel">
  <p class="agents-lead" data-i18n="agents_lead">{_t("agents_lead")}</p>
  <h4 data-i18n="agents_pipeline">{_t("agents_pipeline")}</h4>
  <ul class="agents-list">{pipeline_rows}</ul>
</div>"""


def _funnel_bar(key: str, value: int, *, max_val: int, tone: str = "neutral") -> str:
    pct = 0 if max_val <= 0 else min(100, round(100 * int(value or 0) / max_val))
    return (
        f'<div class="funnel-row funnel-{tone}">'
        f'<span class="funnel-label" data-i18n="{esc(key)}">{_t(key)}</span>'
        f'<div class="funnel-bar-track" aria-hidden="true">'
        f'<div class="funnel-bar-fill" style="width:{pct}%"></div>'
        f"</div>"
        f'<span class="funnel-value">{esc(value or 0)}</span>'
        f"</div>"
    )


def _funnel_block(title_key: str, rows: list[tuple[str, int, str]]) -> str:
    vals = [v for _, v, _ in rows]
    max_val = max(vals) if vals else 1
    body = "".join(_funnel_bar(k, v, max_val=max_val, tone=tone) for k, v, tone in rows)
    return (
        f'<div class="funnel-block">'
        f'<h4 data-i18n="{esc(title_key)}">{_t(title_key)}</h4>'
        f'<div class="funnel-rows">{body}</div>'
        f"</div>"
    )


def scan_funnel_viz(
    *,
    funnel: dict,
    lit: dict,
    gate: dict,
    raw_repos: int,
) -> str:
    repo_rows = [
        ("funnel_raw_repos", int(raw_repos or 0), "input"),
        ("funnel_in_catalog", int(funnel.get("already_in_catalog") or 0), "muted"),
        ("funnel_filtered", int(funnel.get("filtered_out") or 0), "warn"),
        ("funnel_candidates", int(funnel.get("candidates") or 0), "ok"),
        ("funnel_manual", int(funnel.get("manual_check") or 0), "watch"),
        ("funnel_rejected", int(funnel.get("rejected_material") or 0), "bad"),
    ]
    lit_rows = [
        ("lit_scanned", int(lit.get("publications_scanned") or 0), "input"),
        ("lit_llm_read", int(lit.get("abstract_llm_read") or 0), "neutral"),
        ("lit_fit_yes", int(lit.get("atlas_fit_yes") or 0), "ok"),
        ("lit_fit_maybe", int(lit.get("atlas_fit_maybe") or 0), "watch"),
        ("lit_resolved", int(lit.get("literature_resolved") or 0), "ok"),
    ]
    gate_rows = [
        ("gate_quant_table", int(gate.get("quant_table") or 0), "ok"),
        ("gate_omics_protein", int(gate.get("omics_protein") or 0), "ok"),
        ("gate_no_files", int(gate.get("no_files") or 0), "warn"),
        ("gate_unknown", int(gate.get("omics_unknown") or 0), "warn"),
        ("gate_raw_only", int(gate.get("raw_only") or 0), "bad"),
    ]
    candidates = int(funnel.get("candidates") or 0)
    flow_svg = (
        f'<svg class="funnel-svg" viewBox="0 0 420 120" role="img" '
        f'aria-labelledby="funnel-svg-title">'
        f'<title id="funnel-svg-title">Screening funnel</title>'
        f'<defs><linearGradient id="funnelGrad" x1="0" y1="0" x2="0" y2="1">'
        f'<stop offset="0%" stop-color="var(--link)" stop-opacity="0.85"/>'
        f'<stop offset="100%" stop-color="var(--link)" stop-opacity="0.35"/>'
        f"</linearGradient></defs>"
        f'<polygon points="10,8 410,8 360,112 60,112" fill="url(#funnelGrad)" opacity="0.22"/>'
        f'<text x="210" y="34" text-anchor="middle" class="funnel-svg-label" '
        f'data-i18n="funnel_svg_in">{_t("funnel_svg_in")}</text>'
        f'<text x="210" y="54" text-anchor="middle" class="funnel-svg-num">{esc(raw_repos)}</text>'
        f'<text x="210" y="78" text-anchor="middle" class="funnel-svg-label" '
        f'data-i18n="funnel_svg_out">{_t("funnel_svg_out")}</text>'
        f'<text x="210" y="98" text-anchor="middle" class="funnel-svg-num funnel-svg-ok">{esc(candidates)}</text>'
        f"</svg>"
    )
    blocks = (
        _funnel_block("methods_funnel", repo_rows)
        + _funnel_block("methods_literature", lit_rows)
        + _funnel_block("methods_data_gate", gate_rows)
    )
    return f"""<div class="scan-funnel-viz">
  <p class="funnel-viz-lead" data-i18n="funnel_viz_lead">{_t("funnel_viz_lead")}</p>
  <div class="funnel-viz-layout">
    <div class="funnel-viz-chart">{flow_svg}</div>
    <div class="funnel-viz-bars">{blocks}</div>
  </div>
</div>"""


def scan_funnel_raw_stats(
    *,
    funnel: dict,
    lit: dict,
    gate: dict,
    raw_repos: int,
    st: dict,
) -> str:
    def li(key: str, val: object) -> str:
        return f'<li><span data-i18n="{esc(key)}">{_t(key)}</span> <b>{esc(val)}</b></li>'

    repo = "".join(
        li(k, v)
        for k, v in (
            ("funnel_raw_repos", raw_repos),
            ("funnel_in_catalog", funnel.get("already_in_catalog", 0)),
            ("funnel_filtered", funnel.get("filtered_out", 0)),
            ("funnel_candidates", funnel.get("candidates", 0)),
            ("funnel_manual", funnel.get("manual_check", 0)),
            ("funnel_rejected", funnel.get("rejected_material", 0)),
        )
    )
    literature = (
        li("lit_scanned", lit.get("publications_scanned", 0))
        + li("lit_llm_read", lit.get("abstract_llm_read", st.get("abstract_llm_read", 0)))
        + li("lit_regex_only", lit.get("abstract_regex_only", 0))
        + li("lit_exclusion_engine", lit.get("abstract_exclusion_engine", 0))
        + li("lit_llm_errors", sum((lit.get("abstract_llm_errors") or {}).values()) if isinstance(lit.get("abstract_llm_errors"), dict) else lit.get("abstract_llm_errors", 0))
        + li("lit_fit_yes", lit.get("atlas_fit_yes", 0))
        + li("lit_fit_maybe", lit.get("atlas_fit_maybe", 0))
        + li("lit_resolved", lit.get("literature_resolved", st.get("literature_resolved", 0)))
    )
    data_gate = (
        li("gate_quant_table", gate.get("quant_table", 0))
        + li("gate_omics_protein", gate.get("omics_protein", 0))
        + li("gate_raw_only", gate.get("raw_only", 0))
        + li("gate_no_files", gate.get("no_files", 0))
        + li("gate_unknown", gate.get("omics_unknown", 0))
    )
    return f"""<details class="site-fold methods-raw-stats">
  <summary data-i18n="methods_raw_stats">{_t("methods_raw_stats")}</summary>
  <div class="methods-grid methods-grid-compact">
    <div class="methods-card"><h3 data-i18n="methods_funnel"></h3><ul class="methods-stats">{repo}</ul></div>
    <div class="methods-card"><h3 data-i18n="methods_literature"></h3><ul class="methods-stats">{literature}</ul></div>
    <div class="methods-card"><h3 data-i18n="methods_data_gate"></h3><ul class="methods-stats">{data_gate}</ul></div>
  </div>
</details>"""


def pipeline_steps_panel(manifest: dict) -> str:
    pipe = manifest.get("pipeline") or {}
    steps = pipe.get("steps") or []
    repo = esc(pipe.get("github_repo") or "https://github.com/arinaatom-cyber/ai-for-atlas")
    r_count = pipe.get("stats_plans_count") or 0
    sim = esc(pipe.get("similarity_method") or "")
    example = esc(pipe.get("example_data_file") or "")
    rows = "".join(
        f"<tr>"
        f"<td class='cell-mono'><b>{esc(s.get('step'))}</b></td>"
        f"<td><span class='lang-block lang-ru'>{esc(s.get('stage_ru'))}</span>"
        f"<span class='lang-block lang-en'>{esc(s.get('stage_en'))}</span></td>"
        f"<td><code>{esc(s.get('language'))}</code></td>"
        f"<td><code class='file-name'>{esc(s.get('script'))}</code></td>"
        f"<td>{esc(s.get('agent') or '—')}</td>"
        f"<td><span class='lang-block lang-ru'>{esc(s.get('purpose_ru'))}</span>"
        f"<span class='lang-block lang-en'>{esc(s.get('purpose_en'))}</span></td>"
        f"</tr>"
        for s in steps
    )
    return f"""<div class="pipeline-panel">
  <p class="pipeline-lead" data-i18n="pipeline_lead">{_t("pipeline_lead")}</p>
  <p class="pipeline-meta">
    <span data-i18n="pipeline_similarity">{_t("pipeline_similarity")}</span>: <code>{sim}</code>
    · <span data-i18n="pipeline_example_file">{_t("pipeline_example_file")}</span>: <code class="file-name">{example}</code>
    · <span data-i18n="pipeline_r_plans">{_t("pipeline_r_plans")}</span>: <b>{esc(r_count)}</b>
  </p>
  <p class="pipeline-opensource">
    <a href="{repo}" target="_blank" rel="noopener" data-i18n="pipeline_github">{_t("pipeline_github")}</a>
  </p>
  <div class="table-wrap">
    <table class="data-table pipeline-table">
      <thead>
        <tr>
          <th data-i18n="pipe_th_step"></th>
          <th data-i18n="pipe_th_stage"></th>
          <th data-i18n="pipe_th_lang"></th>
          <th data-i18n="pipe_th_script"></th>
          <th data-i18n="pipe_th_agent"></th>
          <th data-i18n="pipe_th_purpose"></th>
        </tr>
      </thead>
      <tbody>{rows or '<tr><td colspan="6" data-i18n="no_rows"></td></tr>'}</tbody>
    </table>
  </div>
</div>"""


def note_rules(title_key: str, body_key: str) -> str:
    return (
        f'<div class="note"><strong data-i18n="{title_key}">{_t(title_key)}</strong> '
        f'<span data-i18n="{body_key}">{_t(body_key)}</span></div>'
    )


def toolbar_search(
    input_id: str,
    placeholder_key: str,
    chips: list[tuple[str, str, str]],
    count_id: str | None = None,
) -> str:
    chip_html = "".join(
        f'<button type="button" class="chip{" active" if i == 0 else ""}" '
        f'data-{attr}="{esc(val)}" data-i18n="{label}">{_t(label)}</button>'
        if label.startswith("filter_") or label.startswith("pat_") or label == "filter_all"
        else f'<button type="button" class="chip{" active" if i == 0 else ""}" '
        f'data-{attr}="{esc(val)}">{esc(label)}</button>'
        for i, (attr, val, label) in enumerate(chips)
    )
    count = f'<span class="count-badge" id="{count_id}"></span>' if count_id else ""
    return f"""
<div class="toolbar">
  <input type="search" id="{input_id}" data-i18n-placeholder="{placeholder_key}" placeholder="{_t(placeholder_key)}"/>
  {chip_html}
  {count}
</div>"""
