"""Organ map page — embeds interactive TMT body map (GitHub Pages)."""
from __future__ import annotations

from pathlib import Path
from urllib.parse import quote

from atlas_agent.viz.i18n_defaults import BRAND_NAME
from atlas_agent.viz.site_components import esc, i18n_el, meta_time, page_hero
from atlas_agent.viz.site_theme import LIVE_MAP, page_wrap


def _organ_chips(top_organs: list[str]) -> str:
    if not top_organs:
        return ""
    chips = []
    for organ in top_organs[:14]:
        key = organ.strip().replace(" ", "_")
        href = f"{LIVE_MAP}?organ={quote(key)}"
        label = esc(organ.replace("_", " "))
        chips.append(f'<a class="organ-chip" href="{href}" target="_blank" rel="noopener">{label}</a>')
    return f'<div class="organ-chip-grid">{"".join(chips)}</div>'


def generate_map_html(report: dict, out_path: str | Path, *, deploy: str = "docs_site") -> Path:
    profile = report.get("catalog_profile") or {}
    gen = report.get("generated_at") or ""
    organs = list(profile.get("top_organs") or [])
    n_cat = profile.get("n_unique_ids") or profile.get("n_rows") or "—"

    meta = meta_time(gen) + f'<span class="meta-pill badge badge-muted">{esc(n_cat)} atlas IDs</span>'

    body = (
        page_hero("map_title", "map_lead", meta)
        + f"""
<div class="page-content">
  <div class="how-to-panel">
    {i18n_el("map_how_title", tag="h3")}
    <ol class="how-to-steps">
      <li data-i18n="map_step1"></li>
      <li data-i18n="map_step2"></li>
      <li data-i18n="map_step3"></li>
    </ol>
  </div>
  <div class="embed-shell">
    <iframe
      class="embed-frame"
      src="{esc(LIVE_MAP)}"
      title="Human TMT organ map"
      loading="lazy"
      referrerpolicy="no-referrer-when-downgrade"
      allow="fullscreen"
    ></iframe>
    <div class="embed-toolbar">
      <a class="btn btn-primary" href="{esc(LIVE_MAP)}" target="_blank" rel="noopener" data-i18n="map_open_full"></a>
      <span class="muted embed-hint" data-i18n="map_embed_hint"></span>
    </div>
  </div>
  <div class="section-block">
    {i18n_el("map_organs_title", tag="h3")}
    {_organ_chips(organs)}
  </div>
</div>"""
    )

    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        page_wrap(active="map", body=body, title=f"{BRAND_NAME} — Organ map", deploy=deploy),
        encoding="utf-8",
    )
    return out
