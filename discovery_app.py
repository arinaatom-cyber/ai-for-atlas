#!/usr/bin/env python3
"""
Sirius TMT Atlas — Streamlit portal (read-only).

Tabs: AI search · Discovery (unified table) · Body map.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).parent
SITE_DISCOVERY = ROOT / "docs" / "site" / "discovery.html"
SITE_QC = ROOT / "docs" / "site" / "qc.html"

st.set_page_config(
    page_title="Sirius TMT Atlas Portal",
    layout="wide",
    initial_sidebar_state="expanded",
)

APP_VERSION = "2026.07.15-portal-v8-unified"

st.markdown(
    """
    <style>
    .portal-title { font-size: 1.75rem; font-weight: 600; color: #e8eef7; margin-bottom: 0.25rem; }
    .portal-sub { color: #8b9cb3; font-size: 0.95rem; margin-bottom: 1rem; }
    .metric-box {
        background: #151d2b; border: 1px solid #2a3548; border-radius: 8px;
        padding: 0.75rem 1rem; text-align: center;
    }
    .metric-num { font-size: 1.5rem; font-weight: 600; color: #6cb6ff; }
    .metric-lbl { font-size: 0.85rem; color: #8b9cb3; }
    .wip-banner {
        background: #2a2418; border: 1px solid #5c4a20; border-radius: 8px;
        padding: 0.6rem 1rem; color: #d4b86a; font-size: 0.9rem; margin-bottom: 1rem;
    }
    .stDataFrame { font-size: 1rem !important; }
    div[data-testid="stDataFrame"] td { font-size: 1rem !important; }
    div[data-testid="stDataFrame"] th { font-size: 0.9rem !important; }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data(ttl=180)
def load_catalog_bundle():
    from pathlib import Path

    from atlas_agent.config import load_config
    from atlas_agent.discovery.catalog_profile import build_catalog_profile
    from atlas_agent.sources.projects_table import load_catalog
    from atlas_agent.viz.portal_index import build_organ_index

    cfg = load_config()
    sheet = cfg.get("sheet") or {}
    catalog_path = sheet.get("projects_file") or ""
    try:
        if catalog_path and not Path(catalog_path).is_file():
            raise FileNotFoundError(catalog_path)
        from atlas_agent.discovery.agent import load_catalog_readonly

        df = load_catalog_readonly(cfg)
    except (FileNotFoundError, OSError):
        cloud_cfg = dict(cfg)
        cloud_cfg["sheet"] = dict(sheet)
        cloud_cfg["sheet"]["projects_file"] = str(ROOT / "data" / "projects.csv")
        cloud_cfg["sheet"]["projects_sheet"] = None
        df = load_catalog(cloud_cfg)
        st.sidebar.caption("Catalog: data/projects.csv (cloud fallback)")
    profile = build_catalog_profile(df)
    profile["n_atlas_projects"] = profile["n_unique_ids"]
    organ_index = build_organ_index(df, cfg)
    return df, profile, cfg, organ_index


def load_scan_report():
    from atlas_agent.discovery.history import load_latest

    return load_latest(ROOT)


def run_full_scan(cfg, df, year_from: int):
    from atlas_agent.discovery.agent import run_discovery_scan

    sc = dict(cfg.get("discovery") or {})
    sc["year_from"] = year_from
    merged = dict(cfg)
    merged["discovery"] = sc
    return run_discovery_scan(df, merged, root=ROOT)


def run_keyword_search(cfg, df, keywords, extra_query, y0, y1):
    from atlas_agent.discovery.keyword_search import run_keyword_ai_search

    return run_keyword_ai_search(
        df, cfg, keywords=keywords, extra_query=extra_query, year_from=y0, year_to=y1
    )


def _source_label(item: dict) -> str:
    acc = (item.get("project_accession") or item.get("accession") or "").upper()
    if acc.startswith("PDC"):
        return "PDC"
    if acc.startswith("PXD"):
        return "PRIDE"
    if acc.startswith("MSV"):
        return "MassIVE"
    if acc.startswith("IPX"):
        return "iProX"
    return str(item.get("source") or item.get("database") or "")


def _ai_summary(ai: dict) -> str:
    return ai.get("summary_en") or ai.get("summary_ru") or ""


def _pub_index(pubs: list[dict]) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for p in pubs:
        pmid = str(p.get("pmid") or "").strip()
        if pmid:
            out[pmid] = p
    return out


def _analysis_text(item: dict, pubs_by_pmid: dict[str, dict]) -> str:
    from atlas_agent.viz.portal_index import format_finding_note

    parts: list[str] = []
    note = item.get("finding_note") or format_finding_note(item)
    if note:
        parts.append(note[:200])
    pmid = str(item.get("pmid") or "").strip()
    pub = pubs_by_pmid.get(pmid) if pmid else None
    if pub:
        summary = pub.get("summary_en") or ""
        fit = pub.get("atlas_fit")
        if summary:
            parts.append(summary[:180])
        if fit:
            parts.append(f"fit: {fit}")
    else:
        ai = item.get("abstract_ai") or {}
        if ai.get("summary_en"):
            parts.append(ai["summary_en"][:180])
    return " · ".join(parts) if parts else ""


def _data_label(item: dict) -> str:
    da = item.get("data_availability") or {}
    if not da:
        return ""
    label = da.get("label") or da.get("status") or ""
    samples = da.get("proteome_files") or da.get("quant_files") or da.get("sample_files") or []
    if samples:
        return f"{label} · {samples[0][:40]}"
    return label


def new_projects_table(items: list[dict], pubs: list[dict]) -> pd.DataFrame:
    from atlas_agent.viz.portal_index import format_finding_note, resolve_publication_links, repository_url

    pubs_by_pmid = _pub_index(pubs)
    rows = []
    for p in items:
        resolve_publication_links(p, fetch_pride_pmid=True)
        p["finding_note"] = format_finding_note(p)
        acc = (p.get("project_accession") or p.get("accession") or "").strip().upper()
        repo = p.get("repository_url") or repository_url(acc)
        rows.append({
            "ID": acc,
            "Title": (p.get("title") or "")[:100],
            "Source": _source_label(p),
            "Design": str(p.get("sample_design") or "").replace("_", "-"),
            "Analysis": _analysis_text(p, pubs_by_pmid),
            "Data": _data_label(p),
            "Repository": repo,
            "PubMed": p.get("pubmed_url") or "",
        })
    return pd.DataFrame(rows)


def papers_without_id_table(manual: list[dict], literature: list[dict]) -> pd.DataFrame:
    from atlas_agent.sources.dataset_resolve import _url_for_accession
    from atlas_agent.viz.portal_index import europe_pmc_url, pubmed_url

    seen: set[str] = set()
    rows = []
    for p in manual + literature:
        pmid = str(p.get("pmid") or "").strip()
        key = pmid or str(p.get("title") or "")[:80]
        if key in seen:
            continue
        seen.add(key)
        ai = p.get("abstract_ai") or {}
        fit = p.get("atlas_fit") or ai.get("atlas_fit", "")
        score = p.get("atlas_fit_score") or ai.get("atlas_fit_score", "")
        weight = f"{fit} ({score})" if score else str(fit)
        accs = p.get("accessions_mentioned") or p.get("pxd_mentioned") or []
        acc = str(accs[0]).upper() if accs else ""
        rows.append({
            "PMID": pmid,
            "Title": (p.get("title") or "")[:100],
            "Weight": weight,
            "Europe PMC": europe_pmc_url(pmid) if pmid else "",
            "Analysis": ai.get("summary_en") or p.get("summary_en") or p.get("finding_note") or "",
            "PubMed": pubmed_url(pmid),
            "Project": _url_for_accession(acc) if acc else "",
        })
    return pd.DataFrame(rows)


def cohorts_table(items: list[dict]) -> pd.DataFrame:
    from atlas_agent.viz.portal_index import europe_pmc_url, pubmed_url

    rows = []
    for p in items:
        pmid = str(p.get("pmid") or "").strip()
        omics = ", ".join(p.get("omics") or [])[:80]
        rows.append({
            "PMID": pmid,
            "Title": (p.get("title") or "")[:100],
            "Weight": p.get("cohort_score") or "",
            "Europe PMC": europe_pmc_url(pmid) if pmid else "",
            "Year": p.get("year") or "",
            "Journal": (p.get("journal") or "")[:60],
            "Patients": p.get("has_patients") or "",
            "N": p.get("patient_n") or "",
            "Omics": omics,
            "TMT": "yes" if p.get("tmt_detected") else "",
            "Analysis": (p.get("description_en") or "")[:140],
            "PubMed": pubmed_url(pmid),
        })
    return pd.DataFrame(rows)


def unified_discovery_table(report: dict) -> pd.DataFrame:
    """One table: projects + papers without ID + literature cohorts."""
    if not report:
        return pd.DataFrame()
    cand = report.get("candidates") or report.get("new_projects") or []
    pubs = report.get("publications_analyzed") or []
    manual = report.get("manual_check") or []
    literature = report.get("literature_semantic") or []
    cohorts = report.get("cohort_literature") or []

    rows: list[dict] = []
    for _, r in new_projects_table(cand, pubs).iterrows():
        rows.append({
            "Type": "Project",
            "Project ID": r["ID"],
            "Title": r["Title"],
            "Source": r["Source"],
            "Design": r["Design"],
            "Patients": "",
            "N": "",
            "Fit": "",
            "Analysis": r["Analysis"],
            "Data": r["Data"],
            "Repository": r["Repository"],
            "PubMed": r["PubMed"],
        })
    for _, r in papers_without_id_table(manual, literature).iterrows():
        rows.append({
            "Type": "Paper",
            "Project ID": "No PXD",
            "Title": r["Title"],
            "Source": "Europe PMC",
            "Design": "",
            "Patients": "",
            "N": "",
            "Fit": r["Weight"],
            "Analysis": r["Analysis"],
            "Data": "",
            "Repository": r["Project"],
            "PubMed": r["PubMed"],
        })
    for _, r in cohorts_table(cohorts).iterrows():
        rows.append({
            "Type": "Cohort",
            "Project ID": r["PMID"],
            "Title": r["Title"],
            "Source": "Europe PMC",
            "Design": r["Omics"],
            "Patients": r["Patients"],
            "N": r["N"],
            "Fit": r["Weight"],
            "Analysis": r["Analysis"],
            "Data": "TMT" if r["TMT"] else "",
            "Repository": r["Europe PMC"],
            "PubMed": r["PubMed"],
        })
    return pd.DataFrame(rows)


    rows = []
    for p in items:
        ai = p.get("abstract_ai") or {}
        accs = p.get("accessions_mentioned") or p.get("pxd_mentioned") or []
        rows.append({
            "PMID": p.get("pmid", ""),
            "Fit": ai.get("atlas_fit") or p.get("atlas_fit", ""),
            "Finding": p.get("finding_note") or _ai_summary(ai),
            "TMT": ai.get("tmt", ""),
            "Material": ai.get("material", ""),
            "IDs in text": ", ".join(accs[:3]),
            "Title": (p.get("title") or "")[:80],
        })
    return pd.DataFrame(rows)


def keyword_repo_table(items: list[dict]) -> pd.DataFrame:
    from atlas_agent.sources.dataset_resolve import _url_for_accession

    rows = []
    for p in items:
        acc = p.get("accession") or p.get("project_accession") or ""
        sim = (p.get("similar_in_catalog") or [{}])[0]
        rows.append({
            "ID": acc,
            "Source": _source_label(p),
            "Finding": p.get("finding_note", ""),
            "Similar to": sim.get("project_id", ""),
            "Link": _url_for_accession(acc.upper()) if acc else "",
            "Title": (p.get("title") or p.get("projectTitle") or "")[:80],
        })
    return pd.DataFrame(rows)


def render_project_links(card: dict):
    c1, c2, c3, c4 = st.columns(4)
    if card.get("repository_url"):
        c1.link_button("PRIDE / PDC / MSV", card["repository_url"], use_container_width=True)
    if card.get("pubmed_url"):
        c2.link_button("PubMed", card["pubmed_url"], use_container_width=True)
    if card.get("atlas_map_url"):
        c3.link_button("Organ map", card["atlas_map_url"], use_container_width=True)
    gh = card.get("github") or {}
    if gh.get("tmt_projects_folder"):
        c4.link_button("GitHub: data", gh["tmt_projects_folder"], use_container_width=True)
    if gh.get("atlas_repo_folder"):
        st.link_button("GitHub: TMT repo", gh["atlas_repo_folder"], use_container_width=False)


# --- Header ---
st.markdown('<p class="portal-title">Sirius Human TMT Proteome Atlas — Portal</p>', unsafe_allow_html=True)
st.markdown(
    '<p class="portal-sub">🔍 AI search · Discovery (unified table) · Body map</p>',
    unsafe_allow_html=True,
)

df, profile, cfg, organ_index = load_catalog_bundle()
disc = cfg.get("discovery") or {}
gh_meta = organ_index.get("github") or {}

with st.sidebar:
    st.subheader("Controls")
    year_scan = st.slider("Year from (full scan)", 2020, 2026, int(disc.get("year_from") or 2024))
    if st.button("Reload scan from disk", use_container_width=True):
        st.session_state["scan_report"] = load_scan_report()
        st.rerun()
    if st.button("Run full Discovery scan", type="primary", use_container_width=True):
        st.session_state["run_full_scan"] = True
    st.divider()
    st.metric("TMT ATLAS projects", organ_index["n_projects"])
    st.caption(f"UI version: {APP_VERSION}")
    st.markdown(f"[Discovery site]({gh_meta.get('discovery_site', '')})")
    st.markdown(f"[QC site]({gh_meta.get('discovery_site', '').replace('discovery.html', 'qc.html')})")
    st.markdown(f"[Interactive map]({gh_meta.get('streamlit_map') or gh_meta.get('atlas_map', '')})")
    st.divider()
    st.markdown("**Tabs:**")
    st.markdown("1. **🔍 AI search** — Run search")
    st.markdown("2. **Discovery** — projects + papers + cohorts (one table)")
    st.markdown("3. **Body map**")

if "scan_report" not in st.session_state:
    st.session_state["scan_report"] = load_scan_report()

if st.session_state.pop("run_full_scan", False):
    with st.spinner("Discovery scan (PRIDE, PDC, MassIVE, iProX, Europe PMC)…"):
        st.session_state["scan_report"] = run_full_scan(cfg, df, year_scan)

tab_keywords, tab_discovery, tab_map = st.tabs([
    "🔍 AI search",
    "Discovery",
    "Body map",
])

# --- Tab 1: AI keyword search ---
with tab_keywords:
    st.subheader("AI keyword search — run here")
    from atlas_agent.discovery.keyword_search import default_search_keywords

    st.markdown(
        "Search by **atlas profile keywords** (organs, diseases, TMT) across repositories "
        "and Europe PMC. LLM scores abstracts by meaning (not exact title match)."
    )

    default_kw = default_search_keywords(cfg, profile)
    kw_left, kw_right = st.columns([2, 1])
    with kw_left:
        kw_raw = st.text_area("Keywords", value="\n".join(default_kw), height=120)
    with kw_right:
        y0 = st.number_input("Year from", 2020, 2026, int(disc.get("year_from") or 2024))
        y1 = st.number_input("Year to", 2020, 2026, int(disc.get("year_to") or 2026))
        extra = st.text_input("Extra Europe PMC query", placeholder="gastric TMT adjacent normal")

    keywords = []
    for line in kw_raw.replace(",", "\n").splitlines():
        k = line.strip()
        if k and k not in keywords:
            keywords.append(k)

    st.caption(
        f"Catalog profile: {', '.join(profile.get('top_organs') or [])[:4]} · "
        f"{', '.join(profile.get('top_diseases') or [])[:4]}"
    )

    if st.button("Run search", type="primary", use_container_width=True):
        with st.spinner("Steps 1–4: repositories → literature → filters → LLM…"):
            st.session_state["kw_result"] = run_keyword_search(cfg, df, keywords, extra, int(y0), int(y1))

    kw_res = st.session_state.get("kw_result")
    if kw_res:
        stats = kw_res.get("source_stats") or {}
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("PRIDE", stats.get("pride", 0))
        c2.metric("PDC", stats.get("pdc", 0))
        c3.metric("Papers", stats.get("publications", 0))
        c4.metric("New IDs", len(kw_res.get("repository_novel") or []))
        c5.metric("LLM", stats.get("llm_read", 0))

        with st.expander("Europe PMC query (step 2)"):
            st.code(kw_res.get("literature_query") or "")

        sub_r, sub_p = st.tabs(["Repositories", "Publications"])
        with sub_r:
            repos = kw_res.get("repository_candidates") or kw_res.get("repository_novel") or []
            if repos:
                st.dataframe(keyword_repo_table(repos), use_container_width=True, hide_index=True, height=360)
            else:
                st.caption("No new repository IDs")
        with sub_p:
            pubs = kw_res.get("publications") or []
            fit = st.selectbox("Atlas fit", ["All", "yes", "maybe", "no"])
            if fit != "All":
                pubs = [
                    p
                    for p in pubs
                    if (p.get("abstract_ai") or {}).get("atlas_fit") == fit or p.get("atlas_fit") == fit
                ]
            if pubs:
                st.dataframe(keyword_pub_table(pubs), use_container_width=True, hide_index=True, height=360)
            else:
                st.caption("No publications")

        st.download_button(
            "Download JSON",
            json.dumps(kw_res, ensure_ascii=False, indent=2, default=str),
            file_name=f"keyword_search_{datetime.now():%Y%m%d}.json",
        )
    else:
        st.info("Click **Run search** above to start AI keyword discovery.")

# --- Tab 2: Unified Discovery ---
with tab_discovery:
    st.subheader("Discovery — unified table")
    report = st.session_state.get("scan_report")
    if not report:
        st.info("No saved scan. Sidebar → **Run full Discovery scan** or `python run_discovery.py scan`.")
    else:
        s = report.get("summary") or {}
        cand = report.get("candidates") or report.get("new_projects") or []
        manual = report.get("manual_check") or []
        literature = report.get("literature_semantic") or []
        cohorts = report.get("cohort_literature") or []
        table_n = sum(1 for x in cand if (x.get("data_availability") or {}).get("status") == "quant_table")
        atlas_n = s.get("catalog_unique_ids", "?")
        papers_df = papers_without_id_table(manual, literature)
        total = len(cand) + len(papers_df) + len(cohorts)

        st.caption(
            f"**{total} rows** in one table: {len(cand)} projects · "
            f"{len(papers_df)} papers · {len(cohorts)} cohorts "
            f"({atlas_n} already in atlas). Same view as GitHub **discovery.html**."
        )
        link_col1, link_col2 = st.columns(2)
        if SITE_DISCOVERY.is_file():
            link_col1.link_button("GitHub Discovery", gh_meta.get("discovery_site", ""), use_container_width=True)
        link_col2.link_button("QC report", gh_meta.get("discovery_site", "").replace("discovery.html", "qc.html"), use_container_width=True)

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Projects", len(cand))
        m2.metric("Papers", len(papers_df))
        m3.metric("Cohorts", len(cohorts))
        m4.metric("With protein table", table_n)

        type_filter = st.selectbox("Type filter", ["All", "Project", "Paper", "Cohort"], key="disc_type_filter")
        search = st.text_input("Search", placeholder="PXD, PDC, gastric, cohort…", key="disc_search")
        udf = unified_discovery_table(report)
        if type_filter != "All":
            udf = udf[udf["Type"] == type_filter]
        if search:
            fl = search.lower()
            udf = udf[udf.astype(str).apply(lambda row: fl in " ".join(row.values).lower(), axis=1)]
        if not udf.empty:
            st.dataframe(
                udf,
                use_container_width=True,
                hide_index=True,
                height=min(560, 80 + 38 * min(len(udf), 16)),
                column_config={
                    "Repository": st.column_config.LinkColumn("Repository", display_text="Open"),
                    "PubMed": st.column_config.LinkColumn("PubMed", display_text="PubMed"),
                },
            )
        else:
            st.caption("No rows match filter")

with tab_map:
    st.subheader("Human body organ map")
    streamlit_map = gh_meta.get("streamlit_map") or gh_meta.get("atlas_map", "")
    github_map = gh_meta.get("atlas_map", "")
    st.markdown(
        "Open the interactive map in a **separate tab** (faster than embedding). "
        "Streamlit Cloud hosts the portal; GitHub Pages hosts the static SVG map."
    )
    c1, c2 = st.columns(2)
    if streamlit_map:
        c1.link_button("Open on Streamlit Cloud", streamlit_map, use_container_width=True)
    if github_map:
        c2.link_button("Open on GitHub Pages (TMT)", github_map, use_container_width=True)
    st.caption("Deep link example: add `?organ=gastric` to filter by organ.")

    organs = sorted(
        organ_index["organ_counts"].keys(),
        key=lambda o: (-organ_index["organ_counts"][o], o),
    )
    st.markdown("**Organs in catalog** (quick index — full map opens above)")
    cols = st.columns(4)
    for i, organ in enumerate(organs[:16]):
        n = organ_index["organ_counts"][organ]
        cols[i % 4].markdown(f"· {organ.replace('_', ' ')} ({n})")
    if len(organs) > 16:
        st.caption(f"+ {len(organs) - 16} more organs — see full map")
