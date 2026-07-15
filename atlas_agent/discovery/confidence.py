"""Rule-calibrated confidence tiers (Nature-style) — not raw LLM floats."""
from __future__ import annotations

from typing import Any

from atlas_agent.discovery.fit_rules import (
    cohort_verdict,
    is_cohort_excluded,
    literature_verdict,
    project_verdict,
)


def _bullets(*parts: str) -> list[str]:
    return [p for p in parts if p]


def project_confidence(item: dict[str, Any]) -> tuple[str, str, list[str]]:
    """Tier A–D for repository projects."""
    da = item.get("data_availability") or {}
    layer = da.get("omics_layer") or ""
    status = da.get("status") or ""
    design = item.get("sample_design") or "unknown"
    plex = item.get("inferred_plex") or item.get("tmt_label") or ""
    human = item.get("human") is not False
    qc = item.get("qc_status") or ""
    reasons = list(item.get("filter_reasons") or [])[:4]

    if status in ("phospho_table", "no_files", "raw_only") or layer == "phospho":
        return (
            "D",
            "tier-d",
            _bullets("No protein-level table", reasons[0] if reasons else ""),
        )
    if layer == "mixed":
        return (
            "B",
            "tier-b",
            _bullets("Mixed protein+phospho files — manual matrix check", f"design: {design}"),
        )
    if status == "quant_table" and human and qc == "candidate" and design != "unknown":
        return (
            "A",
            "tier-a",
            _bullets("Protein quant table confirmed", f"TMT {plex}" if plex else "TMT detected", f"design: {design}"),
        )
    if status in ("quant_table", "local_mirror", "maybe_table"):
        return (
            "B",
            "tier-b",
            _bullets("Quant files present", f"design: {design}", reasons[0] if reasons else "verify sample labels"),
        )
    vlabel, _, _ = project_verdict(item)
    if vlabel == "Exclude":
        return ("D", "tier-d", _bullets("Fails atlas file criteria", reasons[0] if reasons else ""))
    return ("C", "tier-c", _bullets("Needs manual review", reasons[0] if reasons else ""))


def literature_confidence(item: dict[str, Any], *, has_accession: bool) -> tuple[str, str, list[str]]:
    fit = str(item.get("atlas_fit") or (item.get("abstract_ai") or {}).get("atlas_fit") or "").lower()
    reason = (item.get("abstract_ai") or {}).get("exclusion_reason") or ""
    reader = item.get("abstract_reader") or (item.get("abstract_ai") or {}).get("reader") or ""
    evidence = list((item.get("abstract_ai") or {}).get("semantic_evidence") or [])[:3]
    resolved = item.get("accessions_resolved") or (item.get("abstract_ai") or {}).get("accessions") or {}

    if fit == "no" or reason:
        return ("D", "tier-d", _bullets(reason or "Atlas exclusion", reader and f"reader: {reader}"))
    if has_accession and any(resolved.get(k) for k in ("PXD", "PDC", "MSV", "IPX")):
        return ("A", "tier-a", _bullets("Repository ID from data availability", *evidence))
    if fit == "yes" and evidence:
        return ("C", "tier-c", _bullets("LLM yes — no verified PXD/PDC", *evidence, reader and f"reader: {reader}"))
    if fit == "maybe":
        return ("C", "tier-c", _bullets("LLM maybe — literature watch", *evidence))
    return ("C", "tier-c", _bullets("Literature surveillance", reader and f"reader: {reader}"))


def cohort_confidence(item: dict[str, Any]) -> tuple[str, str, list[str]]:
    if is_cohort_excluded(str(item.get("title") or ""), str(item.get("abstract") or "")):
        return ("D", "tier-d", _bullets("Review / software / narrative"))
    n = item.get("patient_n") or 0
    if item.get("tmt_detected") and n >= 50:
        return ("B", "tier-b", _bullets(f"N≈{n}", "TMT mention", "Cohort watch — not a new repo ID"))
    if n >= 100:
        return ("C", "tier-c", _bullets(f"Large cohort N≈{n}", "No TMT confirmation"))
    vlabel, _, vtitle = cohort_verdict(item)
    if vlabel == "Exclude":
        return ("D", "tier-d", _bullets(vtitle))
    return ("C", "tier-c", _bullets(vtitle or "Cohort literature watch"))


def attach_confidence(item: dict[str, Any], *, kind: str, has_accession: bool = False) -> None:
    if kind == "project":
        tier, css, bullets = project_confidence(item)
    elif kind == "cohort":
        tier, css, bullets = cohort_confidence(item)
    else:
        tier, css, bullets = literature_confidence(item, has_accession=has_accession)
    item["confidence_tier"] = tier
    item["confidence_css"] = css
    item["confidence_evidence"] = bullets
