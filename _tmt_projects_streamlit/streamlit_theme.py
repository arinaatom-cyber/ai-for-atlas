# -*- coding: utf-8 -*-
"""Streamlit UI theme aligned with arinaatom-cyber.github.io/TMT site."""
from __future__ import annotations

import html as html_module

import streamlit as st

BRAND_TITLE = "Human TMT Proteome Atlas"
BRAND_SUB = "Interactive organ map · catalog · Discovery"


def inject_theme() -> None:
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&display=swap');

        :root {
          --bg: #080c12;
          --card: #151d28;
          --border: #243044;
          --text: #eef2f8;
          --muted: #7d8fa6;
          --accent: #4da3ff;
          --ok: #34d399;
          --warn: #fbbf24;
        }

        .stApp {
          background: var(--bg);
          font-family: "IBM Plex Sans", "Segoe UI", system-ui, sans-serif;
        }

        .block-container {
          padding-top: 1.25rem;
          padding-bottom: 2rem;
          max-width: 1480px;
        }

        /* Hide default header clutter */
        header[data-testid="stHeader"] {
          background: rgba(8, 12, 18, 0.85);
          border-bottom: 1px solid var(--border);
        }

        /* Hero */
        .atlas-hero {
          background: linear-gradient(135deg, #111a26 0%, #0d1219 100%);
          border: 1px solid var(--border);
          border-radius: 14px;
          padding: 1.25rem 1.5rem 1rem;
          margin-bottom: 1rem;
          box-shadow: 0 8px 32px rgba(0,0,0,.35);
        }
        .atlas-hero h1 {
          margin: 0 0 .35rem;
          font-size: 1.65rem;
          font-weight: 600;
          color: var(--text);
          letter-spacing: -0.02em;
        }
        .atlas-hero p {
          margin: 0;
          color: var(--muted);
          font-size: .95rem;
        }

        /* KPI grid */
        .kpi-grid {
          display: grid;
          grid-template-columns: repeat(5, minmax(0, 1fr));
          gap: .65rem;
          margin-bottom: 1rem;
        }
        @media (max-width: 1100px) {
          .kpi-grid { grid-template-columns: repeat(3, minmax(0, 1fr)); }
        }
        @media (max-width: 700px) {
          .kpi-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
        }
        .kpi-card {
          background: var(--card);
          border: 1px solid var(--border);
          border-radius: 10px;
          padding: .75rem .9rem;
          text-align: center;
        }
        .kpi-value {
          display: block;
          font-size: 1.35rem;
          font-weight: 600;
          color: var(--accent);
          line-height: 1.2;
        }
        .kpi-label {
          display: block;
          font-size: .78rem;
          color: var(--muted);
          margin-top: .2rem;
          text-transform: uppercase;
          letter-spacing: .04em;
        }

        /* Tabs */
        .stTabs [data-baseweb="tab-list"] {
          gap: 6px;
          background: transparent;
          border-bottom: 1px solid var(--border);
          padding-bottom: 2px;
        }
        .stTabs [data-baseweb="tab"] {
          background: var(--card);
          border: 1px solid var(--border);
          border-radius: 8px 8px 0 0;
          color: var(--muted);
          padding: .45rem 1rem;
          font-weight: 500;
        }
        .stTabs [aria-selected="true"] {
          background: #1a2433 !important;
          color: var(--text) !important;
          border-color: var(--accent) !important;
        }

        /* Sidebar */
        section[data-testid="stSidebar"] {
          background: #0f141c;
          border-right: 1px solid var(--border);
        }
        section[data-testid="stSidebar"] .block-container {
          padding-top: 1rem;
        }
        .sidebar-section {
          font-size: .72rem;
          text-transform: uppercase;
          letter-spacing: .08em;
          color: var(--muted);
          margin: 1rem 0 .35rem;
          font-weight: 600;
        }

        /* Map panel — seamless iframe */
        .map-panel {
          background: var(--card);
          border: 1px solid var(--border);
          border-radius: 14px;
          padding: .5rem .75rem .25rem;
          margin-bottom: .75rem;
          overflow: hidden;
        }
        .map-panel iframe {
          border: none !important;
          background: #080c12 !important;
        }

        /* Status pills */
        .status-pill {
          display: inline-flex;
          align-items: center;
          gap: .5rem;
          padding: .55rem 1rem;
          border-radius: 999px;
          font-size: .9rem;
          font-weight: 500;
          margin: .5rem 0 1rem;
        }
        .status-pill.ok {
          background: rgba(52, 211, 153, 0.12);
          border: 1px solid rgba(52, 211, 153, 0.35);
          color: #6ee7b7;
        }
        .status-pill.hint {
          background: rgba(77, 163, 255, 0.1);
          border: 1px solid rgba(77, 163, 255, 0.3);
          color: #93c5fd;
        }

        /* Section titles */
        .section-title {
          font-size: 1.1rem;
          font-weight: 600;
          color: var(--text);
          margin: .25rem 0 .75rem;
        }

        /* Metrics override (stats tab fallback) */
        div[data-testid="stMetric"] {
          background: var(--card);
          border: 1px solid var(--border);
          border-radius: 10px;
          padding: .5rem .75rem;
        }
        div[data-testid="stMetric"] label {
          color: var(--muted) !important;
        }
        div[data-testid="stMetric"] [data-testid="stMetricValue"] {
          color: var(--accent) !important;
        }

        /* Dataframe */
        div[data-testid="stDataFrame"] {
          border: 1px solid var(--border);
          border-radius: 10px;
          overflow: hidden;
        }

        /* Expander */
        details[data-testid="stExpander"] {
          background: var(--card);
          border: 1px solid var(--border);
          border-radius: 8px;
        }

        /* Streamlit component / iframe — full width, tall map */
        iframe {
          border: none !important;
          background: #080c12 !important;
          width: 100% !important;
          min-width: 100% !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"] iframe,
        div[data-testid="stIFrame"] {
          width: 100% !important;
          min-width: 100% !important;
        }
        div[data-testid="stIFrame"] {
          min-height: 1200px;
        }
        div[data-testid="stIFrame"] > iframe {
          min-height: 1200px !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_hero() -> None:
    st.markdown(
        f"""
        <div class="atlas-hero">
          <h1>{BRAND_TITLE}</h1>
          <p>{BRAND_SUB} · Data on <a href="https://github.com/arinaatom-cyber/tmt-projects" target="_blank">GitHub</a></p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_kpi_row(
    *,
    projects: int | str,
    samples: str,
    proteins: str,
    healthy: str,
    in_repo: int | str,
) -> None:
    st.markdown(
        f"""
        <div class="kpi-grid">
          <div class="kpi-card"><span class="kpi-value">{projects}</span><span class="kpi-label">Projects</span></div>
          <div class="kpi-card"><span class="kpi-value">{samples}</span><span class="kpi-label">Samples</span></div>
          <div class="kpi-card"><span class="kpi-value">{proteins}</span><span class="kpi-label">Unique proteins</span></div>
          <div class="kpi-card"><span class="kpi-value">{healthy}</span><span class="kpi-label">Healthy samples</span></div>
          <div class="kpi-card"><span class="kpi-value">{in_repo}</span><span class="kpi-label">In repo</span></div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_organ_status(organ: str | None, stats: dict, df) -> None:
    from organ_atlas import organ_stats

    if organ:
        s = stats.get(organ, organ_stats(df, organ))
        label = html_module.escape(organ.replace("_", " "))
        pan = f" · {s['nPan']} pan-organ" if s.get("nPan") else ""
        st.markdown(
            f'<div class="status-pill ok"><span>●</span> <b>{label}</b> — '
            f"{s['n']} projects · {s['nC']} cancer · {s['nN']} normal{pan}</div>",
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<div class="status-pill hint">Click an organ on the map or pick from the sidebar</div>',
            unsafe_allow_html=True,
        )
