#!/usr/bin/env python3

from __future__ import annotations

import json
import textwrap
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.gridspec import GridSpec
from matplotlib.colors import LinearSegmentedColormap
import numpy as np
import pandas as pd
import requests
import seaborn as sns

PROJECT_ROOT = Path(r"C:\Users\Arina1996\Desktop\Gastric_Cancer_Review")
EXCEL_PATH = PROJECT_ROOT / "tables" / "gastric_cancer_markers_only_clin_study_2016_2026.xlsx"
OUT_DIR = PROJECT_ROOT / "clinical"
GPROFILER_URL = "https://biit.cs.ut.ee/gprofiler/api/gost/profile/"

CLIN_COLORS = {
    "DNA Repair (MSI)": "#2166AC",
    "Immunotherapy": "#B2182B",
    "Prognostic Markers": "#1B7837",
    "Signaling Pathways": "#E66101",
    "Targeted Therapy": "#762A83",
}

SUBTYPE_COLORS = {
    "CIN": "#2166AC",
    "MSI": "#4393C3",
    "EBV": "#92C5DE",
    "GS": "#D1E5F0",
    "Intestinal": "#1B7837",
    "Diffuse": "#5AAE61",
    "Mixed": "#A6DBA0",
    "Unclassified": "#969696",
}

STRESS_GENES = {
    "HSP": ["HSP90AA1", "HSP90AB1", "HSPA1A", "HSPA1B", "HSPA8", "HSPB1", "HSPD1", "HSPE1", "HSPH1"],
    "ANXA": ["ANXA1", "ANXA2", "ANXA4", "ANXA5", "ANXA6"],
    "S100": ["S100A2", "S100A4", "S100A6", "S100A7", "S100A8", "S100A9", "S100A10", "S100A11"],
}


def setup_style() -> None:
    plt.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.sans-serif": ["Arial", "DejaVu Sans", "Helvetica"],
            "font.size": 9,
            "axes.titlesize": 10,
            "axes.labelsize": 9,
            "axes.titleweight": "bold",
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "figure.dpi": 150,
            "savefig.dpi": 300,
            "axes.spines.top": False,
            "axes.spines.right": False,
        }
    )


def load_all() -> dict[str, pd.DataFrame]:
    xl = pd.ExcelFile(EXCEL_PATH)
    return {s: pd.read_excel(EXCEL_PATH, sheet_name=s) for s in xl.sheet_names}


def clean_go_label(text: str, max_len: int = 55) -> str:
    t = str(text).strip().strip('"')
    for sep in ['" [', " [GOC:", " [PMID:", " [ISBN:"]:
        if sep in t:
            t = t.split(sep)[0].strip().strip('"')
    return (t[: max_len - 1] + "…") if len(t) > max_len else t


def run_gprofiler(genes: list[str], sources: list[str] | None = None) -> pd.DataFrame:
    sources = sources or ["GO:BP", "GO:MF", "GO:CC", "KEGG", "REAC"]
    resp = requests.post(
        GPROFILER_URL,
        json={
            "organism": "hsapiens",
            "query": genes,
            "sources": sources,
            "user_threshold": 0.05,
            "all_results": False,
        },
        timeout=120,
    )
    resp.raise_for_status()
    rows = resp.json().get("result", [])
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows)
    df["neg_log10_p"] = -np.log10(df["p_value"].clip(lower=1e-300))
    df["gene_ratio"] = df["intersection_size"] / df["query_size"]
    return df.sort_values("p_value")


def build_intersection_table(data: dict[str, pd.DataFrame]) -> pd.DataFrame:
    clinical = data["3_Clinical_Genes"].copy()
    top100 = data["1_Top_100_Genes"]
    top20 = set(data["4_Top_20_Presentation"]["Gene"])
    full = data["7_Full_Dataset"]
    all_ranked = full.groupby("Gene")["Mentions"].sum().sort_values(ascending=False)
    rank_map = {g: i + 1 for i, g in enumerate(all_ranked.index)}

    stress_flat = {g for genes in STRESS_GENES.values() for g in genes}
    rows = []
    for _, r in clinical.iterrows():
        gene = r["Gene"]
        sub = full[full["Gene"] == gene]
        rows.append(
            {
                "Gene": gene,
                "Clinical_Relevance": r["Clinical_Relevance"],
                "Functional_Category": r["Functional Category"],
                "Total_Mentions": int(r["Total Mentions"]),
                "Bibliometric_Rank": int(r["Rank"]),
                "Global_Rank_all_genes": rank_map.get(gene, np.nan),
                "In_Top20": gene in top20,
                "In_Top100": gene in set(top100["Gene"]),
                "In_Full_Dataset": gene in set(full["Gene"]),
                "Is_Stress_Family": gene in stress_flat,
                "CIN": int(sub.loc[sub["Subtype"] == "CIN", "Mentions"].sum()),
                "MSI": int(sub.loc[sub["Subtype"] == "MSI", "Mentions"].sum()),
                "EBV": int(sub.loc[sub["Subtype"] == "EBV", "Mentions"].sum()),
                "Intestinal": int(sub.loc[sub["Subtype"] == "Intestinal", "Mentions"].sum()),
                "Diffuse": int(sub.loc[sub["Subtype"] == "Diffuse", "Mentions"].sum()),
            }
        )
    return pd.DataFrame(rows)


def save_fig(fig: plt.Figure, name: str, *, also_as: list[str] | None = None) -> None:
    for n in [name, *(also_as or [])]:
        fig.savefig(OUT_DIR / f"{n}.png", bbox_inches="tight", facecolor="white", pad_inches=0.08)
        fig.savefig(OUT_DIR / f"{n}.pdf", bbox_inches="tight", facecolor="white", pad_inches=0.08)
    plt.close(fig)


def panel_label(ax, letter: str) -> None:
    ax.text(
        -0.12, 1.06, letter,
        transform=ax.transAxes,
        fontsize=12,
        fontweight="bold",
        va="top",
        ha="left",
    )


def figure_clinical_overview(clinical: pd.DataFrame, cross: pd.DataFrame, data: dict) -> None:
    full = data["7_Full_Dataset"]
    top100 = data["1_Top_100_Genes"]
    total_all = int(full["Mentions"].sum())
    clin_total = int(clinical["Total Mentions"].sum())
    top100_total = int(top100["Total Mentions"].sum())
    nonclin_top100 = int(top100_total - clin_total)
    other = total_all - top100_total

    fig = plt.figure(figsize=(13.5, 9.5))
    gs = GridSpec(2, 2, figure=fig, hspace=0.42, wspace=0.35, height_ratios=[1.15, 1])

    ax_a = fig.add_subplot(gs[0, :])
    d = clinical.sort_values("Total Mentions", ascending=True).copy()
    y = np.arange(len(d))
    colors = [CLIN_COLORS[c] for c in d["Clinical_Relevance"]]
    ax_a.hlines(y, 0, d["Total Mentions"], color=colors, linewidth=2.2, alpha=0.55, zorder=1)
    ax_a.scatter(d["Total Mentions"], y, c=colors, s=90, edgecolors="white", linewidths=0.8, zorder=3)
    for i, (m, rk) in enumerate(zip(d["Total Mentions"], d["Rank"])):
        ax_a.text(m + 5, i, f"#{rk}", va="center", fontsize=7, color="#555555")
    ax_a.set_yticks(y)
    ax_a.set_yticklabels(
        [f"{g}  ({cr.split('(')[0].strip()})" for g, cr in zip(d["Gene"], d["Clinical_Relevance"])],
        fontsize=8,
    )
    ax_a.set_xlabel("PubMed mentions (2016–2026)")
    ax_a.set_title("Clinically actionable gene panel — bibliometric rank", loc="left", pad=10)
    panel_label(ax_a, "A")
    handles = [mpatches.Patch(color=c, label=k) for k, c in CLIN_COLORS.items()]
    ax_a.legend(handles=handles, loc="lower right", frameon=False, fontsize=7.5, ncol=2)

    ax_b = fig.add_subplot(gs[1, 0])
    sizes = [clin_total, nonclin_top100, other]
    labels = [
        f"Clinical panel\n(n=18, {clin_total})",
        f"Other top-100\n(n=82, {nonclin_top100})",
        f"Remaining catalog\n(n={full['Gene'].nunique()-100}, {other})",
    ]
    pie_c = ["#B2182B", "#4575B4", "#D9D9D9"]
    wedges, _, autotexts = ax_b.pie(
        sizes,
        labels=None,
        autopct=lambda p: f"{p:.1f}%" if p > 3 else "",
        colors=pie_c,
        startangle=90,
        pctdistance=0.75,
        wedgeprops=dict(width=0.45, edgecolor="white", linewidth=1.5),
    )
    for t in autotexts:
        t.set_fontsize(8)
        t.set_fontweight("bold")
    ax_b.legend(wedges, labels, loc="center left", bbox_to_anchor=(1.0, 0.5), frameon=False, fontsize=7.5)
    ax_b.set_title("Share of total gene mentions", loc="left")
    panel_label(ax_b, "B")

    ax_c = fig.add_subplot(gs[1, 1])
    metrics = {
        "In top-20": int(cross["In_Top20"].sum()),
        "In top-100": int(cross["In_Top100"].sum()),
        "All 18 clinical": 18,
        "Also in stress\n(HSP/ANXA/S100)": int(cross["Is_Stress_Family"].sum()),
    }
    x = np.arange(len(metrics))
    vals = list(metrics.values())
    bar_c = ["#762A83", "#762A83", "#B2182B", "#969696"]
    bars = ax_c.bar(x, vals, color=bar_c, width=0.55, edgecolor="white")
    ax_c.set_xticks(x)
    ax_c.set_xticklabels(metrics.keys(), fontsize=8)
    ax_c.set_ylim(0, 22)
    ax_c.set_ylabel("Number of genes")
    ax_c.set_title("Clinical panel overlap with bibliometric tiers", loc="left")
    for b, v in zip(bars, vals):
        ax_c.text(b.get_x() + b.get_width() / 2, v + 0.4, str(v), ha="center", fontsize=9, fontweight="bold")
    panel_label(ax_c, "C")

    fig.suptitle(
        "Clinical biomarker panel in the gastric cancer PubMed landscape (2016–2026)",
        fontsize=12,
        fontweight="bold",
        y=1.01,
    )
    save_fig(fig, "Clinical_Fig1_overview")


def figure_subtype_heatmap(cross: pd.DataFrame) -> None:
    subtype_cols = ["CIN", "MSI", "EBV", "Intestinal", "Diffuse"]
    mat = cross.set_index("Gene")[subtype_cols].astype(float)
    mat = mat.loc[mat.sum(axis=1).sort_values(ascending=False).index]
    row_colors = [CLIN_COLORS[cross.set_index("Gene").loc[g, "Clinical_Relevance"]] for g in mat.index]

    fig, (ax_bar, ax_hm) = plt.subplots(
        1, 2, figsize=(11, 7.5), gridspec_kw={"width_ratios": [0.22, 1], "wspace": 0.05}
    )
    totals = mat.sum(axis=1)
    y = np.arange(len(totals))
    ax_bar.barh(y, totals, color=row_colors, edgecolor="white", height=0.72)
    ax_bar.set_yticks(y)
    ax_bar.set_yticklabels(mat.index, fontsize=8)
    ax_bar.invert_yaxis()
    ax_bar.set_xlabel("Total")
    ax_bar.set_title("Σ mentions", fontsize=9, loc="left")
    for i, v in enumerate(totals):
        ax_bar.text(v + 2, i, str(int(v)), va="center", fontsize=7)

    log_mat = np.log1p(mat)
    cmap = sns.color_palette("YlOrRd", as_cmap=True)
    sns.heatmap(
        log_mat,
        ax=ax_hm,
        cmap=cmap,
        linewidths=0.5,
        linecolor="white",
        cbar_kws={"label": "log(1 + mentions)", "shrink": 0.8},
        yticklabels=False,
    )
    ax_hm.set_xlabel("Molecular / histologic subtype")
    ax_hm.set_title("Subtype distribution of clinical biomarkers", loc="left", pad=10)
    for i in range(mat.shape[0]):
        for j in range(mat.shape[1]):
            v = int(mat.iloc[i, j])
            if v > 0:
                ax_hm.text(j + 0.5, i + 0.5, str(v), ha="center", va="center", fontsize=6.5, color="#333333")

    handles = [mpatches.Patch(color=c, label=k.replace(" (MSI)", "")) for k, c in CLIN_COLORS.items()]
    ax_hm.legend(handles=handles, title="Clinical role", loc="upper left", bbox_to_anchor=(1.15, 1.0), frameon=False, fontsize=7)
    save_fig(fig, "Clinical_Fig2_subtype_heatmap")


def figure_go_clinical(go_df: pd.DataFrame) -> None:
    source_style = {
        "GO:BP": ("Biological Process", "#C51B7D"),
        "GO:MF": ("Molecular Function", "#E66101"),
        "GO:CC": ("Cellular Component", "#5E3C99"),
        "KEGG": ("KEGG pathways", "#1B7837"),
        "REAC": ("Reactome", "#2166AC"),
    }
    fig, axes = plt.subplots(1, 3, figsize=(15, 8))
    for ax, src in zip(axes, ["GO:BP", "GO:MF", "GO:CC"]):
        sub = go_df[go_df["source"] == src].head(10).sort_values("neg_log10_p", ascending=True)
        title, color = source_style[src]
        if sub.empty:
            ax.text(0.5, 0.5, "No terms", ha="center", va="center", transform=ax.transAxes)
            ax.set_title(title, loc="left")
            continue
        y = np.arange(len(sub))
        sizes = 70 + sub["intersection_size"] * 32
        ax.scatter(sub["neg_log10_p"], y, s=sizes, c=color, alpha=0.85, edgecolors="white", linewidths=0.6)
        ax.set_yticks(y)
        ax.set_yticklabels([clean_go_label(t) for t in sub["description"]], fontsize=7.5)
        ax.set_xlabel("-log10(p-value)")
        ax.set_title(title, loc="left", pad=8)
        ax.axvline(-np.log10(0.05), color="#AAAAAA", linestyle="--", linewidth=0.7)
        ax.grid(axis="x", alpha=0.2, linestyle="--")
    fig.suptitle(
        "Functional enrichment of the 18-gene clinical biomarker panel (g:Profiler, FDR < 0.05)",
        fontsize=11,
        fontweight="bold",
        y=1.02,
    )
    save_fig(fig, "Clinical_Fig3_GO_enrichment")


def figure_pathways(go_df: pd.DataFrame) -> None:
    kegg = go_df[go_df["source"] == "KEGG"].head(8).sort_values("neg_log10_p", ascending=True)
    reac = go_df[go_df["source"] == "REAC"].head(8).sort_values("neg_log10_p", ascending=True)
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 7.2), gridspec_kw={"wspace": 0.42})
    thresh = -np.log10(0.05)
    for ax, df, panel, title, color in [
        (ax1, kegg, "A", "KEGG pathways", "#1B7837"),
        (ax2, reac, "B", "Reactome pathways", "#2166AC"),
    ]:
        if df.empty:
            continue
        y = np.arange(len(df))
        bars = ax.barh(y, df["neg_log10_p"], color=color, alpha=0.88, height=0.68, edgecolor="white", linewidth=0.6)
        ax.set_yticks(y)
        ax.set_yticklabels([clean_go_label(t, 50) for t in df["description"]], fontsize=8.5)
        ax.set_xlabel("-log10(p-value)", fontsize=9)
        ax.set_title(f"{panel}  {title}", loc="left", fontsize=10, pad=10)
        ax.axvline(thresh, color="#666666", linestyle="--", linewidth=0.9, alpha=0.75)
        ax.set_xlim(left=0)
        ax.grid(axis="x", alpha=0.18, linestyle="--")
        for bar, val in zip(bars, df["neg_log10_p"]):
            ax.text(val + 0.15, bar.get_y() + bar.get_height() / 2, f"{val:.1f}", va="center", fontsize=7, color="#444444")
    fig.suptitle(
        "Pathway enrichment of the 18-gene clinical biomarker panel\n(g:Profiler, Homo sapiens, FDR < 0.05)",
        fontsize=12,
        fontweight="bold",
        y=1.02,
    )
    fig.tight_layout()
    save_fig(fig, "Clinical_Fig4_pathways", also_as=["Figure_Pathway_enrichment"])


def figure_clinical_vs_landscape(clinical: pd.DataFrame, data: dict, cross: pd.DataFrame) -> None:
    full = data["7_Full_Dataset"]
    top100 = data["1_Top_100_Genes"]
    clin_set = set(clinical["Gene"])
    nonclin = top100[~top100["Gene"].isin(clin_set)]

    groups = {
        "Clinical panel\n(18 genes)": clinical.groupby("Clinical_Relevance")["Total Mentions"].sum(),
    }
    fig = plt.figure(figsize=(13, 6))
    gs = GridSpec(1, 2, figure=fig, wspace=0.32)

    ax1 = fig.add_subplot(gs[0, 0])
    cr_order = list(CLIN_COLORS.keys())
    cr_vals = clinical.groupby("Clinical_Relevance")["Total Mentions"].sum().reindex(cr_order)
    bars = ax1.bar(
        range(len(cr_vals)),
        cr_vals.values,
        color=[CLIN_COLORS[k] for k in cr_vals.index],
        edgecolor="white",
        width=0.62,
    )
    ax1.set_xticks(range(len(cr_vals)))
    ax1.set_xticklabels([k.replace(" (MSI)", "\n(MSI)") for k in cr_vals.index], fontsize=7.5)
    ax1.set_ylabel("PubMed mentions")
    ax1.set_title("A  Clinical relevance categories", loc="left")
    for b, v in zip(bars, cr_vals.values):
        ax1.text(b.get_x() + b.get_width() / 2, v + 6, str(int(v)), ha="center", fontsize=8)

    ax2 = fig.add_subplot(gs[0, 1])
    compare = pd.DataFrame(
        {
            "Group": [
                "Clinical panel",
                "Other top-100",
                "HSP family",
                "Annexins",
                "S100 proteins",
                "Full catalog\n(median gene)",
            ],
            "Mentions": [
                int(clinical["Total Mentions"].sum()),
                int(nonclin["Total Mentions"].sum()),
                int(full[full["Gene"].isin(STRESS_GENES["HSP"])]["Mentions"].sum()),
                int(full[full["Gene"].isin(STRESS_GENES["ANXA"])]["Mentions"].sum()),
                int(full[full["Gene"].isin(STRESS_GENES["S100"])]["Mentions"].sum()),
                int(full.groupby("Gene")["Mentions"].sum().median()),
            ],
            "N_genes": [18, 82, len(STRESS_GENES["HSP"]), len(STRESS_GENES["ANXA"]), len(STRESS_GENES["S100"]), 1],
        }
    )
    colors_cmp = ["#B2182B", "#4575B4", "#FD8D3C", "#FD8D3C", "#FD8D3C", "#CCCCCC"]
    x2 = np.arange(len(compare))
    bars2 = ax2.bar(x2, compare["Mentions"], color=colors_cmp, edgecolor="white", width=0.62)
    ax2.set_xticks(x2)
    ax2.set_xticklabels(compare["Group"], fontsize=7.5)
    ax2.set_ylabel("Total mentions")
    ax2.set_title("B  Clinical panel vs proteomic stress markers", loc="left")
    for b, v, n in zip(bars2, compare["Mentions"], compare["N_genes"]):
        ax2.text(b.get_x() + b.get_width() / 2, v + 8, f"{int(v)}\n(n={n})", ha="center", fontsize=7)

    fig.suptitle("Clinical biomarkers dominate actionable literature space", fontsize=11, fontweight="bold", y=1.02)
    save_fig(fig, "Clinical_Fig5_vs_landscape")


def figure_intersection_matrix(cross: pd.DataFrame, data: dict) -> None:
    top20 = set(data["4_Top_20_Presentation"]["Gene"])
    features = {
        "Top-20": cross["Gene"].isin(top20),
        "Top-100": cross["In_Top100"],
        "CIN-enriched\n(>50% CIN)": cross["CIN"] / cross["Total_Mentions"].clip(lower=1) > 0.5,
        "MSI-linked": cross["MSI"] >= 5,
        "Targeted\ntherapy": cross["Clinical_Relevance"] == "Targeted Therapy",
        "Immuno-\ntherapy": cross["Clinical_Relevance"] == "Immunotherapy",
        "DNA repair": cross["Clinical_Relevance"] == "DNA Repair (MSI)",
    }
    mat = pd.DataFrame({k: v.astype(int).values for k, v in features.items()}, index=cross["Gene"])
    mat = mat.loc[cross.sort_values("Total_Mentions", ascending=False)["Gene"]]
    row_colors_series = cross.set_index("Gene").loc[mat.index, "Clinical_Relevance"]

    fig = plt.figure(figsize=(11, 8.5))
    gs = GridSpec(1, 2, figure=fig, width_ratios=[0.04, 1], wspace=0.06)
    ax_strip = fig.add_subplot(gs[0])
    ax = fig.add_subplot(gs[1])

    strip = np.array([[CLIN_COLORS[cr]] for cr in row_colors_series]).reshape(len(mat), 1)
    ax_strip.imshow(strip, aspect="auto")
    ax_strip.set_xticks([])
    ax_strip.set_yticks(np.arange(len(mat)))
    ax_strip.set_yticklabels(mat.index, fontsize=9)
    ax_strip.set_ylabel("Gene", fontsize=9)

    cmap = LinearSegmentedColormap.from_list("bin", ["#FFFFFF", "#B2182B"])
    sns.heatmap(
        mat,
        ax=ax,
        cmap=cmap,
        linewidths=1.0,
        linecolor="#E8E8E8",
        cbar_kws={"label": "Present in category", "ticks": [0, 1], "shrink": 0.55},
        annot=True,
        fmt="d",
        annot_kws={"fontsize": 9, "fontweight": "bold"},
        yticklabels=False,
    )
    ax.set_xlabel("Bibliometric tier / molecular feature", fontsize=9)
    ax.set_title(
        "Intersection of clinical biomarkers with bibliometric tiers\nand molecular subtypes (PubMed 2016–2026)",
        loc="left",
        pad=14,
        fontsize=11,
    )
    handles = [mpatches.Patch(color=c, label=k.replace(" (MSI)", "")) for k, c in CLIN_COLORS.items()]
    ax.legend(
        handles=handles,
        title="Clinical role",
        loc="upper left",
        bbox_to_anchor=(1.18, 1.0),
        frameon=False,
        fontsize=8,
        title_fontsize=8,
    )
    fig.tight_layout()
    save_fig(fig, "Clinical_Fig6_intersection_matrix", also_as=["Figure_Intersection_matrix"])


def figure_rank_scatter(cross: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(9, 6))
    for cr, sub in cross.groupby("Clinical_Relevance"):
        ax.scatter(
            sub["Bibliometric_Rank"],
            sub["Total_Mentions"],
            s=120,
            c=CLIN_COLORS[cr],
            label=cr,
            edgecolors="white",
            linewidths=0.8,
            alpha=0.9,
            zorder=3,
        )
        for _, r in sub.iterrows():
            ax.annotate(
                r["Gene"],
                (r["Bibliometric_Rank"], r["Total_Mentions"]),
                textcoords="offset points",
                xytext=(6, 4),
                fontsize=7.5,
                color="#333333",
            )
    ax.invert_xaxis()
    ax.set_xlabel("Bibliometric rank (1 = most mentioned)")
    ax.set_ylabel("PubMed mentions")
    ax.set_title("Clinical biomarkers in the global rank–mention space", loc="left")
    ax.legend(frameon=False, fontsize=7.5, loc="upper right")
    ax.grid(alpha=0.25, linestyle="--")
    save_fig(fig, "Clinical_Fig7_rank_scatter")


def export_analysis(cross: pd.DataFrame, go_df: pd.DataFrame, clinical: pd.DataFrame, data: dict) -> None:
    cross.to_csv(OUT_DIR / "clinical_intersection_table.csv", index=False)
    go_df.to_csv(OUT_DIR / "clinical_GO_pathway_results.csv", index=False)

    full = data["7_Full_Dataset"]
    summary = {
        "n_clinical_genes": 18,
        "clinical_total_mentions": int(clinical["Total Mentions"].sum()),
        "all_total_mentions": int(full["Mentions"].sum()),
        "clinical_share_pct": round(100 * clinical["Total Mentions"].sum() / full["Mentions"].sum(), 2),
        "clinical_in_top100": int(cross["In_Top100"].sum()),
        "clinical_in_top20": int(cross["In_Top20"].sum()),
        "top_clinical_gene": clinical.loc[clinical["Total Mentions"].idxmax(), "Gene"],
        "dominant_subtype_CIN_pct": round(100 * cross["CIN"].sum() / cross["Total_Mentions"].sum(), 1),
        "top_GO_BP": [clean_go_label(t) for t in go_df[go_df["source"] == "GO:BP"].head(5)["description"]],
        "top_KEGG": [clean_go_label(t) for t in go_df[go_df["source"] == "KEGG"].head(5)["description"]],
    }
    (OUT_DIR / "clinical_analysis_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    md = f"""# Клинический анализ — сводка

## Панель клинически значимых генов (n = 18)

| Показатель | Значение |
|------------|----------|
| Суммарные упоминания | {summary['clinical_total_mentions']} ({summary['clinical_share_pct']}% каталога) |
| В топ-100 | {summary['clinical_in_top100']}/18 (100%) |
| В топ-20 | {summary['clinical_in_top20']}/18 |
| Доминирование CIN-подтипа | {summary['dominant_subtype_CIN_pct']}% упоминаний панели |
| Лидер | {summary['top_clinical_gene']} |

## Категории клинической значимости

"""
    for cr, sub in clinical.groupby("Clinical_Relevance"):
        genes = ", ".join(sub["Gene"].tolist())
        md += f"- **{cr}** ({len(sub)} генов, {int(sub['Total Mentions'].sum())} упоминаний): {genes}\n"

    md += "\n## Топ GO:BP (клиническая панель)\n\n"
    for t in summary["top_GO_BP"]:
        md += f"- {t}\n"

    md += "\n## Топ KEGG\n\n"
    for t in summary["top_KEGG"]:
        md += f"- {t}\n"

    (OUT_DIR / "CLINICAL_ANALYSIS_RU.md").write_text(md, encoding="utf-8")


def main() -> None:
    setup_style()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    data = load_all()
    clinical = data["3_Clinical_Genes"]
    cross = build_intersection_table(data)

    genes = clinical["Gene"].tolist()
    print(f"GO/pathway enrichment for {len(genes)} clinical genes...")
    go_df = run_gprofiler(genes)

    figure_clinical_overview(clinical, cross, data)
    figure_subtype_heatmap(cross)
    figure_go_clinical(go_df)
    figure_pathways(go_df)
    figure_clinical_vs_landscape(clinical, data, cross)
    figure_intersection_matrix(cross, data)
    figure_rank_scatter(cross)
    export_analysis(cross, go_df, clinical, data)

    print(f"Clinical figures saved to {OUT_DIR}")


if __name__ == "__main__":
    main()
