#!/usr/bin/env python3

from __future__ import annotations

import json
import textwrap
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
import pandas as pd
import requests
import seaborn as sns
from matplotlib.gridspec import GridSpec

PROJECT_ROOT = Path(r"C:\Users\Arina1996\Desktop\Gastric_Cancer_Review")
EXCEL_PATH = PROJECT_ROOT / "tables" / "gastric_cancer_markers_only_clin_study_2016_2026.xlsx"
OUT_DIR = PROJECT_ROOT / "figures"
TABLE_DIR = PROJECT_ROOT / "tables"
GPROFILER_URL = "https://biit.cs.ut.ee/gprofiler/api/gost/profile/"

COLORS = {
    "CIN": "#2166AC",
    "MSI": "#4393C3",
    "EBV": "#92C5DE",
    "GS": "#D1E5F0",
    "Intestinal": "#1B7837",
    "Diffuse": "#5AAE61",
    "Mixed": "#A6DBA0",
    "Unclassified": "#B8B8B8",
    "BP": "#C51B7D",
    "MF": "#E66101",
    "CC": "#5E3C99",
    "highlight": "#D73027",
    "accent": "#4575B4",
}

STRESS_FAMILIES = {
    "HSP": ["HSP90AA1", "HSP90AB1", "HSPA1A", "HSPA1B", "HSPA8", "HSPB1", "HSPD1", "HSPE1", "HSPH1"],
    "ANXA": ["ANXA1", "ANXA2", "ANXA4", "ANXA5", "ANXA6"],
    "S100": ["S100A2", "S100A4", "S100A6", "S100A7", "S100A8", "S100A9", "S100A10", "S100A11"],
}
TARGET_GENES = ["ERBB2", "CD274", "CLDN18", "EGFR", "MET", "KRAS", "TP53", "MSH2", "MLH1", "PDCD1"]


def setup_style() -> None:
    plt.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.sans-serif": ["Arial", "DejaVu Sans", "Helvetica"],
            "font.size": 9,
            "axes.titlesize": 10,
            "axes.labelsize": 9,
            "xtick.labelsize": 8,
            "ytick.labelsize": 8,
            "legend.fontsize": 8,
            "figure.dpi": 150,
            "savefig.dpi": 300,
            "axes.spines.top": False,
            "axes.spines.right": False,
        }
    )


def load_data() -> dict[str, pd.DataFrame]:
    xl = pd.ExcelFile(EXCEL_PATH)
    return {s: pd.read_excel(EXCEL_PATH, sheet_name=s) for s in xl.sheet_names}


def run_gprofiler(genes: list[str], sources: list[str]) -> pd.DataFrame:
    payload = {
        "organism": "hsapiens",
        "query": genes,
        "sources": sources,
        "user_threshold": 0.05,
        "all_results": False,
        "ordered": False,
    }
    resp = requests.post(GPROFILER_URL, json=payload, timeout=120)
    resp.raise_for_status()
    rows = resp.json().get("result", [])
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows)
    df["neg_log10_p"] = -np.log10(df["p_value"].clip(lower=1e-300))
    df["gene_ratio"] = df["intersection_size"] / df["query_size"]
    df["term"] = df["description"].str.wrap(45)
    return df.sort_values("p_value")


def top_go_terms(df: pd.DataFrame, source: str, n: int = 12) -> pd.DataFrame:
    sub = df[df["source"] == source].head(n).copy()
    sub = sub.sort_values("neg_log10_p", ascending=True)
    return sub


def clean_go_label(text: str, max_len: int = 58) -> str:
    t = str(text).strip().strip('"')
    if t.startswith('"') and t.endswith('"'):
        t = t[1:-1]
    for sep in ['" [', " [GOC:", " [PMID:", " [ISBN:"]:
        if sep in t:
            t = t.split(sep)[0].strip().strip('"')
    if len(t) > max_len:
        t = t[: max_len - 1].rstrip() + "…"
    return t


def wrap_label(text: str, width: int = 42) -> str:
    return "\n".join(textwrap.wrap(clean_go_label(text), width=width))


def plot_go_dotpanel(ax, df: pd.DataFrame, title: str, color: str) -> None:
    if df.empty:
        ax.text(0.5, 0.5, "No significant terms", ha="center", va="center", transform=ax.transAxes)
        ax.set_title(title, fontweight="bold", loc="left")
        return
    y = np.arange(len(df))
    sizes = 60 + df["intersection_size"] * 28
    labels = [clean_go_label(t) for t in df["description"]]
    ax.scatter(
        df["neg_log10_p"],
        y,
        s=sizes,
        c=color,
        alpha=0.82,
        edgecolors="white",
        linewidths=0.6,
        zorder=3,
    )
    ax.set_yticks(y)
    ax.set_yticklabels(labels, fontsize=7.5)
    ax.set_xlabel("-log10(p-value)")
    ax.set_title(title, fontweight="bold", loc="left", pad=8)
    ax.axvline(-np.log10(0.05), color="#999999", linestyle="--", linewidth=0.7)
    ax.grid(axis="x", alpha=0.2, linestyle="--")
    ax.set_xlim(left=0)
    for n, lab in [(5, "5"), (10, "10"), (20, "20")]:
        ax.scatter([], [], s=60 + n * 28, c="gray", alpha=0.45, label=lab)
    ax.legend(title="Genes", loc="lower right", frameon=False, fontsize=7, title_fontsize=7)


def figure1_bibliometric(data: dict[str, pd.DataFrame]) -> None:
    top20 = data["4_Top_20_Presentation"].head(20).iloc[::-1]
    categories = data["2_Category_Summary"].sort_values("Total_Mentions", ascending=False).head(10)
    full = data["7_Full_Dataset"]
    subtype_totals = full.groupby("Subtype")["Mentions"].sum().sort_values(ascending=False)

    fig = plt.figure(figsize=(12, 10))
    gs = GridSpec(2, 2, figure=fig, height_ratios=[1.2, 1], hspace=0.38, wspace=0.32)

    ax_a = fig.add_subplot(gs[0, :])
    colors_a = [COLORS["highlight"] if g in TARGET_GENES else COLORS["accent"] for g in top20["Gene"]]
    ax_a.barh(top20["Gene"], top20["Total Mentions"], color=colors_a, edgecolor="white", height=0.72)
    ax_a.set_xlabel("PubMed mentions (2016–2026)")
    ax_a.set_title("A  Top-20 most frequently mentioned genes", fontweight="bold", loc="left")
    for i, (v, cat) in enumerate(zip(top20["Total Mentions"], top20["Functional Category"])):
        ax_a.text(v + 6, i, cat, va="center", fontsize=6.5, color="#555555")

    ax_b = fig.add_subplot(gs[1, 0])
    labels = subtype_totals.index.tolist()
    vals = subtype_totals.values
    pie_colors = [COLORS.get(l, "#999999") for l in labels]
    wedges, texts, autotexts = ax_b.pie(
        vals,
        labels=None,
        autopct=lambda p: f"{p:.1f}%" if p > 4 else "",
        startangle=90,
        colors=pie_colors,
        pctdistance=0.78,
        wedgeprops=dict(width=0.42, edgecolor="white", linewidth=1.2),
    )
    for t in autotexts:
        t.set_fontsize(7)
    ax_b.legend(
        wedges,
        [f"{l} ({v})" for l, v in zip(labels, vals)],
        loc="center left",
        bbox_to_anchor=(1.02, 0.5),
        frameon=False,
        fontsize=7,
    )
    ax_b.set_title("B  Mentions by molecular / histologic subtype", fontweight="bold", loc="left")

    ax_c = fig.add_subplot(gs[1, 1])
    cat_colors = sns.color_palette("Spectral", n_colors=len(categories))[::-1]
    ax_c.barh(
        categories["Functional Category"][::-1],
        categories["Total_Mentions"][::-1],
        color=cat_colors,
        edgecolor="white",
    )
    ax_c.set_xlabel("Total mentions")
    ax_c.set_title("C  Top functional categories", fontweight="bold", loc="left")
    ax_c.tick_params(axis="y", labelsize=7)

    fig.suptitle(
        "Bibliometric landscape of gastric cancer molecular markers\n(PubMed clinical studies, 2016–2026)",
        fontsize=11,
        fontweight="bold",
        y=1.01,
    )
    fig.savefig(OUT_DIR / "Figure1_bibliometric_overview.png", bbox_inches="tight", facecolor="white")
    fig.savefig(OUT_DIR / "Figure1_bibliometric_overview.pdf", bbox_inches="tight", facecolor="white")
    plt.close(fig)


def figure2_go_enrichment(go_df: pd.DataFrame, n_genes: int) -> None:
    fig, axes = plt.subplots(1, 3, figsize=(15, 8.5))
    panels = [
        ("GO:BP", "A  Biological Process", COLORS["BP"]),
        ("GO:MF", "B  Molecular Function", COLORS["MF"]),
        ("GO:CC", "C  Cellular Component", COLORS["CC"]),
    ]
    for ax, (src, title, color) in zip(axes, panels):
        plot_go_dotpanel(ax, top_go_terms(go_df, src, 12), title, color)
    fig.suptitle(
        f"Gene Ontology enrichment of top bibliometric gene set (n = {n_genes})",
        fontsize=11,
        fontweight="bold",
        y=1.02,
    )
    fig.savefig(OUT_DIR / "Figure2_GO_enrichment.png", bbox_inches="tight", facecolor="white")
    fig.savefig(OUT_DIR / "Figure2_GO_enrichment.pdf", bbox_inches="tight", facecolor="white")
    plt.close(fig)


def figure3_subtype_heatmap(data: dict[str, pd.DataFrame]) -> None:
    top_genes = data["1_Top_100_Genes"].head(25)["Gene"].tolist()
    full = data["7_Full_Dataset"]
    sub = full[full["Gene"].isin(top_genes)].copy()
    pivot = sub.pivot_table(index="Gene", columns="Subtype", values="Mentions", fill_value=0, aggfunc="sum")
    order = sub.groupby("Gene")["Mentions"].sum().sort_values(ascending=False).index
    pivot = pivot.loc[order]
    col_order = ["CIN", "MSI", "EBV", "GS", "Intestinal", "Diffuse", "Mixed", "Unclassified"]
    pivot = pivot[[c for c in col_order if c in pivot.columns]]

    fig, ax = plt.subplots(figsize=(9, 8))
    log_data = np.log1p(pivot)
    sns.heatmap(
        log_data,
        cmap="YlOrRd",
        linewidths=0.4,
        linecolor="white",
        cbar_kws={"label": "log(1 + mentions)"},
        ax=ax,
    )
    ax.set_title("Spatial distribution of top-25 gene mentions across tumor subtypes", fontweight="bold", loc="left")
    ax.set_xlabel("Subtype")
    ax.set_ylabel("Gene")
    fig.savefig(OUT_DIR / "Figure3_subtype_heatmap.png", bbox_inches="tight", facecolor="white")
    fig.savefig(OUT_DIR / "Figure3_subtype_heatmap.pdf", bbox_inches="tight", facecolor="white")
    plt.close(fig)


def figure4_research_gap(data: dict[str, pd.DataFrame]) -> None:
    full = data["7_Full_Dataset"]
    top100 = set(data["1_Top_100_Genes"]["Gene"])

    def family_mentions(gene_list: list[str]) -> int:
        return int(full[full["Gene"].isin(gene_list)]["Mentions"].sum())

    groups = {
        "RTK / target\n(ERBB2, EGFR, MET…)": family_mentions(["ERBB2", "EGFR", "MET", "KRAS", "CLDN18"]),
        "Immune checkpoints\n(CD274, PDCD1…)": family_mentions(["CD274", "PDCD1", "PDCD1LG2", "CTLA4"]),
        "DNA repair / MSI\n(MLH1, MSH2…)": family_mentions(["MLH1", "MSH2", "MSH6", "PMS2"]),
        "HSP family": family_mentions(STRESS_FAMILIES["HSP"]),
        "Annexins (ANXA)": family_mentions(STRESS_FAMILIES["ANXA"]),
        "S100 calcium-binding": family_mentions(STRESS_FAMILIES["S100"]),
    }
    in_top = {
        "RTK / target\n(ERBB2, EGFR, MET…)": len([g for g in ["ERBB2", "EGFR", "MET", "KRAS", "CLDN18"] if g in top100]),
        "Immune checkpoints\n(CD274, PDCD1…)": len([g for g in ["CD274", "PDCD1", "PDCD1LG2", "CTLA4"] if g in top100]),
        "DNA repair / MSI\n(MLH1, MSH2…)": len([g for g in ["MLH1", "MSH2", "MSH6", "PMS2"] if g in top100]),
        "HSP family": len([g for g in STRESS_FAMILIES["HSP"] if g in top100]),
        "Annexins (ANXA)": len([g for g in STRESS_FAMILIES["ANXA"] if g in top100]),
        "S100 calcium-binding": len([g for g in STRESS_FAMILIES["S100"] if g in top100]),
    }

    labels = list(groups.keys())
    mentions = list(groups.values())
    colors = [COLORS["accent"], COLORS["accent"], COLORS["accent"], COLORS["highlight"], COLORS["highlight"], COLORS["highlight"]]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 5), gridspec_kw={"width_ratios": [1.4, 1]})
    x = np.arange(len(labels))
    bars = ax1.bar(x, mentions, color=colors, edgecolor="white", width=0.65)
    ax1.set_xticks(x)
    ax1.set_xticklabels(labels, fontsize=7.5)
    ax1.set_ylabel("Total PubMed mentions")
    ax1.set_title("A  Clinical literature focus by marker class", fontweight="bold", loc="left")
    for b, v in zip(bars, mentions):
        ax1.text(b.get_x() + b.get_width() / 2, v + 3, str(v), ha="center", fontsize=8)

    top_vals = [in_top[k] for k in labels]
    ax2.barh(labels, top_vals, color=colors, edgecolor="white", height=0.65)
    ax2.set_xlabel("Genes in top-100 list")
    ax2.set_title("B  Representation among top-100 genes", fontweight="bold", loc="left")
    ax2.set_xlim(0, 6)
    for i, v in enumerate(top_vals):
        ax2.text(v + 0.08, i, str(v), va="center", fontsize=8)

    fig.suptitle(
        "Research gap: targetable vs stress/inflammation proteomic markers",
        fontsize=11,
        fontweight="bold",
    )
    fig.tight_layout()
    fig.savefig(OUT_DIR / "Figure4_research_gap.png", bbox_inches="tight", facecolor="white")
    fig.savefig(OUT_DIR / "Figure4_research_gap.pdf", bbox_inches="tight", facecolor="white")
    plt.close(fig)


def figure5_go_bubble_combined(go_df: pd.DataFrame) -> None:
    parts = [go_df[go_df["source"] == src].nsmallest(8, "p_value") for src in ["GO:BP", "GO:MF", "GO:CC"]]
    top = pd.concat(parts, ignore_index=True).sort_values("neg_log10_p", ascending=True)
    source_labels = {"GO:BP": "Biological Process", "GO:MF": "Molecular Function", "GO:CC": "Cellular Component"}
    top["ontology"] = top["source"].map(source_labels)
    top["label"] = top.apply(
        lambda r: f"[{r['ontology'][:2]}] {clean_go_label(r['description'], 52)}", axis=1
    )

    fig, ax = plt.subplots(figsize=(10, 10))
    palette = {"Biological Process": COLORS["BP"], "Molecular Function": COLORS["MF"], "Cellular Component": COLORS["CC"]}
    for ont, sub in top.groupby("ontology"):
        y = sub["label"].tolist()
        y_pos = [top["label"].tolist().index(l) for l in y]
        ax.scatter(
            sub["neg_log10_p"],
            y_pos,
            s=sub["intersection_size"] * 45,
            c=palette[ont],
            alpha=0.8,
            edgecolors="white",
            linewidths=0.7,
            label=ont,
        )
    ax.set_yticks(range(len(top)))
    ax.set_yticklabels(top["label"], fontsize=7.5)
    ax.set_xlabel("-log10(p-value)")
    ax.set_title("GO enrichment of gastric cancer bibliometric gene signature", fontweight="bold", loc="left")
    ax.axvline(-np.log10(0.05), color="#888888", linestyle="--", linewidth=0.8, alpha=0.7)
    ax.legend(title="Ontology", frameon=False, loc="lower right")
    ax.grid(axis="x", alpha=0.2, linestyle="--")
    fig.tight_layout()
    fig.savefig(OUT_DIR / "Figure5_GO_combined_bubble.png", bbox_inches="tight", facecolor="white")
    fig.savefig(OUT_DIR / "Figure5_GO_combined_bubble.pdf", bbox_inches="tight", facecolor="white")
    plt.close(fig)


def export_tables(go_df: pd.DataFrame, data: dict[str, pd.DataFrame], gene_list: list[str]) -> None:
    TABLE_DIR.mkdir(parents=True, exist_ok=True)
    go_df.to_csv(TABLE_DIR / "GO_enrichment_results.csv", index=False)
    summary = {
        "n_genes_analyzed": len(gene_list),
        "n_go_terms_significant": len(go_df),
        "top_bp": go_df[go_df["source"] == "GO:BP"].head(5)["description"].tolist(),
        "top_mf": go_df[go_df["source"] == "GO:MF"].head(5)["description"].tolist(),
        "top_cc": go_df[go_df["source"] == "GO:CC"].head(5)["description"].tolist(),
    }
    (TABLE_DIR / "GO_summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

    full = data["7_Full_Dataset"]
    total_mentions = int(full["Mentions"].sum())
    stress_genes = set(STRESS_FAMILIES["HSP"] + STRESS_FAMILIES["ANXA"] + STRESS_FAMILIES["S100"])
    stress_mentions = int(full[full["Gene"].isin(stress_genes)]["Mentions"].sum())
    all_genes_mentions = int(full.groupby("Gene")["Mentions"].sum().sum())
    pct = 100 * stress_mentions / total_mentions
    stats = pd.DataFrame(
        [
            {"metric": "total_mentions", "value": total_mentions},
            {"metric": "stress_family_mentions", "value": stress_mentions},
            {"metric": "stress_family_pct", "value": round(pct, 2)},
            {"metric": "unique_genes", "value": full["Gene"].nunique()},
        ]
    )
    stats.to_csv(TABLE_DIR / "manuscript_stats.csv", index=False)


def main() -> None:
    setup_style()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    data = load_data()

    gene_list = data["1_Top_100_Genes"]["Gene"].dropna().astype(str).unique().tolist()
    print(f"Running GO enrichment for {len(gene_list)} genes...")

    go_df = run_gprofiler(gene_list, ["GO:BP", "GO:MF", "GO:CC"])
    print(f"Significant GO terms: {len(go_df)}")

    figure1_bibliometric(data)
    figure2_go_enrichment(go_df, len(gene_list))
    figure3_subtype_heatmap(data)
    figure4_research_gap(data)
    figure5_go_bubble_combined(go_df)
    export_tables(go_df, data, gene_list)

    print(f"Figures saved to {OUT_DIR}")


if __name__ == "__main__":
    main()
