"""Atlas-trained fit rules: exclusions (mouse, TMT6, reviews) + honest display labels."""
from __future__ import annotations

import re
from typing import Any

from atlas_agent.discovery.filters import PHOSPHOPROTEOMICS

GARBAGE_SUMMARY = re.compile(
    r"json\s*schema|this\s+json\s+schema|reply\s+with\s+only\s+valid\s+json",
    re.I,
)

REVIEW_METHODS_TITLE = re.compile(
    r"\b(review|perspective|editorial|protocol\s+paper|narrative\s+review|"
    r"benchmark|tutorial|guide\s+to|methods?\s+paper|software|toolbox|platform|"
    r"integrator|workflow|explorer|scanner)\b",
    re.I,
)

MOUSE_OR_XENO = re.compile(
    r"\b(mouse|mice|murine|rat\b|xenograft|pdx-only|organoid-only)\b",
    re.I,
)


def sanitize_summary(text: object) -> str:
    s = str(text or "").strip()
    if not s or GARBAGE_SUMMARY.search(s):
        return ""
    return s[:320]


def is_non_study_literature(title: str, abstract: str = "") -> bool:
    """Methods, reviews, software — not atlas dataset candidates."""
    t = title or ""
    blob = f"{t} {abstract or ''}"
    if REVIEW_METHODS_TITLE.search(t):
        if not re.search(r"\b(\d+\s+patients?|clinical\s+cohort|multicenter)\b", blob, re.I):
            return True
    if re.search(r"\b(single-cell|scproteomics|microfluidic\s+platform)\b", t, re.I):
        if not re.search(r"\b(cohort|patients?)\b", blob, re.I):
            return True
    return False


def is_cohort_excluded(title: str, abstract: str = "") -> bool:
    t = title or ""
    blob = f"{t} {abstract or ''}"
    if REVIEW_METHODS_TITLE.search(t):
        return True
    if re.search(r"\b(narrative\s+review|artificial\s+intelligence\s+and\s+multi-omics)\b", blob, re.I):
        return True
    return False


def apply_literature_exclusions(item: dict[str, Any]) -> dict[str, Any]:
    """Downgrade atlas_fit when atlas exclusion rules fire (mouse, review, phospho-only text)."""
    title = str(item.get("title") or "")
    abstract = str(item.get("abstract") or "")
    ai = dict(item.get("abstract_ai") or {})
    blob = f"{title} {abstract}"

    if MOUSE_OR_XENO.search(blob) and not re.search(r"\bhuman\b", blob, re.I):
        ai["atlas_fit"] = "no"
        ai["exclusion_reason"] = "non-human / xenograft"
    elif is_non_study_literature(title, abstract):
        ai["atlas_fit"] = "no"
        ai["exclusion_reason"] = "review / methods / software"
    elif PHOSPHOPROTEOMICS.search(blob) and not re.search(
        r"\b(proteome|protein[- ]level|global\s+proteom)\b", blob, re.I
    ):
        ai["atlas_fit"] = "no"
        ai["exclusion_reason"] = "phospho-only emphasis"

    for key in ("summary_en", "summary_ru"):
        if key in ai:
            ai[key] = sanitize_summary(ai.get(key))
    if ai.get("summary_ru") and not ai.get("summary_en"):
        ai["summary_en"] = sanitize_summary(ai["summary_ru"])

    item["abstract_ai"] = ai
    if ai.get("atlas_fit"):
        item["atlas_fit"] = ai["atlas_fit"]
    item["atlas_fit_score"] = None
    return item


def project_verdict(item: dict[str, Any]) -> tuple[str, str, str]:
    """label, badge class, title tooltip."""
    da = item.get("data_availability") or {}
    layer = da.get("omics_layer") or ""
    status = da.get("status") or ""
    if layer == "mixed":
        return ("Review", "badge-warn", "Protein + phospho files — manual check")
    if status == "quant_table":
        return ("Candidate", "badge-ok", "Protein-level table in repository")
    if status in ("phospho_table", "raw_only", "no_files"):
        return ("Exclude", "badge-bad", "No suitable protein table")
    return ("Review", "badge-warn", "Needs manual review")


def literature_verdict(item: dict[str, Any], *, has_accession: bool) -> tuple[str, str, str]:
    fit = str(item.get("atlas_fit") or (item.get("abstract_ai") or {}).get("atlas_fit") or "").lower()
    reason = (item.get("abstract_ai") or {}).get("exclusion_reason") or ""
    if fit == "no" or reason:
        return ("Exclude", "badge-bad", reason or "Atlas exclusion rules")
    if has_accession:
        return ("Watch", "badge-warn", "Has ID — verify in catalog")
    if fit == "maybe":
        return ("Watch", "badge-warn", "LLM maybe — no repository ID")
    if fit == "yes":
        return ("Watch", "badge-warn", "LLM yes — no PXD/PDC; find dataset manually")
    return ("Watch", "badge-muted", "Literature surveillance")


def cohort_verdict(item: dict[str, Any]) -> tuple[str, str, str]:
    if is_cohort_excluded(str(item.get("title") or ""), str(item.get("abstract") or "")):
        return ("Exclude", "badge-bad", "Review / software / narrative")
    if item.get("tmt_detected"):
        return ("Watch", "badge-ok", "Large cohort + TMT mention")
    return ("Watch", "badge-warn", "Cohort literature — not a new repository ID")


def fit_display_label(item: dict[str, Any]) -> str:
    fit = str(item.get("atlas_fit") or (item.get("abstract_ai") or {}).get("atlas_fit") or "").strip()
    if not fit:
        return ""
    return f"LLM {fit}"
