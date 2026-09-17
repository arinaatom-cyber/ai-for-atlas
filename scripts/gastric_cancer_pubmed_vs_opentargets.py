#!/usr/bin/env python3

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
import pandas as pd
from adjustText import adjust_text
from scipy.stats import spearmanr

PROJECT_ROOT = Path(r"C:\Users\Arina1996\Desktop\Gastric_Cancer_Review")
EXCEL_PATH = PROJECT_ROOT / "tables" / "gastric_cancer_markers_only_clin_study_2016_2026.xlsx"
OUT_DIR = PROJECT_ROOT / "figures" / "opentargets"

OT_THRESHOLD = 0.30
N_LABELS = 20

PRIORITY_COLORS = {"High": "#B2182B", "Medium": "#4575B4", "Low": "#BDBDBD"}
EVIDENCE_COLORS = {
    "clinical": "#B2182B",
    "biomarker": "#E66101",
    "genetic": "#1B7837",
    "literature": "#4575B4",
    "weak/no specific evidence": "#BDBDBD",
}


def setup_style() -> None:
    plt.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.sans-serif": ["Arial", "DejaVu Sans", "Helvetica"],
            "font.size": 9,
            "axes.titlesize": 11,
            "axes.titleweight": "bold",
            "axes.labelsize": 9.5,
            "xtick.labelsize": 8.5,
            "ytick.labelsize": 8.5,
            "legend.fontsize": 8,
            "figure.dpi": 150,
            "savefig.dpi": 300,
            "axes.spines.top": False,
            "axes.spines.right": False,
        }
    )


def load() -> pd.DataFrame:
    df = pd.read_excel(EXCEL_PATH, sheet_name="PubMed_vs_OpenTargets")
    df = df[df["In_OpenTargets"] == "Yes"].copy()
    df["OpenTargets_score"] = pd.to_numeric(df["OpenTargets_score"], errors="coerce")
    df = df.dropna(subset=["OpenTargets_score"])
    df["significant_both"] = df["OpenTargets_score"] >= OT_THRESHOLD
    return df


def pick_labels(df: pd.DataFrame, n: int = N_LABELS) -> set[str]:
    sig = df[df["significant_both"]].copy()
    sig["pub_rank"] = sig["PubMed_mentions"].rank(ascending=False)
    sig["ot_rank"] = sig["OpenTargets_score"].rank(ascending=False)
    sig["combined"] = sig["pub_rank"] + sig["ot_rank"]
    return set(sig.nsmallest(n, "combined")["Gene"])


def save(fig: plt.Figure, name: str) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT_DIR / f"{name}.png", bbox_inches="tight", facecolor="white", pad_inches=0.1)
    fig.savefig(OUT_DIR / f"{name}.pdf", bbox_inches="tight", facecolor="white", pad_inches=0.1)
    plt.close(fig)


def _label_points(ax, df_lab: pd.DataFrame, xcol: str, ycol: str) -> None:
    texts = [
        ax.text(r[xcol], r[ycol], r["Gene"], fontsize=8, fontweight="bold", color="#222222")
        for _, r in df_lab.iterrows()
    ]
    adjust_text(
        texts,
        ax=ax,
        arrowprops=dict(arrowstyle="-", color="#999999", lw=0.6),
        expand_points=(1.4, 1.6),
        force_text=(0.4, 0.6),
    )


def fig_a_score_scatter(df: pd.DataFrame, labels: set[str], n_missing: int) -> None:
    fig, ax = plt.subplots(figsize=(9, 6.5))

    for prio in ["Low", "Medium", "High"]:
        sub = df[df["Priority"] == prio]
        ax.scatter(
            sub["PubMed_mentions"],
            sub["OpenTargets_score"],
            s=70,
            c=PRIORITY_COLORS[prio],
            alpha=0.85,
            edgecolors="white",
            linewidths=0.7,
            label=f"{prio} priority (n={len(sub)})",
            zorder=3,
        )

    ax.axhline(OT_THRESHOLD, color="#666666", linestyle="--", linewidth=0.9, zorder=1)
    ax.text(
        df["PubMed_mentions"].max(), OT_THRESHOLD + 0.012,
        f"Open Targets score = {OT_THRESHOLD:g}",
        ha="right", va="bottom", fontsize=7.5, color="#666666",
    )

    df_lab = df[df["Gene"].isin(labels)]
    _label_points(ax, df_lab, "PubMed_mentions", "OpenTargets_score")

    ax.set_xscale("log")
    ax.set_xlabel("PubMed mentions (2016–2026, log scale)")
    ax.set_ylabel("Open Targets association score")
    ax.set_title("Gastric cancer markers: PubMed literature vs Open Targets evidence")
    ax.set_ylim(-0.03, 0.92)
    rho, p = spearmanr(df["PubMed_mentions"], df["OpenTargets_score"])
    leg = ax.legend(loc="upper left", frameon=False, title=f"Spearman ρ = {rho:.2f}")
    leg.get_title().set_fontsize(8)
    ax.text(
        0.99, 0.02,
        f"Top-100 PubMed genes; {n_missing} absent from Open Targets not shown",
        transform=ax.transAxes, ha="right", va="bottom", fontsize=7, color="#888888",
    )
    save(fig, "Fig_A_PubMed_vs_OpenTargets_score")


def fig_b_quadrant(df: pd.DataFrame, labels: set[str], n_missing: int) -> None:
    fig, ax = plt.subplots(figsize=(9, 6.5))
    x_med = df["PubMed_mentions"].median()
    colors = np.where(df["significant_both"], "#B2182B", "#90A4AE")

    ax.scatter(
        df["PubMed_mentions"], df["OpenTargets_score"],
        s=70, c=colors, alpha=0.85, edgecolors="white", linewidths=0.7, zorder=3,
    )
    ax.axhline(OT_THRESHOLD, color="#666666", linestyle="--", linewidth=0.9)
    ax.axvline(x_med, color="#666666", linestyle=":", linewidth=0.9)

    df_lab = df[df["Gene"].isin(labels)]
    _label_points(ax, df_lab, "PubMed_mentions", "OpenTargets_score")

    ax.set_xscale("log")
    ax.set_xlabel("PubMed mentions (log scale)")
    ax.set_ylabel("Open Targets association score")
    ax.set_title("Validated vs literature-only gastric cancer markers")
    ax.set_ylim(-0.03, 0.92)

    ax.text(0.985, 0.97, "Validated\n(high in both)", transform=ax.transAxes,
            ha="right", va="top", fontsize=8, color="#B2182B", fontweight="bold")
    ax.text(0.015, 0.05, "Under-studied\n(low in both)", transform=ax.transAxes,
            ha="left", va="bottom", fontsize=8, color="#607D8B")

    handles = [
        mpatches.Patch(color="#B2182B", label=f"Significant in both (score ≥ {OT_THRESHOLD:g}, n={int(df['significant_both'].sum())})"),
        mpatches.Patch(color="#90A4AE", label=f"Open Targets sub-threshold (n={int((~df['significant_both']).sum())})"),
    ]
    ax.legend(handles=handles, loc="upper left", frameon=False)
    ax.text(0.99, 0.02, f"{n_missing} genes absent from Open Targets not shown",
            transform=ax.transAxes, ha="right", va="bottom", fontsize=7, color="#888888")
    save(fig, "Fig_B_quadrant_validated")


def fig_c_rank_rank(df: pd.DataFrame, labels: set[str], n_missing: int) -> None:
    d = df.copy()
    d["pub_rank"] = d["PubMed_mentions"].rank(ascending=False, method="min")
    d["ot_rank"] = d["OpenTargets_score"].rank(ascending=False, method="min")

    fig, ax = plt.subplots(figsize=(7.5, 7))
    colors = np.where(d["significant_both"], "#B2182B", "#90A4AE")
    ax.scatter(d["pub_rank"], d["ot_rank"], s=70, c=colors, alpha=0.85,
               edgecolors="white", linewidths=0.7, zorder=3)
    lim = max(d["pub_rank"].max(), d["ot_rank"].max()) + 3
    ax.plot([0, lim], [0, lim], color="#CCCCCC", linewidth=0.8, zorder=1)

    df_lab = d[d["Gene"].isin(labels)]
    _label_points(ax, df_lab, "pub_rank", "ot_rank")

    ax.set_xlim(0, lim)
    ax.set_ylim(0, lim)
    ax.invert_xaxis()
    ax.invert_yaxis()
    ax.set_xlabel("PubMed rank (1 = most mentioned)")
    ax.set_ylabel("Open Targets rank (1 = strongest evidence)")
    ax.set_title("Concordance of PubMed and Open Targets rankings")
    rho, p = spearmanr(d["pub_rank"], d["ot_rank"])
    ax.text(0.02, 0.02, f"Spearman ρ = {rho:.2f}", transform=ax.transAxes,
            ha="left", va="bottom", fontsize=8.5, color="#333333")
    ax.text(0.98, 0.98, f"{n_missing} genes absent from Open Targets not shown",
            transform=ax.transAxes, ha="right", va="top", fontsize=7, color="#888888")
    save(fig, "Fig_C_rank_rank_concordance")


def fig_d_evidence(df: pd.DataFrame, labels: set[str], n_missing: int) -> None:
    fig, ax = plt.subplots(figsize=(9, 6.5))
    order = ["clinical", "biomarker", "genetic", "literature", "weak/no specific evidence"]
    for ev in order:
        sub = df[df["Evidence_type"] == ev]
        if sub.empty:
            continue
        ax.scatter(sub["PubMed_mentions"], sub["OpenTargets_score"], s=70,
                   c=EVIDENCE_COLORS[ev], alpha=0.85, edgecolors="white", linewidths=0.7,
                   label=f"{ev} (n={len(sub)})", zorder=3)
    ax.axhline(OT_THRESHOLD, color="#666666", linestyle="--", linewidth=0.9)

    df_lab = df[df["Gene"].isin(labels)]
    _label_points(ax, df_lab, "PubMed_mentions", "OpenTargets_score")

    ax.set_xscale("log")
    ax.set_xlabel("PubMed mentions (log scale)")
    ax.set_ylabel("Open Targets association score")
    ax.set_title("Gastric cancer markers by Open Targets evidence class")
    ax.set_ylim(-0.03, 0.92)
    ax.legend(loc="upper left", frameon=False, title="Evidence type")
    ax.text(0.99, 0.02, f"{n_missing} genes absent from Open Targets not shown",
            transform=ax.transAxes, ha="right", va="bottom", fontsize=7, color="#888888")
    save(fig, "Fig_D_evidence_type")


def main() -> None:
    setup_style()
    full = pd.read_excel(EXCEL_PATH, sheet_name="PubMed_vs_OpenTargets")
    n_missing = int((full["In_OpenTargets"] != "Yes").sum())
    df = load()
    labels = pick_labels(df)
    print(f"Plotting {len(df)} genes in Open Targets; {n_missing} absent. Labelling {len(labels)}.")

    fig_a_score_scatter(df, labels, n_missing)
    fig_b_quadrant(df, labels, n_missing)
    fig_c_rank_rank(df, labels, n_missing)
    fig_d_evidence(df, labels, n_missing)
    print(f"Saved figures to {OUT_DIR}")


if __name__ == "__main__":
    main()
