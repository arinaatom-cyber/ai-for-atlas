"""AI keyword search landing — launches Streamlit app (Pf-HaploAtlas-style workflow)."""
from __future__ import annotations

import json
from pathlib import Path

from atlas_agent.viz.i18n_defaults import BRAND_NAME
from atlas_agent.viz.site_components import esc, i18n_el, meta_time, page_hero
from atlas_agent.viz.site_theme import page_wrap
from atlas_agent.viz.portal_index import STREAMLIT_ATLAS_URL


def generate_ai_search_html(report: dict, out_path: str | Path, *, deploy: str = "docs_site") -> Path:
    profile = report.get("catalog_profile") or {}
    gen = report.get("generated_at") or ""
    keywords = list(profile.get("search_keywords") or profile.get("top_organs") or [])[:12]
    kw_json = json.dumps(keywords, ensure_ascii=False)

    streamlit_url = STREAMLIT_ATLAS_URL.rstrip("/")

    meta = meta_time(gen) + '<span class="meta-pill badge badge-ok" data-i18n="ai_badge_live">Live app</span>'

    body = (
        page_hero("ai_title", "ai_lead", meta)
        + f"""
<div class="page-content">
  <div class="how-to-panel">
    {i18n_el("ai_how_title", tag="h3")}
    <ol class="how-to-steps">
      <li data-i18n="ai_step1"></li>
      <li data-i18n="ai_step2"></li>
      <li data-i18n="ai_step3"></li>
      <li data-i18n="ai_step4"></li>
    </ol>
  </div>

  <div class="card ai-launch-card">
    {i18n_el("ai_launch_title", tag="h2")}
    {i18n_el("ai_launch_desc", tag="p")}
    <div class="btn-row">
      <a class="btn btn-primary btn-lg" href="{esc(streamlit_url)}" target="_blank" rel="noopener" data-i18n="ai_launch_btn"></a>
      <a class="btn" href="discovery.html" data-i18n="ai_view_discovery"></a>
    </div>
  </div>

  <div class="section-block">
    {i18n_el("ai_keywords_title", tag="h3")}
    <p class="muted" data-i18n="ai_keywords_desc"></p>
    <div class="tag-list" id="ai-kw-tags"></div>
    <pre class="code-block" id="ai-kw-pre"></pre>
  </div>

  <div class="embed-shell embed-shell-compact">
    <iframe
      class="embed-frame embed-frame-tall"
      src="{esc(streamlit_url)}"
      title="AI keyword search"
      loading="lazy"
      referrerpolicy="no-referrer-when-downgrade"
    ></iframe>
    <p class="muted embed-fallback-note" data-i18n="ai_iframe_fallback"></p>
  </div>
</div>
<script>
(function () {{
  const kws = {kw_json};
  const pre = document.getElementById("ai-kw-pre");
  const tags = document.getElementById("ai-kw-tags");
  if (pre && kws.length) pre.textContent = kws.join("\\n");
  if (tags && kws.length) {{
    tags.innerHTML = kws.map(function (k) {{
      return '<span class="tag">' + k.replace(/</g, "&lt;") + '</span>';
    }}).join("");
  }}
}})();
</script>"""
    )

    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        page_wrap(active="ai", body=body, title=f"{BRAND_NAME} — AI search", deploy=deploy),
        encoding="utf-8",
    )
    return out
