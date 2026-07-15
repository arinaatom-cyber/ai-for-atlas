"""Cohorts page — redirects to unified Discovery table."""
from __future__ import annotations

from pathlib import Path

from atlas_agent.viz.site_theme import page_wrap


def generate_cohorts_html(report: dict, out_path: str | Path, *, deploy: str = "docs_site") -> Path:
    """Cohorts merged into discovery.html — this page only redirects."""
    del report
    prefix = "" if deploy == "tmt_discovery" else ""
    target = f"{prefix}discovery.html#discovery"
    body = f"""<div class="page-content page-content-wide">
  <p class="note">Large cohorts are now in the <strong>single Discovery table</strong> (filter: Cohorts).</p>
  <p><a href="{target}" class="btn-primary">Open Discovery table</a></p>
  <script>location.replace("{target}");</script>
</div>"""
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page_wrap(active="cohorts", body=body, title="Cohorts", deploy=deploy), encoding="utf-8")
    return out
