"""HTML generators — unified layout via site_components."""
from __future__ import annotations

import html
from pathlib import Path

from atlas_agent.viz.site_components import (
    kpi_grid,
    meta_pill_i18n,
    meta_pill_text,
    meta_time,
    page_hero,
    section_head,
)
from atlas_agent.viz.site_theme import page_wrap

GITHUB_TMT = "https://github.com/arinaatom-cyber/TMT"


def _esc(s: object) -> str:
    return html.escape(str(s or ""))


def _bar_rows(data: dict, *, limit: int = 10) -> str:
    if not data:
        return '<p class="muted cell-empty" data-i18n="cell_empty"></p>'
    items = sorted(data.items(), key=lambda x: -x[1])[:limit]
    mx = max(v for _, v in items) or 1
    rows = []
    for label, val in items:
        pct = int(100 * val / mx)
        rows.append(
            f'<div class="bar-row">'
            f'<span class="bar-label" title="{_esc(label)}">{_esc(label)}</span>'
            f'<div class="bar-track"><div class="bar-fill" style="width:{pct}%"></div></div>'
            f'<span class="bar-val">{val}</span></div>'
        )
    return "\n".join(rows)


def _tags(items: list[str], *, limit: int = 16) -> str:
    if not items:
        return '<p class="muted cell-empty" data-i18n="cell_empty"></p>'
    return '<div class="tag-list">' + "".join(
        f'<span class="tag">{_esc(x)}</span>' for x in items[:limit]
    ) + "</div>"


def generate_atlas_html(report: dict, out_path: str | Path, *, deploy: str = "docs_site") -> Path:
    profile = report.get("catalog_profile") or {}
    s = report.get("summary") or {}
    gen = report.get("generated_at") or ""
    n_ids = s.get("catalog_unique_ids") or profile.get("n_unique_ids") or "—"
    n_rows = profile.get("n_rows") or "—"

    meta = meta_time(gen) + meta_pill_i18n("badge_readonly", css="badge-ok")
    body = (
        page_hero("atlas_title", "atlas_lead", meta)
        + kpi_grid(
            [
                (str(n_rows), "atlas_datasets"),
                (str(n_ids), "atlas_publications"),
                (str(len(profile.get("tmt_plexes") or [])), "atlas_tmt"),
            ]
        )
        + f"""
<div class="page-content">
  <div class="profile-grid">
    <div class="card">
      <h2 data-i18n="atlas_repos"></h2>
      {_bar_rows(profile.get("databases") or {})}
    </div>
    <div class="card">
      <h2 data-i18n="atlas_organs"></h2>
      {_tags(profile.get("top_organs") or [])}
    </div>
    <div class="card">
      <h2 data-i18n="atlas_diseases"></h2>
      {_tags(profile.get("top_diseases") or [])}
    </div>
    <div class="card">
      <h2 data-i18n="atlas_tmt"></h2>
      {_tags(profile.get("tmt_plexes") or [])}
    </div>
  </div>

  <section class="section">
    {section_head("atlas_keywords")}
    <div class="note">{_esc(", ".join(profile.get("search_keywords") or [])[:500])}</div>
  </section>

  <section class="section">
    <div class="btn-row">
      <a class="btn btn-primary" href="{GITHUB_TMT}" target="_blank" rel="noopener" data-i18n="atlas_link"></a>
      <a class="btn" href="discovery.html" data-i18n="atlas_discovery"></a>
    </div>
  </section>
</div>"""
    )

    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page_wrap(active="atlas", body=body, title="Atlas", deploy=deploy), encoding="utf-8")
    return out
