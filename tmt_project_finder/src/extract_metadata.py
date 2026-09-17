"""Extract organism, TMT, context, material from text using dictionaries.yaml."""
from __future__ import annotations

import re
from typing import Any

from src.utils import load_dictionaries, record_blob


def _find_terms(blob: str, terms: list[str]) -> list[str]:
    hits = []
    for t in terms:
        if re.search(r"\b" + re.escape(t.lower()) + r"\b", blob, re.I):
            hits.append(t)
    return hits


def extract_organism(record: dict[str, Any], dictionaries: dict | None = None) -> dict[str, Any]:
    d = dictionaries or load_dictionaries()
    blob = record_blob(record)
    allowed = _find_terms(blob, d.get("allowed_organism") or [])
    rejected = _find_terms(blob, d.get("rejected_organism") or [])

    status = "unclear"
    if allowed and not rejected:
        status = "confirmed"
    elif rejected:
        status = "rejected"
    elif allowed:
        status = "confirmed"

    return {
        "status": status,
        "allowed_hits": allowed,
        "rejected_hits": rejected,
        "value": record.get("organism") or ", ".join(allowed) or "",
    }


def extract_tmt(record: dict[str, Any], dictionaries: dict | None = None) -> dict[str, Any]:
    d = dictionaries or load_dictionaries()
    blob = record_blob(record)
    method = (record.get("method") or "").lower()
    full = f"{blob} {method}"

    allowed = _find_terms(full, d.get("allowed_tmt") or [])
    rejected = _find_terms(full, d.get("rejected_tmt") or [])
    ambiguous = _find_terms(full, d.get("ambiguous_tmt") or [])

    allowed_plex = {str(n) for n in range(7, 19)}  # строго >6 и ≤18
    reject_plex = {"2", "3", "4", "5", "6"}
    plex_hits: list[str] = []
    for m in re.finditer(r"tmtpro\s*[- ]?(\d{1,2})|tmt\s*[- ]?(\d{1,2})\b", full, re.I):
        val = next(g for g in m.groups() if g)
        is_pro = "tmtpro" in m.group(0).lower()
        if val in reject_plex:
            rejected.append(f"TMT{val}")
            continue
        if val not in allowed_plex:
            continue
        plex_hits.append(f"TMTpro{val}" if is_pro else f"TMT{val}")

    allowed = list(dict.fromkeys(allowed + plex_hits))

    status = "unclear"
    if rejected:
        status = "rejected"
    elif allowed:
        status = "confirmed"
    elif ambiguous:
        status = "ambiguous"

    return {
        "status": status,
        "allowed_hits": allowed,
        "rejected_hits": rejected,
        "ambiguous_hits": ambiguous,
        "value": ", ".join(allowed) or ", ".join(ambiguous) or "",
    }


def extract_context(record: dict[str, Any], dictionaries: dict | None = None) -> dict[str, Any]:
    d = dictionaries or load_dictionaries()
    blob = record_blob(record)
    cancer = _find_terms(blob, d.get("cancer_terms") or [])
    healthy = _find_terms(blob, d.get("healthy_terms") or [])
    mixed = _find_terms(blob, d.get("mixed_terms") or [])

    if mixed or (cancer and healthy):
        design = "mixed"
    elif cancer:
        design = "cancer"
    elif healthy:
        design = "healthy"
    else:
        design = "unknown"

    return {
        "design": design,
        "cancer_hits": cancer,
        "healthy_hits": healthy,
        "mixed_hits": mixed,
    }


def extract_material(record: dict[str, Any], dictionaries: dict | None = None) -> dict[str, Any]:
    d = dictionaries or load_dictionaries()
    blob = record_blob(record)
    sample = (record.get("sample_type") or "").lower()
    full = f"{blob} {sample}"

    allowed = _find_terms(full, d.get("allowed_material") or [])
    rejected = _find_terms(full, d.get("rejected_material") or [])
    biofluid = {"plasma", "serum", "urine", "saliva"}
    if allowed:
        rejected = [h for h in rejected if h.lower() not in biofluid]

    status = "unclear"
    if rejected and not allowed:
        status = "rejected"
    elif allowed and rejected:
        status = "conflicting"
    elif allowed:
        status = "confirmed"
    elif rejected:
        status = "rejected"

    return {
        "status": status,
        "allowed_hits": allowed,
        "rejected_hits": rejected,
        "value": record.get("sample_type") or ", ".join(allowed) or "",
    }


def enrich_record(record: dict[str, Any]) -> dict[str, Any]:
    """Attach extracted metadata fields to record."""
    out = dict(record)
    out["organism_extract"] = extract_organism(out)
    out["tmt_extract"] = extract_tmt(out)
    out["context_extract"] = extract_context(out)
    out["material_extract"] = extract_material(out)
    return out
