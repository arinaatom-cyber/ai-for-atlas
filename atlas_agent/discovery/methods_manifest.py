"""Reproducibility manifest for Discovery scans (Methods / supplementary)."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from atlas_agent.discovery.ai_agents import agents_for_site
from atlas_agent.discovery.pipeline_methods import pipeline_for_manifest
from atlas_agent.discovery.search_limits import optional_cap


def build_methods_manifest(report: dict[str, Any], cfg: dict[str, Any] | None = None) -> dict[str, Any]:
    disc = (cfg or {}).get("discovery") or {}
    s = report.get("summary") or {}
    st = s.get("source_stats") or {}
    da = s.get("data_availability") or {}
    filters = report.get("filters_applied") or disc.get("filters") or {}

    return {
        "pipeline_name": "Atlas Discovery Agent",
        "generated_at": report.get("generated_at") or datetime.now(timezone.utc).isoformat(),
        "ai_agents": agents_for_site(cfg),
        "pipeline": pipeline_for_manifest(),
        "catalog_policy": report.get("policy") or {},
        "inclusion_criteria": {
            "organism": "Homo sapiens only (reject mouse/rat/chicken and mixed)",
            "quantification": "TMT/isobaric >6-plex (reject TMT6 / ≤6-plex; TMT18 allowed)",
            "omics_layer": "Global protein-level proteome (reject phospho-only, peptide-only)",
            "material": "Human tissue (tumor / adjacent / normal) or human cancer cell lines (reject plasma/serum/urine-only)",
            "literature": "Europe PMC semantic screening; repository IDs from data availability only",
        },
        "exclusion_criteria": [
            "Non-human, mixed, or xenograft-only",
            "TMT6 or ≤6-plex",
            "Plasma / serum / urine / blood-only (need tissue or cell line)",
            "Phosphoproteomics-only emphasis",
            "Peptide-level quantification only",
            "Review / methods / software papers without cohort data",
            "Phospho-only or RAW-only repository files",
        ],
        "search_config": {
            "year_from": disc.get("year_from"),
            "year_to": disc.get("year_to"),
            "pride_max": optional_cap(disc.get("pride_max")),
            "massive_max": optional_cap(disc.get("massive_max")),
            "iprox_max": optional_cap(disc.get("iprox_max")),
            "publications_max": optional_cap(disc.get("publications_max")),
            "repo_unlimited": not any(
                optional_cap(disc.get(k)) for k in ("pride_max", "massive_max", "iprox_max")
            ),
            "abstract_llm": disc.get("abstract_llm", True),
            "abstract_llm_max": disc.get("abstract_llm_max", 25),
            "abstract_resolve_accessions": disc.get("abstract_resolve_accessions", False),
            "abstract_semantic_resolve": disc.get("abstract_semantic_resolve", False),
            "strict_sample_design": disc.get("strict_sample_design", True),
            "search_mode": disc.get("search_mode", "professional"),
        },
        "filters_applied": filters,
        "funnel": {
            "raw_novel_repos": st.get("pride_v3_search", 0) + st.get("pdc_uiStudySummary", 0),
            "candidates": s.get("candidates"),
            "manual_check": s.get("manual_check"),
            "rejected_material": s.get("rejected_material"),
            "filtered_out": s.get("filtered_out"),
            "already_in_catalog": s.get("already_in_catalog"),
        },
        "literature_screening": {
            "publications_scanned": st.get("publications_scanned"),
            "abstract_llm_read": st.get("abstract_llm_read"),
            "abstract_regex_only": st.get("abstract_regex_only"),
            "atlas_fit_yes": st.get("abstract_atlas_fit_yes"),
            "atlas_fit_maybe": st.get("abstract_atlas_fit_maybe"),
            "literature_resolved": st.get("literature_resolved"),
            "semantic_from_abstract": st.get("semantic_from_abstract"),
        },
        "data_availability_gate": da,
        "confidence_model": "Rule-based tiers A–D (not calibrated LLM probability)",
        "catalog_read_only": True,
    }
