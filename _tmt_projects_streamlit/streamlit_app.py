# -*- coding: utf-8 -*-
"""Sirius Human TMT Proteome Atlas — anatomical map + projects (English UI)."""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.io as pio
import streamlit as st

from body_map_component import GITHUB_MAP, render_discovery_embed, render_map_iframe
from organ_atlas import (
    all_organ_stats,
    enrich_projects,
    normalize_database,
    normalize_pid,
    organ_project_counts,
    organ_stats,
)
from streamlit_theme import inject_theme, render_hero, render_kpi_row, render_organ_status

pio.templates.default = "plotly_dark"

APP_DIR = Path(__file__).resolve().parent
DATA_FULL = APP_DIR / "data" / "projects.csv"
DATA_SUMMARY = APP_DIR / "data" / "projects_summary.csv"
STATS_JSON = APP_DIR / "data" / "atlas_stats.json"
PROJECTS_DIR = APP_DIR / "Projects"
GITHUB_BASE = "https://github.com/arinaatom-cyber/tmt-projects/tree/main/Projects"

ORGAN_GROUPS = [
    ("Head & Neck", ["Brain", "Pituitary", "Eye", "Thyroid", "Salivary_Gland", "Esophagus"]),
    ("Thorax", ["Lung", "Heart", "Breast"]),
    ("Abdomen", ["Liver", "Stomach", "Pancreas", "Spleen", "Adrenal_Gland", "Kidney", "Small_Intestine", "Colon"]),
    ("Pelvic & Urinary", ["Bladder", "Ovary", "Uterus", "Cervix", "Prostate", "Testis"]),
    ("Blood & Immune", ["Blood", "Bone_Marrow", "Lymph_Node"]),
]


def organ_label(key: str) -> str:
    return key.replace("_", " ")


@st.cache_data
def load_stats() -> dict:
    if STATS_JSON.exists():
        return json.loads(STATS_JSON.read_text(encoding="utf-8"))
    return {}


@st.cache_data
def load_projects() -> pd.DataFrame:
    path = DATA_FULL if DATA_FULL.exists() else DATA_SUMMARY
    df = pd.read_csv(path, encoding="utf-8-sig", low_memory=False)
    pid = df["Project ID"].astype(str).str.strip()
    df = df[pid.notna() & ~pid.isin(["", "nan", "NaN", "None"])].copy()
    if path == DATA_SUMMARY:
        df["project_key"] = df["Project ID"].map(normalize_pid)
        df["organs"] = df["Organ"].fillna("").map(
            lambda x: [organ_label(p.strip()) for p in str(x).split(";") if p.strip()] or ["Other"]
        )
        df["healthy"] = False
        df["is_pan"] = False
    else:
        df = enrich_projects(df)
    df = df[df["project_key"].notna() & (df["project_key"].astype(str).str.strip() != "nan")].copy()
    # Keep one row per catalog Project ID (not inferred from PXD prefix).
    df = df.drop_duplicates(subset=["Project ID"], keep="first").reset_index(drop=True)
    df["has_repo_data"] = df["project_key"].map(lambda k: (PROJECTS_DIR / str(k)).is_dir())
    return df


def organ_choices(counts: Counter, current: str | None = None) -> list[tuple[str, str]]:
    """(label, organ_key) pairs for selectbox."""
    items = [("All organs", "")]
    seen: set[str] = {""}
    if current and current not in counts:
        items.append((f"{organ_label(current)} (0)", current))
        seen.add(current)
    for organ, n in counts.most_common():
        if n <= 0 or organ == "Other" or organ in seen:
            continue
        items.append((f"{organ_label(organ)} ({n})", organ))
        seen.add(organ)
    return items


def _query_organ() -> str | None:
    qp = st.query_params.get("organ")
    if qp is None:
        return None
    if isinstance(qp, list):
        qp = qp[0] if qp else None
    raw = str(qp or "").strip()
    return raw or None


def sync_organ_from_url(valid: set[str] | None = None) -> None:
    qp = _query_organ()
    if qp:
        if valid and qp not in valid:
            st.session_state.selected_organ = None
            st.query_params.pop("organ", None)
        else:
            st.session_state.selected_organ = qp
    elif "selected_organ" not in st.session_state:
        st.session_state.selected_organ = None


def set_organ(organ: str | None) -> None:
    st.session_state.selected_organ = organ
    if organ:
        st.query_params["organ"] = organ
    else:
        st.query_params.pop("organ", None)


def filter_projects(
    df: pd.DataFrame,
    *,
    organ: str | None,
    database: str | None,
    health: str | None,
    disease_query: str,
    only_with_data: bool,
    search: str,
) -> pd.DataFrame:
    out = df.copy()
    if organ:
        out = out[out["organs"].map(lambda xs: organ in xs)]
    if database and database != "All":
        out = out[out["Database"] == database]
    if health == "cancer":
        out = out[~out["healthy"]]
    elif health == "normal":
        out = out[out["healthy"]]
    if disease_query:
        q = disease_query.lower()
        out = out[out["Disease"].fillna("").str.lower().str.contains(q, regex=False)]
    if only_with_data:
        out = out[out["has_repo_data"]]
    if search:
        q = search.lower().strip()
        organs_text = out["organs"].map(lambda xs: " ".join(xs).replace("_", " ").lower())
        tmt = out.get("TMT Label (Unified)", pd.Series([""] * len(out), index=out.index)).fillna("").astype(str).str.lower()
        mask = (
            out["Project ID"].astype(str).str.lower().str.contains(q, regex=False)
            | out["Title"].fillna("").str.lower().str.contains(q, regex=False)
            | out["PMID"].astype(str).str.contains(q, regex=False)
            | out["Organ"].fillna("").str.lower().str.contains(q, regex=False)
            | out["Disease"].fillna("").str.lower().str.contains(q, regex=False)
            | out["Database"].fillna("").str.lower().str.contains(q, regex=False)
            | out["project_key"].astype(str).str.lower().str.contains(q, regex=False)
            | organs_text.str.contains(q, regex=False)
            | tmt.str.contains(q, regex=False)
        )
        out = out[mask]
    return out


def github_project_url(project_key: str) -> str:
    return f"{GITHUB_BASE}/{project_key}"


def pubmed_url(pmid) -> str:
    try:
        return f"https://pubmed.ncbi.nlm.nih.gov/{int(float(pmid))}/"
    except (TypeError, ValueError):
        return ""


def hbar(df: pd.DataFrame, x: str, y: str, title: str, color: str = "#9cb8d9") -> None:
    fig = px.bar(df, x=x, y=y, orientation="h", title=title, color_discrete_sequence=[color], text=x)
    fig.update_layout(
        height=max(280, 28 * len(df)),
        margin=dict(l=10, r=10, t=40, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    fig.update_traces(textposition="outside")
    fig.update_yaxes(autorange="reversed")
    st.plotly_chart(fig, use_container_width=True)


def render_organ_picker(counts: Counter) -> None:
    choices = organ_choices(counts, st.session_state.selected_organ)
    labels = [c[0] for c in choices]
    keys = [c[1] for c in choices]
    st.session_state._organ_labels = labels
    st.session_state._organ_keys = keys
    current = st.session_state.selected_organ or ""
    try:
        idx = keys.index(current)
    except ValueError:
        idx = 0
    st.selectbox(
        "Select organ",
        labels,
        index=idx,
        key="organ_selectbox",
        on_change=_on_organ_selectbox_change,
    )


def render_project_cards(filtered: pd.DataFrame) -> None:
    for _, row in filtered.iterrows():
        pid = str(row.get("Project ID", "")).strip()
        if not pid or pid.lower() == "nan":
            continue
        key = str(row["project_key"])
        status = "NORMAL" if row.get("healthy") else "CANCER"
        badge = "data on GitHub" if row["has_repo_data"] else "metadata only"
        with st.expander(f"**{pid}** — {status} · {badge}", expanded=False):
            st.markdown(f"**{row.get('Title', '')}**")
            c1, c2, c3, c4 = st.columns(4)
            c1.markdown(f"**Organ:** {row.get('Organ', '')}")
            c2.markdown(f"**Samples:** {row.get('Total Samples', '')}")
            c3.markdown(f"**Patients:** {row.get('Patients / donors', '—')}")
            c4.markdown(f"**TMT:** {row.get('TMT Label (Unified)', '')}")
            pm = pubmed_url(row.get("PMID"))
            pdc = str(row.get("URL", "") or "").strip()
            links = f"[{key} on GitHub]({github_project_url(key)})"
            if pdc:
                links = f"[PDC study]({pdc}) · {links}"
            if pm:
                links = f"[PubMed {int(float(row['PMID']))}]({pm}) · {links}"
            st.markdown(links)


def apply_organ_pick(picked: str | None, *, rerun: bool = True) -> None:
    """Handle organ selection from map component or sidebar."""
    new_organ = picked if picked else None
    if new_organ == st.session_state.selected_organ:
        return
    set_organ(new_organ)
    st.session_state.body_map_last_value = new_organ
    if rerun:
        st.rerun()


def _on_organ_selectbox_change() -> None:
    labels = st.session_state.get("_organ_labels", [])
    keys = st.session_state.get("_organ_keys", [])
    label = st.session_state.get("organ_selectbox", "")
    try:
        picked = keys[labels.index(label)]
    except (ValueError, IndexError):
        picked = ""
    apply_organ_pick(picked or None, rerun=True)


def database_choices(df: pd.DataFrame) -> list[str]:
    """Repository filter options from catalog column Database."""
    counts = df["Database"].fillna("Unknown").value_counts()
    items = ["All"]
    for db, n in counts.items():
        label = normalize_database(db)
        if label == "Unknown":
            continue
        items.append(f"{label} ({n})")
    return items


def parse_database_choice(choice: str) -> str | None:
    if choice == "All":
        return None
    return choice.split(" (", 1)[0].strip()


def render_projects_table(
    filtered: pd.DataFrame,
    *,
    sel_db: str | None,
    health_key: str | None,
) -> None:
    if filtered.empty:
        st.warning("No projects match these filters.")
        if sel_db == "GTEx" and health_key == "cancer":
            st.caption("GTEx (PXD016999) has no cancer samples — try **Normal only**.")
        return

    table_cols = [
        "Project ID",
        "Database",
        "PMID",
        "Organ",
        "Disease",
        "Total Samples",
        "Patients / donors",
        "TMT Label (Unified)",
        "URL",
        "has_repo_data",
    ]
    table = filtered[[c for c in table_cols if c in filtered.columns]].copy()
    table["Project ID"] = table["Project ID"].astype(str)
    table = table[~table["Project ID"].isin(["nan", "NaN", ""])].rename(columns={"has_repo_data": "Data in repo"})
    if "PMID" in table.columns:
        table["PMID"] = table["PMID"].map(
            lambda v: pubmed_url(v) if pd.notna(v) and str(v).strip() not in ("", "nan") else ""
        )
    st.dataframe(
        table,
        hide_index=True,
        use_container_width=True,
        height=min(560, 38 + 35 * len(table)),
        column_config={
            "PMID": st.column_config.LinkColumn("PMID", display_text=r"https://pubmed\.ncbi\.nlm\.nih\.gov/(\d+)/?"),
            "URL": st.column_config.LinkColumn("Source URL"),
        },
    )
    with st.expander("Project details", expanded=False):
        render_project_cards(filtered)


def render_map_page(df: pd.DataFrame, counts: Counter, stats: dict) -> None:
    with st.sidebar:
        st.markdown('<p class="sidebar-section">Filters</p>', unsafe_allow_html=True)
        db_labels = database_choices(df)
        sel_db_label = st.selectbox("Repository", db_labels)
        sel_db = parse_database_choice(sel_db_label)
        sel_health = st.selectbox(
            "Sample type",
            ["All", "Cancer only", "Normal only"],
        )
        health_key = {"All": None, "Cancer only": "cancer", "Normal only": "normal"}[sel_health]
        if sel_db == "GTEx" and health_key == "cancer":
            st.caption("GTEx = normal tissue only")
        disease_q = st.text_input("Disease contains", placeholder="e.g. lung, AML…")
        only_data = st.checkbox("Only with files in repo", value=False)
        search_q = st.text_input(
            "Search projects",
            placeholder="PXD, PDC, organ, disease, PMID, title…",
            help="Searches Project ID, organ, disease, repository, TMT label, title, PMID.",
        )

        filtered_base = filter_projects(
            df,
            organ=None,
            database=sel_db,
            health=health_key,
            disease_query=disease_q,
            only_with_data=only_data,
            search=search_q,
        )
        sidebar_counts = organ_project_counts(filtered_base)

        st.markdown('<p class="sidebar-section">Organ</p>', unsafe_allow_html=True)
        render_organ_picker(sidebar_counts)
        if st.session_state.selected_organ:
            if st.button("Clear organ filter", use_container_width=True):
                apply_organ_pick(None)
        st.caption(f"**{len(filtered_base)}** projects after filters")

    filtered = filter_projects(
        filtered_base,
        organ=st.session_state.selected_organ,
        database=None,
        health=None,
        disease_query="",
        only_with_data=False,
        search="",
    )

    st.markdown('<p class="section-title">Anatomical map</p>', unsafe_allow_html=True)
    organ_q = st.session_state.selected_organ or ""
    hdr_l, hdr_r = st.columns([4, 1])
    with hdr_l:
        st.caption(
            "Same page as [arinaatom-cyber.github.io/TMT](https://arinaatom-cyber.github.io/TMT/) — "
            "click organs inside the map; scroll inside the frame for the full figure."
        )
    with hdr_r:
        st.link_button(
            "Open full screen",
            f"{GITHUB_MAP}?organ={organ_q}" if organ_q else GITHUB_MAP,
            use_container_width=True,
        )

    with st.container(border=True):
        render_map_iframe(organ_q or None, height=1320)

    render_organ_status(st.session_state.selected_organ, stats, filtered_base)

    organ_part = f" · {organ_label(st.session_state.selected_organ)}" if st.session_state.selected_organ else ""
    st.markdown(
        f'<p class="section-title">Projects{organ_part} '
        f'<span style="color:#7d8fa6;font-weight:400">({len(filtered)} of {len(filtered_base)})</span></p>',
        unsafe_allow_html=True,
    )
    if search_q:
        st.caption(f'Filter: search «{search_q}»')
    render_projects_table(filtered, sel_db=sel_db, health_key=health_key)


def render_discovery_page() -> None:
    st.markdown('<p class="section-title">Discovery — new projects</p>', unsafe_allow_html=True)
    st.caption(
        "Weekly scan: PRIDE, PDC, MassIVE, iProX, Europe PMC. "
        "Candidates are reviewed before adding to the atlas."
    )
    c1, c2, c3 = st.columns(3)
    c1.link_button("Full report", "https://arinaatom-cyber.github.io/TMT/discovery/discovery.html", use_container_width=True)
    c2.link_button("Portal", "https://arinaatom-cyber.github.io/TMT/discovery/index.html", use_container_width=True)
    c3.link_button("QC", "https://arinaatom-cyber.github.io/TMT/discovery/qc.html", use_container_width=True)
    with st.container(border=True):
        render_discovery_embed(height=1200)


def render_statistics_page(stats: dict, df: pd.DataFrame | None = None) -> None:
    if not stats:
        if df is None or df.empty:
            st.warning("`data/atlas_stats.json` not found.")
            return
        st.caption("Using live counts from `data/projects.csv` (atlas_stats.json missing).")
        ov = {
            "datasets": len(df),
            "unique_pmids": df["PMID"].nunique(),
            "total_samples": int(pd.to_numeric(df["Total Samples"], errors="coerce").fillna(0).sum()),
            "patients_donors": int(pd.to_numeric(df.get("Patients / donors", 0), errors="coerce").fillna(0).sum()),
            "control_healthy": int(pd.to_numeric(df.get("Control Healthy", 0), errors="coerce").fillna(0).sum()),
            "case_untreated": int(pd.to_numeric(df.get("Case Cancer Untreated", 0), errors="coerce").fillna(0).sum()),
            "case_treated": int(pd.to_numeric(df.get("Case Cancer Treated", 0), errors="coerce").fillna(0).sum()),
            "precancer": int(pd.to_numeric(df.get("preCancer", 0), errors="coerce").fillna(0).sum()),
        }
        pr = {"unique_uniprot": 0, "unique_genes": 0, "unique_ensembl": 0, "projects_counted": 0}
        stats = {
            "overview": ov,
            "proteins": pr,
            "repositories": [],
            "top_organs_datasets": [],
            "top_organs_samples": [],
            "top_diseases": [],
            "tmt_schemes": [],
            "sample_types": [],
            "top_projects": [],
        }
    else:
        ov = stats["overview"]
        pr = stats["proteins"]

    st.subheader("Overview")
    r1 = st.columns(4)
    r1[0].metric("Datasets", f"{ov['datasets']:,}")
    r1[1].metric("Unique PMIDs", f"{ov['unique_pmids']:,}")
    r1[2].metric("Total samples", f"{ov['total_samples']:,}")
    r1[3].metric("Patients / donors", f"{ov['patients_donors']:,}")

    r2 = st.columns(4)
    r2[0].metric("Healthy / control", f"{ov['control_healthy']:,}")
    case_total = ov["case_untreated"] + ov["case_treated"] + ov["precancer"]
    r2[1].metric("Tumor / case", f"{case_total:,}")
    r2[2].metric("Case untreated", f"{ov['case_untreated']:,}")
    r2[3].metric("Case treated", f"{ov['case_treated']:,}")

    st.subheader("Unique proteins (atlas union)")
    st.caption(f"Counted from `*_result.csv` in {pr['projects_counted']} projects with quantitative files.")
    p1, p2, p3 = st.columns(3)
    p1.metric("UniProt", f"{pr['unique_uniprot']:,}")
    p2.metric("Gene", f"{pr['unique_genes']:,}")
    p3.metric("Ensembl", f"{pr['unique_ensembl']:,}")

    col_a, col_b = st.columns(2)
    with col_a:
        healthy_df = pd.DataFrame({
            "Category": ["Healthy / control", "Case untreated", "Case treated", "preCancer"],
            "Samples": [ov["control_healthy"], ov["case_untreated"], ov["case_treated"], ov["precancer"]],
        })
        st.plotly_chart(
            px.pie(healthy_df, names="Category", values="Samples", title="Samples: healthy vs tumor"),
            use_container_width=True,
        )
    with col_b:
        repo_df = pd.DataFrame(stats.get("repositories") or [])
        if not repo_df.empty:
            st.plotly_chart(
                px.bar(repo_df, x="repo", y="count", title="Datasets by repository", text="count"),
                use_container_width=True,
            )

    col_c, col_d = st.columns(2)
    with col_c:
        organs_ds = pd.DataFrame(stats.get("top_organs_datasets") or [])
        if not organs_ds.empty:
            hbar(organs_ds, "count", "organ", "Top organs (datasets)")
    with col_d:
        organs_sm = pd.DataFrame(stats.get("top_organs_samples") or [])
        if not organs_sm.empty:
            hbar(organs_sm, "samples", "organ", "Top organs (samples)", "#9dc9b0")

    col_e, col_f = st.columns(2)
    with col_e:
        diseases = pd.DataFrame(stats.get("top_diseases") or [])
        if not diseases.empty:
            hbar(diseases, "count", "disease", "Top diseases", "#c4a8d4")
    with col_f:
        tmt_df = pd.DataFrame(stats.get("tmt_schemes") or [])
        if not tmt_df.empty:
            st.plotly_chart(
                px.pie(tmt_df, names="scheme", values="count", title="TMT schemes"),
                use_container_width=True,
            )

    sample_types = pd.DataFrame(stats.get("sample_types") or [])
    if not sample_types.empty:
        st.subheader("Sample material")
        st.dataframe(sample_types, hide_index=True, use_container_width=True)
    top_projects = pd.DataFrame(stats.get("top_projects") or [])
    if not top_projects.empty:
        st.subheader("Largest projects (by samples)")
        st.dataframe(top_projects, hide_index=True, use_container_width=True)


def main() -> None:
    st.set_page_config(
        page_title="Human TMT Proteome Atlas",
        page_icon="🧬",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    inject_theme()

    df = load_projects()
    counts = organ_project_counts(df)
    valid_organs = set(counts.keys())
    sync_organ_from_url(valid_organs)
    stats = all_organ_stats(df)
    atlas = load_stats()
    ov = atlas.get("overview", {})
    pr = atlas.get("proteins", {})

    render_hero()
    render_kpi_row(
        projects=ov.get("datasets", len(df)),
        samples=f"{ov.get('total_samples', int(pd.to_numeric(df['Total Samples'], errors='coerce').fillna(0).sum())):,}",
        proteins=f"{pr['unique_uniprot']:,}" if pr.get("unique_uniprot") else "—",
        healthy=f"{ov.get('control_healthy', 0):,}" if ov else "—",
        in_repo=int(df["has_repo_data"].sum()),
    )

    tab_map, tab_discovery, tab_stats = st.tabs(["Organ map", "New projects", "Statistics"])

    with tab_map:
        render_map_page(df, counts, stats)

    with tab_discovery:
        render_discovery_page()

    with tab_stats:
        render_statistics_page(atlas, df)


if __name__ == "__main__":
    main()
