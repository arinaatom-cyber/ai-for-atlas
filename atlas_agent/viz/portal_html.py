"""Portal landing page (docs/index.html or TMT discovery/index.html)."""
from __future__ import annotations

from pathlib import Path

from atlas_agent.viz.i18n_defaults import ru as i18n_ru
from atlas_agent.viz.site_components import esc, i18n_el, meta_pill_text, meta_time, page_hero
from atlas_agent.viz.site_theme import (
    DEPLOY_DOCS_PORTAL,
    DEPLOY_TMT,
    LIVE_MAP,
    page_wrap,
)


def _page_href(deploy: str, page: str) -> str:
    if deploy == DEPLOY_DOCS_PORTAL:
        return f"site/{page}.html"
    return f"{page}.html"


def generate_portal_html(
    out_path: str | Path,
    *,
    meta: dict | None = None,
    deploy: str = DEPLOY_DOCS_PORTAL,
) -> Path:
    meta_d = meta or {}
    gen = meta_d.get("generated_at") or ""
    n_cand = meta_d.get("new_projects_count", "—")
    n_cat = meta_d.get("catalog_unique_ids", "—")

    meta_html = (
        meta_time(gen)
        + meta_pill_text(str(n_cand), css="badge-ok")
        + f' <span class="meta-pill badge badge-ok" data-i18n="meta_candidates">{esc(i18n_ru("meta_candidates"))}</span>'
        + meta_pill_text(str(n_cat))
        + f' <span class="meta-pill badge badge-muted" data-i18n="meta_atlas_ids">{esc(i18n_ru("meta_atlas_ids"))}</span>'
    )

    map_href = "../index.html" if deploy == DEPLOY_TMT else LIVE_MAP
    map_target = "" if deploy == DEPLOY_TMT else ' target="_blank" rel="noopener"'

    def card(
        title_key: str,
        desc_key: str,
        href: str,
        *,
        primary: bool = True,
        extra: str = "",
        target: str = "",
    ) -> str:
        btn_cls = "btn btn-primary" if primary else "btn"
        return f"""
    <div class="card">
      {i18n_el(title_key, tag="h2")}
      {i18n_el(desc_key, tag="p")}
      <div class="btn-row">
        <a class="{btn_cls}" href="{esc(href)}"{target} data-i18n="card_open">{esc(i18n_ru("card_open"))}</a>
        {extra}
      </div>
    </div>"""

    json_extra = (
        f'<a class="btn" href="latest.json" '
        f'title="JSON API for scripts" data-i18n="card_json">{esc(i18n_ru("card_json"))}</a>'
    )

    body = (
        page_hero("portal_title", "portal_lead", meta_html)
        + f"""
<div class="page-content">
  <div class="card-grid">
    {card("card_map_title", "card_map_desc", map_href, target=map_target)}
    {card("card_discovery_title", "card_discovery_desc", _page_href(deploy, "discovery"))}
    {card("card_atlas_title", "card_atlas_desc", _page_href(deploy, "atlas"))}
    {card("card_cohorts_title", "card_cohorts_desc", _page_href(deploy, "cohorts"))}
    {card("card_qc_title", "card_qc_desc", _page_href(deploy, "qc"), primary=False, extra=json_extra)}
    <div class="card">
      {i18n_el("card_update_title", tag="h2")}
      {i18n_el("card_update_desc", tag="p")}
      <p class="muted"><code>python run_discovery.py scan</code></p>
    </div>
  </div>
  <p class="note muted" style="margin-top:1rem">
    <strong>Deploy:</strong> корень <code>TMT/index.html</code> — интерактивная карта органов
    (<code>?organ=</code>); портал Discovery — только <code>discovery/</code>, не заменяет корень.
  </p>
</div>"""
    )

    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        page_wrap(active="home", body=body, title="Portal", deploy=deploy),
        encoding="utf-8",
    )
    return out
