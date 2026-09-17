from __future__ import annotations

import re
from typing import Any

from atlas_agent.discovery.organism_terms import HUMAN, HUMAN_CANCER_CELL_LINE, NON_HUMAN

HUMAN_TUMOR_TISSUE = re.compile(
    r"\b(tumor\s+tissue|tumou?r\s+specimen|ffpe|surgical\s+specimen|biopsy|"
    r"resected|primary\s+tumor|malignant\s+tissue|carcinoma\s+tissue)\b",
    re.I,
)
NORMAL_ADJACENT = re.compile(
    r"\b(adjacent\s+normal|normal\s+adjacent|paired\s+normal|"
    r"tumor[- ]adjacent|peritumoral|non[- ]?tumou?rous\s+tissue)\b",
    re.I,
)
HUMAN_TISSUE = re.compile(
    r"\b((human|patient|tumor|tumour|normal|adjacent|healthy|surgical|"
    r"fresh|frozen)\s+tissues?|"
    r"tissues?\s+(from|of)\s+(patients?|donors?|humans?)|"
    r"tissue\s+(sample|samples|specimen|proteom|lysate)|"
    r"(liver|lung|brain|kidney|colon|gastric|breast|heart|prostate|"
    r"ovarian|pancreatic|skin|muscle|thyroid)\s+tissue)\b",
    re.I,
)
CLINICAL_HUMAN = re.compile(
    r"\b(patient|patients|clinical\s+sample|donor|cohort|subjects|"
    r"homosapiens|homo\s+sapiens|human\s+subjects?)\b",
    re.I,
)
REAL_INCLUDE_CHECKS: list[tuple[str, re.Pattern[str]]] = [
    ("human_tumor_tissue", HUMAN_TUMOR_TISSUE),
    ("normal_adjacent", NORMAL_ADJACENT),
    ("human_tissue", HUMAN_TISSUE),
    ("human_cancer_cell_line", HUMAN_CANCER_CELL_LINE),
]

BIOFLUID = re.compile(
    r"\b(plasma|serum|urine|saliva|sperm|csf|cerebrospinal\s+fluid|"
    r"whole\s+blood|peripheral\s+blood|\bpbmc\b)\b",
    re.I,
)
SPHEROID_ORGANOID = re.compile(
    r"\b(spheroid|spheroids|organoid|organoids|tumoroid|tumoroids|"
    r"gliosphere|neurosphere|mammosphere)\b",
    re.I,
)
CULTURE_3D = re.compile(
    r"\b(3d\s+culture|three[- ]dimensional\s+culture|scaffold\s+culture|"
    r"hydrogel\s+culture|matrigel\s+culture)\b",
    re.I,
)
PDX_XENO = re.compile(
    r"\b(pdx|patient[- ]derived\s+xenograft|xenograft|xenografted|"
    r"tumorgraft|cdx)\b",
    re.I,
)
NON_HUMAN_CELL = re.compile(
    r"cho\s+cell|3t3|mc38|\bb16\b|mda[- ]?mb[- ]?231[- ]?luc|non[- ]?human\s+cell\s+line",
    re.I,
)
NON_CANCER_HUMAN_CELL = re.compile(
    r"\b(mesenchymal\s+stem|hbm[- ]?msc?s?|\bmsc\b|fibroblast|ipsc|"
    r"induced\s+pluripotent|hek[- ]?293|hek293t|normal\s+cell\s+line|"
    r"primary\s+cells?\s+from\s+healthy|stem\s+cell\s+derived)\b",
    re.I,
)
ANIMAL_TISSUE = NON_HUMAN
NON_HUMAN_ORG = NON_HUMAN
PDC_EXCLUDED_PROGRAM = re.compile(
    r"\b(hcmi|organoid|organoids|spheroid|tumoroid|xenograft|pdx)\b",
    re.I,
)


def material_blob_from_item(item: dict[str, Any]) -> str:
    orgs = " ".join(
        str(o.get("name", o) if isinstance(o, dict) else o)
        for o in (item.get("organisms") or [])
    )
    parts = [orgs]
    qm = item.get("quantification_methods") or []
    if isinstance(qm, list):
        parts.append(" ".join(str(x) for x in qm))
    else:
        parts.append(str(qm or ""))
    for k in (
        "title", "description", "abstract", "abstract_snippet",
        "program", "disease", "experiment_type", "analytical_fraction",
        "primary_site", "sample_processing_protocol", "data_processing_protocol",
    ):
        parts.append(str(item.get(k) or ""))
    ai = item.get("abstract_ai") or {}
    for k in ("material", "summary_en", "summary_ru", "similar_atlas_theme"):
        parts.append(str(ai.get(k) or ""))
    return " ".join(parts)


def _real_include_signals(blob: str) -> list[str]:
    return [name for name, pat in REAL_INCLUDE_CHECKS if pat.search(blob)]


def _pdc_clinical_tumor_default(item: dict[str, Any], blob: str) -> bool:
    if item.get("source") != "pdc_api" and item.get("consortium") != "PDC":
        return False
    if PDC_EXCLUDED_PROGRAM.search(blob):
        return False
    if SPHEROID_ORGANOID.search(blob) or CULTURE_3D.search(blob):
        return False
    if PDX_XENO.search(blob) and not _real_include_signals(blob):
        return False
    return True


_AI_MATERIAL_INCLUDE = {
    "tumor tissue": "human_tumor_tissue",
    "adjacent normal": "normal_adjacent",
    "human tissue": "human_tissue",
    "cancer cell line": "human_cancer_cell_line",
}
_AI_MATERIAL_EXCLUDE = {"plasma", "serum", "blood", "organoid", "pdx"}


def _ai_material_signals(item: dict[str, Any]) -> tuple[list[str], list[str]]:
    ai = item.get("abstract_ai") or {}
    mat = str(ai.get("material") or "").strip().lower()
    if not mat or mat in ("unclear", "other", "unknown"):
        return [], []
    if mat in _AI_MATERIAL_EXCLUDE or ai.get("material_suitable") is False:
        return [], [f"ai_material:{mat}"]
    mapped = _AI_MATERIAL_INCLUDE.get(mat)
    if mapped:
        return [mapped], []
    return [], []


def _has_include_signal(blob: str, item: dict[str, Any]) -> tuple[bool, list[str]]:
    hits = _real_include_signals(blob)
    if hits:
        return True, hits

    ai_inc, _ai_exc = _ai_material_signals(item)
    if ai_inc:
        return True, ai_inc

    if _pdc_clinical_tumor_default(item, blob):
        return True, ["pdc_clinical_tumor"]

    if CLINICAL_HUMAN.search(blob) and re.search(
        r"\b(tissue|ffpe|biopsy|cell\s+line|surgical|resected)\b", blob, re.I
    ):
        if not SPHEROID_ORGANOID.search(blob) and not CULTURE_3D.search(blob):
            return True, ["clinical_human"]

    return False, hits


def assess_sample_material(item: dict[str, Any], blob: str | None = None) -> dict[str, Any]:
    blob = blob or material_blob_from_item(item)
    excluded_hits: list[str] = []

    if NON_HUMAN_ORG.search(blob) and not HUMAN.search(blob):
        return _result("rejected", ["Non-human organism (bacteria/plant/etc.)"], [], [])
    if ANIMAL_TISSUE.search(blob):
        if not re.search(r"\b(patient|patients|clinical|human\s+tissue)\b", blob, re.I):
            return _result("rejected", ["Animal tissue without human component"], [], ["animal_tissue"])
    if NON_HUMAN.search(blob) or NON_HUMAN_CELL.search(blob):
        if not HUMAN_CANCER_CELL_LINE.search(blob) and not HUMAN.search(blob):
            return _result("rejected", ["Non-human cell line"], [], ["non_human_cell_line"])

    real_include = _real_include_signals(blob)
    has_non_cancer_cell = bool(NON_CANCER_HUMAN_CELL.search(blob))
    if has_non_cancer_cell and not real_include:
        return _result(
            "rejected",
            ["Human cells but not cancer cell line (MSC/fibroblast/iPSC etc.)"],
            [],
            ["non_cancer_human_cell"],
        )

    has_3d = bool(SPHEROID_ORGANOID.search(blob) or CULTURE_3D.search(blob))
    has_pdx = bool(PDX_XENO.search(blob))
    has_include, included_hits = _has_include_signal(blob, item)

    if has_pdx:
        excluded_hits.append("pdx_xenograft")
        human_comp = bool(real_include) or bool(
            HUMAN_TUMOR_TISSUE.search(blob)
            or HUMAN_TISSUE.search(blob)
            or NORMAL_ADJACENT.search(blob)
            or HUMAN_CANCER_CELL_LINE.search(blob)
        )
        if not human_comp:
            return _result(
                "rejected",
                ["PDX/xenograft only — no separate human component"],
                included_hits,
                excluded_hits,
            )

    if has_3d:
        excluded_hits.append("3d_model")
        mixed = bool(real_include) or (
            CLINICAL_HUMAN.search(blob)
            and re.search(r"\b(tissue|ffpe|biopsy|cell\s+line)\b", blob, re.I)
        )
        if mixed:
            return _result(
                "requires_manual_check",
                ["Mixed tissue/cell line and spheroids/organoids/3D — review manually"],
                included_hits or real_include,
                excluded_hits,
            )
        return _result(
            "rejected",
            ["Spheroids/organoids/tumoroids/3D culture only"],
            [],
            excluded_hits,
        )

    if BIOFLUID.search(blob) and not has_include:
        return _result(
            "rejected",
            ["Biofluid (plasma/serum/urine/blood) — atlas needs tissue or cell line"],
            included_hits,
            ["biofluid"],
        )

    if has_include:
        if has_non_cancer_cell and "human_cancer_cell_line" not in included_hits:
            return _result(
                "rejected",
                ["Human cells but not cancer cell line (MSC/fibroblast/iPSC etc.)"],
                included_hits,
                excluded_hits + ["non_cancer_human_cell"],
            )
        return _result("candidate", ["Material matches atlas criteria (tissue or cell line)"], included_hits, excluded_hits)

    return _result(
        "rejected",
        ["Material not specified — no tissue/cell line in metadata or article"],
        included_hits,
        excluded_hits,
    )


def _result(
    status: str,
    reasons: list[str],
    included: list[str],
    excluded: list[str],
) -> dict[str, Any]:
    return {
        "qc_status": status,
        "qc_reasons": reasons,
        "material_signals": {
            "included": included,
            "excluded": excluded,
        },
    }
