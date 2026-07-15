"""Per-project organ & sample-type audit (point check vs map logic)."""
from __future__ import annotations

import re
from typing import Any

from atlas_agent.catalog.organ_classify import (
    canon_disease,
    classify_all_organs,
    classify_organ,
    hint_organs_from_text,
    pick_organ_raw,
    split_organ_parts,
    trim_metastasis_organs,
)


def _text_blob(row: dict[str, Any]) -> str:
    keys = (
        "Title",
        "Tissue Cell Type Detailed",
        "Tissue",
        "Cell Line Organ",
        "Tissue for cell lines",
        "Cell Line Name",
        "Tumor Type",
        "Disease",
        "Short Description",
    )
    return " ".join(str(row.get(k) or "") for k in keys)


def expected_organs_from_text(row: dict[str, Any], *, tumor_type: str) -> set[str]:
    """Independent organ hints from metadata (not curator Organ column)."""
    blob = _text_blob(row)
    expected: set[str] = set(hint_organs_from_text(blob))

    detail = str(row.get("Tissue Cell Type Detailed") or "")
    for part in split_organ_parts(detail):
        o = classify_organ(part)
        if o != "Other":
            expected.add(o)
        else:
            expected.update(hint_organs_from_text(part))

    # Cell line organ column when Organ empty
    organ_col = str(row.get("Organ") or "").strip()
    if not organ_col or re.match(r"^(not specified|unknown)$", organ_col, re.I):
        for key in ("Cell Line Organ", "Tissue for cell lines", "Tissue"):
            for part in split_organ_parts(str(row.get(key) or "")):
                o = classify_organ(part)
                if o != "Other":
                    expected.add(o)

    if expected:
        expected = set(trim_metastasis_organs(sorted(expected), tumor_type))
    return expected


def curator_organs_from_column(row: dict[str, Any], *, tumor_type: str) -> set[str]:
    organ_col = str(row.get("Organ") or "").strip()
    if not organ_col:
        return set()
    return set(trim_metastasis_organs(classify_all_organs(organ_col), tumor_type))


def audit_one(row: dict[str, Any], mapped: dict[str, Any]) -> dict[str, Any]:
    """Return audit record with issues list."""
    issues: list[dict[str, str]] = []
    pid = mapped["pid"]
    organs = set(mapped["organs"])
    tumor_type = mapped["tumor_type"]
    organ_col = mapped["organ_column"]
    sample_type = mapped["sample_type"]
    blob = _text_blob(row).lower()

    if not pid:
        issues.append({"code": "missing_pid", "msg": "No Project ID"})
    if organs == {"Other"}:
        issues.append({"code": "only_other", "msg": "Mapped to Other only — check Organ column"})
    if not organ_col:
        issues.append({"code": "empty_organ_col", "msg": "Organ column empty — using fallback fields"})

    curator = curator_organs_from_column(row, tumor_type=tumor_type)
    if curator and organs != curator:
        issues.append({
            "code": "curator_map_mismatch",
            "msg": f"Curator column → {sorted(curator)} vs map → {sorted(organs)}",
        })

    expected = expected_organs_from_text(row, tumor_type=tumor_type)
    enumerated = len(split_organ_parts(organ_col)) >= 5 if organ_col else False
    if organ_col and not re.match(r"^(multiple organs|multi-organ)", organ_col, re.I):
        extra = organs - expected - {"Multiple_Organs"}
        missing = expected - organs - {"Multiple_Organs"}
        if enumerated:
            extra = set()  # long tissue list in Organ column (e.g. GTEx) — curator authoritative
        if extra:
            issues.append({
                "code": "extra_organs",
                "msg": f"Possibly extra on map: {sorted(extra)} (text hints: {sorted(expected) or '—'})",
            })
        if missing and len(missing) <= 3:
            issues.append({
                "code": "missing_organs",
                "msg": f"Text suggests also: {sorted(missing)}",
            })

    # Metastasis: curator lists liver but map drops it
    raw_organs = set(classify_all_organs(pick_organ_raw(row)))
    if "Liver" in raw_organs and "Liver" not in organs and canon_disease(tumor_type) == "Lung cancer":
        issues.append({
            "code": "metastasis_trim",
            "msg": "Liver in curator list removed (lung primary / metastasis trim)",
            "severity": "info",
        })

    # Sample type cross-check
    if sample_type == "Cell Lines":
        if not re.search(r"cell line|cell-line|cell lines", blob):
            issues.append({
                "code": "sample_type_cl_weak",
                "msg": "Sample Type=Cell Lines but text lacks 'cell line'",
            })
    elif sample_type == "Tissue":
        if re.search(r"\bcell lines?\b", str(row.get("Tissue Cell Type Detailed") or ""), re.I):
            if not re.search(r"normal|adjacent|ffpe|tissue|tumor tissue|biopsy|surgical", blob):
                issues.append({
                    "code": "sample_type_tissue_vs_cl",
                    "msg": "Sample Type=Tissue but detail mentions cell lines",
                })

    # Multi-organ sanity
    if len(organs) >= 5 and "Multiple_Organs" not in organs:
        issues.append({
            "code": "many_organs_no_pan",
            "msg": f"{len(organs)} organs without Multiple_Organs tag",
        })

    severity_rank = {"error": 3, "warn": 2, "info": 1}
    max_sev = "ok"
    for it in issues:
        sev = it.get("severity", "warn" if it["code"] not in ("metastasis_trim",) else "info")
        it["severity"] = sev
        if severity_rank.get(sev, 0) > severity_rank.get(max_sev, 0):
            max_sev = sev if sev != "ok" else max_sev
    if issues and max_sev == "ok":
        max_sev = "warn"

    return {
        "pid": pid,
        "database": str(row.get("Database") or ""),
        "title": str(row.get("Title") or "")[:120],
        "organ_column": organ_col[:200],
        "organs": sorted(organs),
        "sample_type": sample_type,
        "material": mapped["material"],
        "healthy": mapped["healthy"],
        "tumor_type": tumor_type[:80],
        "issues": issues,
        "status": "ok" if not issues else max_sev,
    }


def summarize_audits(records: list[dict[str, Any]]) -> dict[str, Any]:
    mat = {"clC": 0, "clN": 0, "tisC": 0, "tisN": 0}
    by_status: dict[str, int] = {}
    by_organ: dict[str, int] = {}
    issue_codes: dict[str, int] = {}
    seen: set[str] = set()

    for rec in records:
        by_status[rec["status"]] = by_status.get(rec["status"], 0) + 1
        pid = rec["pid"]
        if pid in seen:
            continue
        seen.add(pid)
        mat[rec["material"]] = mat.get(rec["material"], 0) + 1
        for o in rec["organs"]:
            by_organ[o] = by_organ.get(o, 0) + 1
        for iss in rec.get("issues") or []:
            c = iss["code"]
            issue_codes[c] = issue_codes.get(c, 0) + 1

    return {
        "projects": len(seen),
        "material_buckets": mat,
        "material_total": sum(mat.values()),
        "by_status": by_status,
        "organ_project_counts": dict(sorted(by_organ.items(), key=lambda x: -x[1])),
        "issue_codes": dict(sorted(issue_codes.items(), key=lambda x: -x[1])),
    }
