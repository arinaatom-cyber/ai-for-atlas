"""Shared HTML shell, nav, and asset deployment for English Discovery site."""
from __future__ import annotations

import html
import shutil
from pathlib import Path

from atlas_agent.viz.i18n_defaults import en as i18n_default

_ASSETS_DIR = Path(__file__).resolve().parent / "site_assets"

GITHUB_TMT = "https://github.com/arinaatom-cyber/TMT"
GITHUB_PROJECTS = "https://github.com/arinaatom-cyber/tmt-projects/tree/main/Projects"
LIVE_TMT = "https://arinaatom-cyber.github.io/TMT/discovery/discovery.html"
LIVE_MAP = "https://arinaatom-cyber.github.io/TMT/"

DEPLOY_DOCS_PORTAL = "docs_portal"
DEPLOY_DOCS_SITE = "docs_site"
DEPLOY_TMT = "tmt_discovery"


def _esc(s: object) -> str:
    return html.escape(str(s or ""))


def write_site_assets(site_dir: Path) -> Path:
    assets = site_dir / "assets"
    assets.mkdir(parents=True, exist_ok=True)
    for name in ("theme.css", "i18n.js"):
        shutil.copy2(_ASSETS_DIR / name, assets / name)
    return assets


def _lang_toggle() -> str:
    return ""


def _nav_paths(deploy: str) -> tuple[str, str, str, str, str, str | None]:
    """home, atlas, discovery, cohorts, qc, optional map_href."""
    if deploy == DEPLOY_DOCS_PORTAL:
        return (
            "index.html",
            "site/atlas.html",
            "site/discovery.html",
            "site/cohorts.html",
            "site/qc.html",
            None,
        )
    if deploy == DEPLOY_TMT:
        return (
            "index.html",
            "atlas.html",
            "discovery.html",
            "cohorts.html",
            "qc.html",
            "../index.html",
        )
    return (
        "../index.html",
        "atlas.html",
        "discovery.html",
        "cohorts.html",
        "qc.html",
        None,
    )


def assets_prefix_for(deploy: str) -> str:
    return "site/assets" if deploy == DEPLOY_DOCS_PORTAL else "assets"


def _i18n_el(key: str, *, tag: str = "span", href: str = "", cls: str = "") -> str:
    text = _esc(i18n_default(key))
    if tag == "a":
        return f'<a href="{_esc(href)}" class="{cls}" data-i18n="{key}">{text}</a>'
    extra = f' class="{cls}"' if cls else ""
    return f"<{tag}{extra} data-i18n=\"{key}\">{text}</{tag}>"


def site_head(*, deploy: str = DEPLOY_DOCS_SITE, title: str = "Atlas Discovery") -> str:
    prefix = assets_prefix_for(deploy)
    css = f"{prefix}/theme.css"
    js = f"{prefix}/i18n.js"
    return f"""<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <meta name="description" content="{_esc(i18n_default('portal_lead')[:160])}"/>
  <title>{_esc(title)}</title>
  <link rel="stylesheet" href="{css}"/>
  <script src="{js}" defer></script>
</head>"""


def site_header_bar(*, active: str, deploy: str = DEPLOY_DOCS_SITE) -> str:
    home, atlas, disc, cohorts, qc, map_href = _nav_paths(deploy)

    def nav(href: str, key: str, page: str) -> str:
        cls = "active" if active == page else ""
        return _i18n_el(key, tag="a", href=href, cls=cls)

    map_link = (
        f'\n      {_i18n_el("nav_map", tag="a", href=map_href, cls="nav-map")}'
        if map_href
        else ""
    )

    return f"""<header class="site-header">
  <div class="site-header-inner">
    <div class="brand">
      {_i18n_el("brand_title", tag="span", cls="brand-title")}
      {_i18n_el("brand_sub", tag="span", cls="brand-sub")}
    </div>
    <nav class="site-nav">
      {nav(home, "nav_home", "home")}
      {nav(atlas, "nav_atlas", "atlas")}
      {nav(disc, "nav_discovery", "discovery")}
      {nav(cohorts, "nav_cohorts", "cohorts")}
      {nav(qc, "nav_qc", "qc")}{map_link}
    </nav>
    {_lang_toggle()}
  </div>
</header>"""


def site_footer(*, deploy: str = DEPLOY_DOCS_SITE) -> str:
    live = LIVE_MAP if deploy == DEPLOY_TMT else LIVE_TMT
    return f"""<footer class="footer">
  <p data-i18n="footer_policy">{_esc(i18n_default("footer_policy"))}</p>
  <p>
    <a href="{GITHUB_TMT}" target="_blank" rel="noopener" data-i18n="footer_github">{_esc(i18n_default("footer_github"))}</a> ·
    <a href="{GITHUB_PROJECTS}" target="_blank" rel="noopener" data-i18n="footer_projects">{_esc(i18n_default("footer_projects"))}</a> ·
    <a href="{live}" target="_blank" rel="noopener" data-i18n="footer_live">{_esc(i18n_default("footer_live"))}</a>
  </p>
</footer>"""


def page_wrap(
    *,
    active: str,
    body: str,
    title: str,
    deploy: str = DEPLOY_DOCS_SITE,
) -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
{site_head(deploy=deploy, title=title)}
<body>
{site_header_bar(active=active, deploy=deploy)}
<main class="site-main">
{body}
</main>
{site_footer(deploy=deploy)}
</body>
</html>"""
