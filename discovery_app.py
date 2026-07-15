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
GITHUB_SITE = "https://arinaatom-cyber.github.io/ai-for-atlas/site/discovery.html"

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


def pubs_to_df(items: list[dict]) -> pd.DataFrame:
    rows = []
    for p in items:
        ai = p.get("abstract_ai") or {}
        sim = (p.get("similar_in_catalog") or [{}])[0]
        accs = p.get("accessions_mentioned") or p.get("pxd_mentioned") or []
        rows.append({
            "PMID": p.get("pmid", ""),
            "Atlas fit": ai.get("atlas_fit") or p.get("atlas_fit") or "",
            "Score": ai.get("atlas_fit_score", ""),
            "Название": (p.get("title") or "")[:100],
            "TMT": ai.get("tmt", ""),
            "Материал": ai.get("material", ""),
            "PXD/PDC": ", ".join(accs[:3]),
            "Похож на": sim.get("project_id", ""),
            "ИИ (RU)": (ai.get("summary_ru") or "")[:120],
            "Reader": p.get("abstract_reader") or ai.get("reader", ""),
        })
    return pd.DataFrame(rows)


def repo_search_to_df(items: list[dict]) -> pd.DataFrame:
    rows = []
    for p in items:
        acc = p.get("accession") or p.get("project_accession") or ""
        sim = (p.get("similar_in_catalog") or [{}])[0]
        rows.append({
            "ID": acc,
            "Название": (p.get("title") or p.get("projectTitle") or "")[:100],
            "Источник": source_label(p),
            "Plex": p.get("tmt_label") or p.get("inferred_plex") or "",
            "Похож на": sim.get("project_id", ""),
            "Score": sim.get("score", ""),
        })
    return pd.DataFrame(rows)


@st.cache_data(ttl=120)
def load_catalog():
    from atlas_agent.config import load_config
    from atlas_agent.discovery.agent import load_catalog_readonly
    from atlas_agent.discovery.catalog_profile import build_catalog_profile

    cfg = load_config()
    df = load_catalog_readonly(cfg)
    profile = build_catalog_profile(df)
    profile["n_atlas_projects"] = profile["n_unique_ids"]
    return df, profile, cfg


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


def run_ai_keyword_search(cfg, df, keywords, extra_query, year_from, year_to):
    from atlas_agent.discovery.keyword_search import run_keyword_ai_search

    return run_keyword_ai_search(
        df,
        cfg,
        keywords=keywords,
        extra_query=extra_query,
        year_from=year_from,
        year_to=year_to,
    )


st.markdown('<p class="main-header">Atlas Discovery + QC</p>', unsafe_allow_html=True)
st.caption("Каталог: TMT ATLAS · Homo sapiens · TMT 10/11/12/16 · GitHub: ai-for-atlas")

df, profile, cfg = load_catalog()
disc = cfg.get("discovery") or {}

with st.sidebar:
    st.header("Скан")
    year = st.slider("Год с", 2020, 2026, int(disc.get("year_from") or 2024))
    if st.button("Обновить с диска", use_container_width=True):
        st.session_state["report"] = load_report()
        st.rerun()
    if st.button("Полный scan", type="primary", use_container_width=True):
        st.session_state["do_scan"] = True
    st.metric("TMT ATLAS", profile.get("n_unique_ids", 0))
    sh = (cfg.get("sheet") or {}).get("projects_sheet", "TMT ATLAS")
    st.caption(f"{sh} · read-only")
    st.divider()
    st.markdown(f"[Сайт на GitHub]({GITHUB_SITE})")

if "report" not in st.session_state:
    st.session_state["report"] = load_report()

if st.session_state.pop("do_scan", False):
    with st.spinner("Полный поиск + QC…"):
        st.session_state["report"] = run_search(cfg, df, year)

tab_qc, tab_ai, tab_site = st.tabs(["QC кандидаты", "ИИ поиск (ключевые слова)", "Сайт / GitHub"])

with tab_qc:
    report = st.session_state.get("report")
    if not report:
        st.warning("Нет скана. Нажмите «Полный scan» или `python run_discovery.py scan`")
    else:
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
            (c5, profile.get("n_atlas_projects") or s.get("catalog_unique_ids", 0), "TMT ATLAS"),
        ]:
            col.markdown(
                f'<div class="metric-card"><div class="metric-val">{n}</div>'
                f'<div class="metric-lbl">{lbl}</div></div>',
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

        t1, t2, t3 = st.tabs([
            f"Candidate ({len(cand)})",
            f"Manual check ({len(manual)})",
            f"Rejected ({len(rejected)})",
        ])
        for tab, data in [(t1, cand), (t2, manual), (t3, rejected)]:
            with tab:
                q = st.text_input("Поиск", key=f"q_{id(data)}", placeholder="PXD, PDC, tumor, organoid…")
                items = data
                if q:
                    ql = q.lower()
                    items = [
                        p
                        for p in data
                        if ql
                        in " ".join(
                            str(p.get(k, "")) for k in ("project_accession", "accession", "title", "qc_reasons")
                        ).lower()
                    ]
                st.caption(f"Показано: {len(items)}")
                if items:
                    st.dataframe(to_df(items), use_container_width=True, hide_index=True, height=420)
                else:
                    st.info("Пусто")

        with st.expander("Скачать JSON"):
            st.download_button(
                "JSON",
                json.dumps(report, ensure_ascii=False, indent=2),
                file_name=f"discovery_{datetime.now():%Y%m%d}.json",
            )

with tab_ai:
    from atlas_agent.discovery.keyword_search import default_search_keywords

    default_kw = default_search_keywords(cfg, profile)
    st.markdown("**ИИ-поиск** по ключевым словам из TMT ATLAS и `config.yaml` (PRIDE, PDC, Europe PMC).")

    kw_cols = st.columns([2, 1])
    with kw_cols[0]:
        kw_text = st.text_area(
            "Ключевые слова (по одному в строке или через запятую)",
            value="\n".join(default_kw),
            height=140,
            help="Органы, болезни, TMT, PDC… из каталога + pride_keywords",
        )
    with kw_cols[1]:
        ai_year_from = st.number_input("Год с", 2020, 2026, int(disc.get("year_from") or 2024))
        ai_year_to = st.number_input("Год по", 2020, 2026, int(disc.get("year_to") or 2026))
        extra_q = st.text_input("Доп. запрос Europe PMC", placeholder="gastric cancer TMT adjacent normal")

    keywords = []
    for line in kw_text.replace(",", "\n").splitlines():
        k = line.strip()
        if k and k not in keywords:
            keywords.append(k)

    st.caption(f"Из каталога: {', '.join(profile.get('top_organs') or [])[:5]} · "
               f"{', '.join(profile.get('top_diseases') or [])[:5]}")

    if st.button("Искать с ИИ", type="primary", use_container_width=True):
        with st.spinner("PRIDE + PDC + Europe PMC + ИИ…"):
            st.session_state["ai_search"] = run_ai_keyword_search(
                cfg, df, keywords, extra_q, int(ai_year_from), int(ai_year_to)
            )

    ai_result = st.session_state.get("ai_search")
    if ai_result:
        stats = ai_result.get("source_stats") or {}
        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric("PRIDE", stats.get("pride", 0))
        m2.metric("PDC", stats.get("pdc", 0))
        m3.metric("Статьи", stats.get("publications", 0))
        m4.metric("Новые репо", len(ai_result.get("repository_novel") or []))
        m5.metric("ИИ прочитано", stats.get("llm_read", 0))

        with st.expander("Запрос Europe PMC"):
            st.code(ai_result.get("literature_query") or "")

        sub_repo, sub_pub = st.tabs([
            f"Репозитории ({len(ai_result.get('repository_candidates') or ai_result.get('repository_novel') or [])})",
            f"Статьи / абстракты ({len(ai_result.get('publications') or [])})",
        ])
        with sub_repo:
            repo_items = ai_result.get("repository_candidates") or ai_result.get("repository_novel") or []
            if repo_items:
                st.dataframe(repo_search_to_df(repo_items), use_container_width=True, hide_index=True, height=360)
            else:
                st.info("Новых ID в репозиториях не найдено по этим ключевым словам.")
        with sub_pub:
            pubs = ai_result.get("publications") or []
            fit_filter = st.selectbox("Atlas fit", ["Все", "yes", "maybe", "no"], index=0)
            if fit_filter != "Все":
                pubs = [
                    p
                    for p in pubs
                    if (p.get("abstract_ai") or {}).get("atlas_fit") == fit_filter
                    or p.get("atlas_fit") == fit_filter
                ]
            if pubs:
                st.dataframe(pubs_to_df(pubs), use_container_width=True, hide_index=True, height=360)
            else:
                st.info("Статей не найдено. Измените ключевые слова или год.")

        st.download_button(
            "JSON результатов",
            json.dumps(ai_result, ensure_ascii=False, indent=2, default=str),
            file_name=f"ai_search_{datetime.now():%Y%m%d_%H%M}.json",
        )

with tab_site:
    st.markdown("### Публикация на GitHub Pages")
    st.markdown(f"**Репозиторий:** [arinaatom-cyber/ai-for-atlas](https://github.com/arinaatom-cyber/ai-for-atlas)")
    st.markdown(f"**URL сайта:** [{GITHUB_SITE}]({GITHUB_SITE})")

    if st.button("Пересобрать docs/site", use_container_width=True):
        from atlas_agent.viz.publish_site import publish_discovery_site

        rep = st.session_state.get("report") or load_report()
        if rep:
            publish_discovery_site(rep, ROOT)
            st.success("docs/site обновлён")
        else:
            st.error("Нет latest.json — сначала полный scan")

    site_html = SITE_REPORT if SITE_REPORT.is_file() else HTML_REPORT
    if site_html.is_file():
        st.link_button("Открыть локальный сайт", site_html.resolve().as_uri(), use_container_width=True)

    st.code(
        "powershell -File scripts\\setup_github_pages.ps1   # первый раз\n"
        "powershell -File scripts\\push_site_github.ps1     # обновить сайт\n"
        "powershell -File scripts\\serve_site.ps1           # localhost:8765",
        language="powershell",
    )
