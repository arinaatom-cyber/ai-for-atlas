#!/usr/bin/env python3

"""Atlas Discovery UI — http://localhost:8501"""

from __future__ import annotations



import json

from datetime import datetime

from pathlib import Path



import pandas as pd

import streamlit as st



ROOT = Path(__file__).parent

HTML_REPORT = ROOT / "reports" / "discovery_index.html"
SITE_REPORT = ROOT / "docs" / "site" / "discovery.html"
QC_REPORT = ROOT / "reports" / "discovery_qc_report.html"
SITE_QC = ROOT / "docs" / "site" / "qc.html"



st.set_page_config(page_title="Atlas Discovery", page_icon="🔬", layout="wide")



st.markdown(

    """<style>

    .main-header { font-size:2rem; font-weight:700;

      background:linear-gradient(90deg,#6cb6ff,#3dd68c);

      -webkit-background-clip:text; -webkit-text-fill-color:transparent; }

    .metric-card { background:#1a2332; border:1px solid #2a3548; border-radius:12px; padding:1rem; }

    .metric-val { font-size:1.6rem; font-weight:700; color:#6cb6ff; }

    .metric-lbl { color:#8b9cb3; font-size:.85rem; }

    </style>""",

    unsafe_allow_html=True,

)





def source_label(item: dict) -> str:

    acc = (item.get("project_accession") or item.get("accession") or "").upper()

    if acc.startswith("PDC"):

        return "PDC"

    if acc.startswith("PXD"):

        return "PRIDE"

    return item.get("source") or "?"





def to_df(items: list[dict]) -> pd.DataFrame:

    rows = []

    for p in items:

        acc = p.get("project_accession") or p.get("accession", "")

        sim = (p.get("similar_in_catalog") or [{}])[0]

        sig = p.get("material_signals") or {}

        rows.append({

            "ID": acc,

            "Название": (p.get("title") or "")[:120],

            "QC": p.get("qc_status", ""),

            "Plex": p.get("tmt_label") or p.get("inferred_plex", ""),

            "Материал +": ", ".join(sig.get("included") or [])[:50],

            "Материал −": ", ".join(sig.get("excluded") or [])[:50],

            "Причина": "; ".join((p.get("qc_reasons") or p.get("filter_reasons") or [])[:2]),

            "Похож на": sim.get("project_id", ""),

            "Источник": source_label(p),

        })

    return pd.DataFrame(rows)





@st.cache_data(ttl=120)

def load_catalog():

    from atlas_agent.config import load_config

    from atlas_agent.discovery.agent import load_catalog_readonly

    from atlas_agent.discovery.catalog_profile import build_catalog_profile



    cfg = load_config()

    df = load_catalog_readonly((cfg.get("sheet") or {}).get("projects_csv"))

    return df, build_catalog_profile(df), cfg





def load_report():

    from atlas_agent.discovery.history import load_latest

    return load_latest(ROOT)





def run_search(cfg, df, year_from):

    from atlas_agent.discovery.agent import run_discovery_scan

    sc = dict(cfg.get("discovery") or {})

    sc["year_from"] = year_from

    cfg = dict(cfg)

    cfg["discovery"] = sc

    return run_discovery_scan(df, cfg, root=ROOT)





st.markdown('<p class="main-header">Atlas Discovery + QC</p>', unsafe_allow_html=True)

st.caption("Homo sapiens · TMT 10/11/12/16 · QC: candidate / manual-check / rejected · projects.csv не меняется")



df, profile, cfg = load_catalog()



with st.sidebar:

    st.header("Скан")

    year = st.slider("Год с", 2020, 2026, int((cfg.get("discovery") or {}).get("year_from") or 2024))

    if st.button("Обновить с диска", use_container_width=True):

        st.session_state["report"] = load_report()

        st.rerun()

    if st.button("Новый поиск", type="primary", use_container_width=True):

        st.session_state["do_scan"] = True

    st.metric("В каталоге", profile.get("n_unique_ids", 0))



if "report" not in st.session_state:

    st.session_state["report"] = load_report()



if st.session_state.pop("do_scan", False):

    with st.spinner("Поиск + QC…"):

        st.session_state["report"] = run_search(cfg, df, year)



report = st.session_state.get("report")

if not report:

    st.warning("Нет скана. Запустите поиск или `python run_discovery.py scan`")

    st.stop()



s = report.get("summary") or {}

cand = report.get("candidates") or report.get("new_projects") or []

manual = report.get("manual_check") or []

rejected = report.get("rejected_material") or []



c1, c2, c3, c4, c5 = st.columns(5)

for col, n, lbl in [

    (c1, len(cand), "Candidate"),

    (c2, len(manual), "Manual check"),

    (c3, len(rejected), "Rejected"),

    (c4, s.get("filtered_out", 0), "Technical filt."),

    (c5, s.get("catalog_unique_ids", 0), "В каталоге"),

]:

    col.markdown(

        f'<div class="metric-card"><div class="metric-val">{n}</div><div class="metric-lbl">{lbl}</div></div>',

        unsafe_allow_html=True,

    )



col1, col2 = st.columns(2)

site_html = SITE_REPORT if SITE_REPORT.is_file() else HTML_REPORT
with col1:
    if site_html.is_file():
        st.link_button("Сайт: только новые", site_html.resolve().as_uri(), use_container_width=True)
with col2:
    qc_path = SITE_QC if SITE_QC.is_file() else Path(report.get("report_qc_html") or QC_REPORT)
    if qc_path.is_file():
        st.link_button("QC Report", qc_path.resolve().as_uri(), use_container_width=True)



tab1, tab2, tab3 = st.tabs([

    f"Candidate ({len(cand)})",

    f"Manual check ({len(manual)})",

    f"Rejected ({len(rejected)})",

])



for tab, data in [(tab1, cand), (tab2, manual), (tab3, rejected)]:

    with tab:

        q = st.text_input("Поиск", key=f"q_{id(data)}", placeholder="PXD, PDC, tumor, organoid…")

        items = data

        if q:

            ql = q.lower()

            items = [

                p for p in data

                if ql in " ".join(

                    str(p.get(k, "")) for k in ("project_accession", "accession", "title", "qc_reasons")

                ).lower()

            ]

        st.caption(f"Показано: {len(items)}")

        if items:

            st.dataframe(to_df(items), use_container_width=True, hide_index=True, height=500)

        else:

            st.info("Пусто")



with st.expander("Скачать JSON"):

    st.download_button(

        "JSON",

        json.dumps(report, ensure_ascii=False, indent=2),

        file_name=f"discovery_{datetime.now():%Y%m%d}.json",

    )


