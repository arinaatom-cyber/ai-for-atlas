"""Reproducibility manifest for Discovery scans (Methods / supplementary)."""
from __future__ import annotations

import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from atlas_agent.discovery.ai_agents import agents_for_site
from atlas_agent.discovery.pipeline_methods import pipeline_for_manifest
from atlas_agent.discovery.search_limits import optional_cap

_REPO_ROOT = Path(__file__).resolve().parents[2]


def _git_head() -> str:
    try:
        r = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=_REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=8,
            check=False,
        )
        if r.returncode == 0:
            return (r.stdout or "").strip()
    except (OSError, subprocess.SubprocessError):
        pass
    return ""


def _llm_lock(cfg: dict[str, Any] | None) -> dict[str, Any]:
    llm = (cfg or {}).get("llm") or {}
    provider = llm.get("provider", "auto")
    model = llm.get("model")
    prefer_cloud = bool(llm.get("prefer_cloud", True))
    resolved = ""
    try:
        from atlas_agent.llm_client import resolve_engine

        resolved = resolve_engine(
            str(provider),
            llm.get("base_url"),
            prefer_cloud=prefer_cloud,
            model=model,
        )
    except Exception:
        resolved = ""
    return {
        "provider": provider,
        "model": model,
        "prefer_cloud": prefer_cloud,
        "base_url": llm.get("base_url"),
        "resolved_engine": resolved,
        "enabled": llm.get("enabled", True),
    }


def _source_label(item: dict[str, Any]) -> str:
    acc = str(item.get("accession") or item.get("project_accession") or "").upper()
    src = str(item.get("source") or "").lower()
    if acc.startswith("PDC") or src.startswith("pdc"):
        return "pdc"
    if acc.startswith("PXD") or src.startswith("pride"):
        return "pride"
    if acc.startswith("MSV") or "massive" in src:
        return "massive"
    if acc.startswith("IPX") or "iprox" in src:
        return "iprox"
    return src or "other"


def _tmt_plex_unspecified_by_source(report: dict[str, Any]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for key in (
        "candidates",
        "new_projects",
        "filtered_out",
        "rejected_material",
        "repository_manual",
        "manual_check",
    ):
        for it in report.get(key) or []:
            reasons = " ".join(str(x) for x in (it.get("filter_reasons") or []))
            if not (
                it.get("tmt_plex_unspecified")
                or it.get("tmt_plex_unspecified_pdc")
                or "tmt_plex_unspecified" in reasons
            ):
                continue
            src = _source_label(it)
            counts[src] = counts.get(src, 0) + 1
    return counts


def _possible_pmid_matches(report: dict[str, Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for key in (
        "candidates",
        "new_projects",
        "filtered_out",
        "rejected_material",
        "repository_manual",
        "manual_check",
    ):
        for it in report.get(key) or []:
            hits = it.get("possible_pmid_match") or []
            if not hits:
                continue
            acc = str(it.get("accession") or it.get("project_accession") or "")
            title = str(it.get("title") or "")[:160]
            sig = f"{acc}|{title}|{','.join(hits)}"
            if sig in seen:
                continue
            seen.add(sig)
            out.append({
                "accession": acc,
                "title": title,
                "possible_pmid_match": hits,
                "verdict": it.get("verdict"),
            })
    return out[:80]


def build_methods_manifest(report: dict[str, Any], cfg: dict[str, Any] | None = None) -> dict[str, Any]:
    disc = (cfg or {}).get("discovery") or {}
    s = report.get("summary") or {}
    st = s.get("source_stats") or {}
    da = s.get("data_availability") or {}
    filters = report.get("filters_applied") or disc.get("filters") or {}
    llm_lock = _llm_lock(cfg)

    return {
        "pipeline_name": "Atlas Discovery Agent",
        "generated_at": report.get("generated_at") or datetime.now(timezone.utc).isoformat(),
        "pipeline_git_commit": _git_head(),
        "llm_locked": llm_lock,
        "ai_agents": agents_for_site(cfg),
        "pipeline": pipeline_for_manifest(),
        "catalog_policy": report.get("policy") or {},
        "inclusion_criteria": {
            "organism": "Homo sapiens only (allow-list: human / Homo sapiens / patient / known human cancer cell line)",
            "quantification": "TMT/isobaric >6-plex (reject TMT6 / ≤6-plex; TMT18 allowed)",
            "omics_layer": "Global protein-level proteome (reject phospho-only, peptide-only)",
            "material": "Human tissue (tumor / adjacent / normal) or human cancer cell lines (reject plasma/serum/urine-only)",
            "literature": "Europe PMC semantic screening; repository IDs from data availability only; preprints tagged (is_preprint) and not auto-excluded",
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
        "pdc_human_policy": (
            "PDC uiStudySummary has no organism field; studies are assumed human "
            "per PDC/CPTAC clinical program scope unless metadata names a non-human organism."
        ),
        "search_window": {
            "year_from": disc.get("year_from"),
            "year_to": disc.get("year_to"),
            "note": (
                "Automated weekly monitoring covers repository deposits from year_from. "
                "Earlier catalog entries were curated at initial atlas assembly."
            ),
        },
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
            "abstract_llm_max": disc.get("abstract_llm_max", 25),
            "atlas_fit_yes": st.get("abstract_atlas_fit_yes"),
            "atlas_fit_maybe": st.get("abstract_atlas_fit_maybe"),
            "literature_resolved": st.get("literature_resolved"),
            "semantic_from_abstract": st.get("semantic_from_abstract"),
            "regex_only_publications": st.get("regex_only_publications") or [],
            "preprints": st.get("literature_preprints"),
            "peer_reviewed": st.get("literature_peer_reviewed"),
        },
        "dedup": {
            "exact_id_pmid_doi": "already_in_catalog (all PXD/PDC/MSV/IPX in the Project ID cell)",
            "jaccard_hint": 0.18,
            "jaccard_close_match": 0.72,
            "close_match_verdict": "requires_manual_check (not auto-excluded)",
        },
        "tmt_plex_unspecified_by_source": _tmt_plex_unspecified_by_source(report),
        "pdc_tmt_plex_unspecified": st.get("pdc_tmt_plex_unspecified", 0),
        "failed_source_requests": st.get("failed_source_requests") or {},
        "possible_pmid_match": _possible_pmid_matches(report),
        "data_availability_gate": da,
        "confidence_model": "Rule-based tiers A–D (not calibrated LLM probability)",
        "catalog_read_only": True,
        "catalog_runtime": "data/projects.csv",
        "catalog_workbook": "project of Proteomics.xlsx (TMT ATLAS)",
    }
