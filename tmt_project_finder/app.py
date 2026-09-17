#!/usr/bin/env python3
"""TMT Project Finder — Streamlit UI."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.pipeline import run_pipeline
from src.save_outputs import _record_to_row
from src.utils import load_config, resolve_path

st.set_page_config(page_title="TMT Project Finder", page_icon="🔬", layout="wide")

st.markdown(
    """<style>
    .metric { background:#1a2332; border:1px solid #2a3548; border-radius:10px;
      padding:14px; text-align:center; }
    .metric b { font-size:1.5rem; color:#6cb6ff; display:block; }
    .metric span { color:#8b9cb3; font-size:.85rem; }
    </style>""",
    unsafe_allow_html=True,
)

TAB_NAMES = [
    "Dashboard",
    "Search",
    "Found Projects",
    "High Priority",
    "Medium Priority",
    "Manual Check",
    "Rejected",
    "Duplicates",
    "Previously Removed",
    "Export",
]

CLASS_MAP = {
    "High Priority": "high_priority_check",
    "Medium Priority": "medium_priority_check",
    "Manual Check": "manual_check",
    "Rejected": "reject",
    "Duplicates": "duplicate",
    "Previously Removed": "rejected_previously_removed",
}


@st.cache_data
def _load_excel(path: str) -> pd.DataFrame:
    p = resolve_path(path)
    if not p.is_file():
        return pd.DataFrame()
    return pd.read_excel(p, engine="openpyxl")


def _load_log() -> dict:
    cfg = load_config()
    log_path = resolve_path(cfg.get("outputs", {}).get("log", "outputs/search_log.json"))
    if log_path.is_file():
        return json.loads(log_path.read_text(encoding="utf-8"))
    return {}


def _counts() -> dict:
    if "pipeline_result" in st.session_state:
        c = st.session_state["pipeline_result"].get("counts", {})
        return {
            "total": st.session_state["pipeline_result"].get("total", 0),
            "high_priority_check": c.get("high_priority_check", 0),
            "medium_priority_check": c.get("medium_priority_check", 0),
            "manual_check": c.get("manual_check", 0),
            "reject": c.get("reject", 0),
            "duplicate": c.get("duplicate", 0),
            "rejected_previously_removed": c.get("rejected_previously_removed", 0),
        }
    log = _load_log()
    c = log.get("counts", {})
    return {
        "total": log.get("total_found", 0),
        "high_priority_check": c.get("high_priority", 0),
        "medium_priority_check": c.get("medium_priority", 0),
        "manual_check": c.get("manual_check", 0),
        "reject": c.get("rejected", 0),
        "duplicate": c.get("duplicates", 0),
        "rejected_previously_removed": c.get("previously_removed", 0),
    }


def _show_metrics(counts: dict):
    cols = st.columns(7)
    for col, (key, lbl) in zip(cols, [
        ("total", "Total found"),
        ("high_priority_check", "High priority"),
        ("medium_priority_check", "Medium priority"),
        ("manual_check", "Manual check"),
        ("reject", "Rejected"),
        ("duplicate", "Duplicates"),
        ("rejected_previously_removed", "Prev. removed"),
    ]):
        col.markdown(
            f'<div class="metric"><b>{counts.get(key, 0)}</b><span>{lbl}</span></div>',
            unsafe_allow_html=True,
        )


cfg = load_config()
outputs = cfg.get("outputs", {})
res = st.session_state.get("pipeline_result")
file_map = {
    "Found Projects": outputs.get("found", "outputs/found_projects.xlsx"),
    "High Priority": outputs.get("high", "outputs/high_priority.xlsx"),
    "Medium Priority": outputs.get("medium", "outputs/medium_priority.xlsx"),
    "Manual Check": outputs.get("manual", "outputs/manual_check.xlsx"),
    "Rejected": outputs.get("rejected", "outputs/rejected.xlsx"),
    "Duplicates": outputs.get("duplicates", "outputs/duplicates.xlsx"),
    "Previously Removed": outputs.get("deleted", "outputs/previously_removed.xlsx"),
}

st.title("TMT Project Finder")
st.caption("Human TMT · PRIDE · PDC · MassIVE · iProX · OmicsDI · PubMed · Europe PMC")
st.info(
    "База: `project of Proteomics.xlsx` — **TMT ATLAS** (в атласе) · **CPTAC** (просмотрено) · "
    "**удалено из general** (отклонённые, красные). Read-only."
)

tabs = st.tabs(TAB_NAMES)

# Dashboard
with tabs[0]:
    _show_metrics(_counts())
    log = _load_log()
    if log:
        st.subheader("search_log.json")
        st.json(log)
    report_p = resolve_path(outputs.get("report", "outputs/report.md"))
    if report_p.is_file():
        st.subheader("report.md")
        st.markdown(report_p.read_text(encoding="utf-8"))

# Search
with tabs[1]:
    st.write("Sources:", ", ".join(k for k, v in (cfg.get("sources") or {}).items() if v))
    c1, c2 = st.columns(2)
    with c1:
        if st.button("Run Search", type="primary", use_container_width=True):
            with st.spinner("Searching…"):
                st.session_state["pipeline_result"] = run_pipeline(cfg)
            st.success(f"Found {st.session_state['pipeline_result']['total']} records")
            st.rerun()
    with c2:
        if st.button("Generate Report", use_container_width=True):
            rp = resolve_path(outputs.get("report", "outputs/report.md"))
            st.success(str(rp) if rp.is_file() else "Run search first")
    res = st.session_state.get("pipeline_result")
    if res:
        if res.get("errors"):
            st.error("\n".join(res["errors"]))
        if res.get("warnings"):
            st.warning("\n".join(res["warnings"][:8]))

# Data tabs
for tab_name in [
    "Found Projects", "High Priority", "Medium Priority",
    "Manual Check", "Rejected", "Duplicates", "Previously Removed",
]:
    with tabs[TAB_NAMES.index(tab_name)]:
        df = _load_excel(file_map[tab_name])
        cls = CLASS_MAP.get(tab_name)
        if df.empty and res and cls:
            recs = [r for r in res["records"] if r.get("classification") == cls]
            if recs:
                df = pd.DataFrame([_record_to_row(r) for r in recs])
        elif df.empty and res and tab_name == "Found Projects":
            df = pd.DataFrame([_record_to_row(r) for r in res["records"]])
        q = st.text_input("Filter", key=f"f_{tab_name}")
        if not df.empty and q:
            df = df[df.astype(str).apply(lambda row: q.lower() in " ".join(row).lower(), axis=1)]
        st.caption(f"{len(df)} rows")
        st.dataframe(df if not df.empty else pd.DataFrame(), use_container_width=True, hide_index=True, height=400)

# Export
with tabs[9]:
    st.subheader("Export Excel")
    for label, fpath in file_map.items():
        p = resolve_path(fpath)
        if p.is_file() and p.stat().st_size > 100:
            st.download_button(
                f"Download {label}",
                p.read_bytes(),
                file_name=p.name,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key=f"dl_{label}",
            )
    if st.button("Export Excel"):
        st.info("Используйте кнопки Download выше.")
