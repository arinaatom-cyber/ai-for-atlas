from __future__ import annotations

import html
import shutil
from pathlib import Path

from atlas_agent.viz.i18n_defaults import BRAND_NAME, en as i18n_default

_ASSETS_DIR = Path(__file__).resolve().parent / "site_assets"

GITHUB_CODE = "https://github.com/arinaatom-cyber/ai-for-atlas"
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
    for name in ("theme.css", "i18n.js", "site_ui.js"):
        shutil.copy2(_ASSETS_DIR / name, assets / name)
    return assets


def _header_controls() -> str:
    return """<div class="header-controls">
      <div class="theme-toggle" aria-label="Theme">
        <button type="button" data-theme="light" title="Light">☀</button>
        <button type="button" data-theme="dark" title="Dark">☾</button>
        <button type="button" data-theme="auto" class="active" title="System">◐</button>
      </div>
      <div class="lang-toggle" aria-label="Language">
        <button type="button" data-lang="ru" class="active">RU</button>
        <button type="button" data-lang="en">EN</button>
      </div>
    </div>"""


def _nav_paths(deploy: str) -> dict[str, str]:
    if deploy == DEPLOY_DOCS_PORTAL:
        return {
            "discovery": "site/discovery.html",
            "qc": "site/qc.html",
        }
    if deploy == DEPLOY_TMT:
        return {
            "discovery": "discovery.html",
            "qc": "qc.html",
        }
    return {
        "discovery": "discovery.html",
        "qc": "qc.html",
    }


def assets_prefix_for(deploy: str) -> str:
    return "site/assets" if deploy == DEPLOY_DOCS_PORTAL else "assets"


def _i18n_el(key: str, *, tag: str = "span", href: str = "", cls: str = "") -> str:
    text = _esc(i18n_default(key))
    if tag == "a":
        return f'<a href="{_esc(href)}" class="{cls}" data-i18n="{key}">{text}</a>'
    extra = f' class="{cls}"' if cls else ""
    return f"<{tag}{extra} data-i18n=\"{key}\">{text}</{tag}>"


def site_head(*, deploy: str = DEPLOY_DOCS_SITE, title: str | None = None) -> str:
    page_title = title or BRAND_NAME
    prefix = assets_prefix_for(deploy)
    css = f"{prefix}/theme.css"
    js = f"{prefix}/i18n.js"
    ui = f"{prefix}/site_ui.js"
    return f"""<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <meta name="description" content="{_esc(i18n_default('portal_lead')[:160])}"/>
  <title>{_esc(page_title)}</title>
  <script>(function(){{try{{var l=localStorage.getItem('atlas_site_lang')||'ru';document.documentElement.lang=l;var t=localStorage.getItem('atlas_site_theme')||'auto';if(t!=='auto')document.documentElement.dataset.theme=t;}}catch(e){{}}}})();</script>
  <link rel="stylesheet" href="{css}"/>
  <script src="{js}" defer></script>
  <script src="{ui}" defer></script>
</head>"""


def site_header_bar(*, active: str, deploy: str = DEPLOY_DOCS_SITE) -> str:
    paths = _nav_paths(deploy)

    def nav(href: str, key: str, page: str) -> str:
        cls = "active" if active == page else ""
        return _i18n_el(key, tag="a", href=href, cls=cls)

    nav_html = "".join(
        nav(paths[page], key, page)
        for page, key in (
            ("discovery", "nav_discovery"),
            ("qc", "nav_qc"),
        )
        if paths.get(page)
    )

    discovery_href = paths.get("discovery") or "discovery.html"

    return f"""<header class="site-header">
  <div class="site-header-inner">
    <div class="brand">
      <a href="{_esc(discovery_href)}" class="brand-link">
        {_i18n_el("brand_title", tag="span", cls="brand-title")}
      </a>
    </div>
    <nav class="site-nav" aria-label="Main">{nav_html}</nav>
    {_header_controls()}
  </div>
</header>"""


def site_footer(*, deploy: str = DEPLOY_DOCS_SITE) -> str:
    live = LIVE_MAP if deploy == DEPLOY_TMT else LIVE_TMT
    return f"""<footer class="footer">
  <p data-i18n="footer_policy">{_esc(i18n_default("footer_policy"))}</p>
  <p class="footer-opensource">
    <a href="{GITHUB_CODE}" target="_blank" rel="noopener" data-i18n="footer_opensource">{_esc(i18n_default("footer_opensource"))}</a>
  </p>
  <p>
    <a href="{GITHUB_CODE}" target="_blank" rel="noopener" data-i18n="footer_code">{_esc(i18n_default("footer_code"))}</a> ·
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
<html lang="ru">
{site_head(deploy=deploy, title=title)}
<body>
{site_header_bar(active=active, deploy=deploy)}
<main class="site-main">
{body}
</main>
{site_footer(deploy=deploy)}
</body>
</html>"""
