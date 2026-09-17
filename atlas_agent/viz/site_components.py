"""Reusable layout blocks — единое оформление всех страниц Discovery."""
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


def page_hero(title_key: str, lead_key: str, meta_html: str) -> str:
    return f"""
<div class="page-hero">
  {i18n_el(title_key, tag="h1")}
  {i18n_el(lead_key, tag="p", cls="lead")}
  <div class="page-meta">{meta_html}</div>
</div>"""


def kpi_grid(items: list[tuple[str, str]]) -> str:
    """items: [(value, i18n_label_key), ...]"""
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
    """Structured scope note with live counts from the last scan."""
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
    """chips: [(data_attr, filter_value, i18n_or_label_key), ...]"""
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
