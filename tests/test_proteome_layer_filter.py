"""Фильтр: protein-level proteome, не phospho и не peptide-only."""
from __future__ import annotations

from atlas_agent.discovery.filters import assess_proteome_layer, classify_candidate, default_filter_config


def _classify(title: str, **extra) -> str:
    item = {"title": title, **extra}
    blob = f"{title} {extra.get('description', '')} {extra.get('analytical_fraction', '')}"
    reasons = assess_proteome_layer(item, blob)
    if reasons:
        return "filtered_out"
    out = classify_candidate(item, {"pmids": set(), "accessions": set()}, cfg=default_filter_config())
    return out["verdict"]


def test_reject_phosphoproteomics_title():
    reasons = assess_proteome_layer(
        {"title": "Phosphoproteomic profiling of bladder cancer"},
        "Phosphoproteomic profiling of bladder cancer TMT 10-plex",
    )
    assert reasons
    assert any("phospho" in r.lower() for r in reasons)


def test_reject_phospho_analytical_fraction():
    reasons = assess_proteome_layer(
        {"title": "CPTAC study", "analytical_fraction": "Phosphoproteome"},
        "lung adenocarcinoma TMT 11-plex",
    )
    assert reasons


def test_allow_global_proteome():
    reasons = assess_proteome_layer(
        {"title": "Global proteome profiling of colorectal tumors"},
        "Quantitative proteomics TMT 10-plex protein abundance in tumor tissue",
    )
    assert not reasons


def test_reject_peptide_only():
    reasons = assess_proteome_layer(
        {"title": "Peptide-level turnover measurements in HeLa cells"},
        "Peptide-level turnover measurements enable proteoform dynamics",
    )
    assert reasons
    assert any("peptide" in r.lower() for r in reasons)


def test_allow_protein_groups_despite_peptide_mention():
    reasons = assess_proteome_layer(
        {"title": "TMT quantitative proteomics of tumor tissue"},
        "Protein group quantification after peptide identification TMT 11-plex",
    )
    assert not reasons


def test_combined_proteome_phospho_rejected():
    reasons = assess_proteome_layer(
        {"title": "Integrated proteome and phosphoproteome of HCC"},
        "Integrated proteome and phosphoproteome analyses TMT 10-plex",
    )
    assert reasons
