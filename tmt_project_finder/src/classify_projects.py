from __future__ import annotations

from typing import Any

from src.deleted_check import check_deleted
from src.duplicate_check import check_duplicate
from src.extract_metadata import enrich_record, extract_material, extract_organism, extract_tmt
from src.parse_sources import normalize_record
from src.utils import ensure_manual_fields

CLASSIFICATIONS = (
    "high_priority_check",
    "medium_priority_check",
    "manual_check",
    "reject",
    "duplicate",
    "rejected_previously_removed",
)


def classify_project(
    record: dict[str, Any],
    *,
    database=None,
    deleted_database=None,
) -> dict[str, Any]:
    rec = normalize_record(record, use_html_fallback=False)
    rec = enrich_record(rec)
    rec = ensure_manual_fields(rec)

    reasons: list[str] = []

    dup = check_duplicate(rec, database)
    if dup["is_duplicate"]:
        rec["classification"] = "duplicate"
        rec["classification_reasons"] = [f"Duplicate on {dup['matched_on']}: {dup['matched_value']}"]
        return rec

    deleted = check_deleted(rec, deleted_database)
    if deleted["is_deleted"]:
        rec["classification"] = "rejected_previously_removed"
        rec["classification_reasons"] = [f"Previously removed ({deleted['matched_on']})"]
        return rec

    org = rec.get("organism_extract") or extract_organism(rec)
    tmt = rec.get("tmt_extract") or extract_tmt(rec)
    mat = rec.get("material_extract") or extract_material(rec)

    if org["status"] == "rejected":
        reasons.append(f"rejected_organism: {org.get('rejected_hits')}")
    if tmt["status"] == "rejected":
        reasons.append(f"rejected_tmt: {tmt.get('rejected_hits')}")
    if mat["status"] == "rejected":
        reasons.append(f"rejected_material: {mat.get('rejected_hits')}")

    if reasons:
        rec["classification"] = "reject"
        rec["classification_reasons"] = reasons
        return rec

    human_ok = org["status"] == "confirmed"
    tmt_ok = tmt["status"] == "confirmed"
    mat_ok = mat["status"] == "confirmed"

    manual_reasons: list[str] = []
    if tmt["status"] == "ambiguous":
        manual_reasons.append("TMT ambiguous")
    if org["status"] in ("unclear", "conflicting"):
        manual_reasons.append("organism unclear/conflicting")
    if mat["status"] in ("unclear", "conflicting"):
        manual_reasons.append("material unclear/conflicting")
    if org["status"] == "conflicting" or mat["status"] == "conflicting":
        manual_reasons.append("conflicting evidence")

    if manual_reasons:
        rec["classification"] = "manual_check"
        rec["classification_reasons"] = manual_reasons
        return rec

    if human_ok and tmt_ok and mat_ok:
        rec["classification"] = "high_priority_check"
        rec["classification_reasons"] = ["human + TMT >6 channels (7–18, incl. TMT18) + allowed material confirmed"]
        return rec

    if human_ok:
        rec["classification"] = "medium_priority_check"
        rec["classification_reasons"] = ["human confirmed; partial metadata missing"]
        return rec

    rec["classification"] = "manual_check"
    rec["classification_reasons"] = ["insufficient metadata for automatic classification"]
    return rec


def classify_all(
    records: list[dict],
    *,
    database=None,
    deleted_database=None,
) -> list[dict]:
    return [
        classify_project(r, database=database, deleted_database=deleted_database)
        for r in records
    ]
