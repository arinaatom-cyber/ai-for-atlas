"""

QC материала образцов для Discovery (не меняет projects.csv).



Статусы:

- candidate — подходит под атлас

- requires_manual_check — смешанный dataset (tissue + organoids/spheroids)

- rejected — не подходит

"""

from __future__ import annotations



import re

from typing import Any



# --- Включение ---

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

PATIENT_FLUID = re.compile(

    r"\b(patient\s+(plasma|serum|blood)|plasma|serum|whole\s+blood|"

    r"peripheral\s+blood|pbmc|csf|cerebrospinal\s+fluid)\b",

    re.I,

)

HUMAN_CANCER_CELL_LINE = re.compile(

    r"\b((human|cancer)\s+cell\s+line|cell\s+lines?\s+from\s+(human|patient)|"

    r"hela|mcf[- ]?7|mcf7|a549|hct116|u2os|pc[- ]?3|du145|t47d|mda[- ]?mb|"

    r"ccle|depmap)\b",

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

    ("patient_fluid", PATIENT_FLUID),

    ("human_cancer_cell_line", HUMAN_CANCER_CELL_LINE),

]



# --- Исключение ---

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

    r"\b(mouse|murine|rat|canine|bovine|porcine|cho\s+cell|3t3|mc38|b16|"

    r"mda[- ]?mb[- ]?231[- ]?luc|non[- ]?human\s+cell\s+line)\b",

    re.I,

)

NON_CANCER_HUMAN_CELL = re.compile(

    r"\b(mesenchymal\s+stem|hbm[- ]?msc?s?|\bmsc\b|fibroblast|ipsc|"

    r"induced\s+pluripotent|hek[- ]?293|hek293t|normal\s+cell\s+line|"

    r"primary\s+cells?\s+from\s+healthy|stem\s+cell\s+derived)\b",

    re.I,

)

ANIMAL_TISSUE = re.compile(

    r"\b(mouse|mice|murine|rat\b|rodent|porcine|bovine|canine|"

    r"animal\s+tissue|xenograft\s+in\s+(mouse|rat))\b",

    re.I,

)

NON_HUMAN_ORG = re.compile(

    r"\b(salmonella|escherichia|chlamydomonas|arabidopsis|yeast|maize|bacteria)\b",

    re.I,

)

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

    for k in (

        "title", "description", "abstract", "abstract_snippet",

        "program", "disease", "experiment_type", "analytical_fraction",

        "primary_site", "sample_processing_protocol",

    ):

        parts.append(str(item.get(k) or ""))

    return " ".join(parts)





def _real_include_signals(blob: str) -> list[str]:

    return [name for name, pat in REAL_INCLUDE_CHECKS if pat.search(blob)]





def _pdc_clinical_tumor_default(item: dict[str, Any], blob: str) -> bool:

    """PDC clinical tumor programs — не HCMI/organoid/PDX-only."""

    if item.get("source") != "pdc_api" and item.get("consortium") != "PDC":

        return False

    if PDC_EXCLUDED_PROGRAM.search(blob):

        return False

    if SPHEROID_ORGANOID.search(blob) or CULTURE_3D.search(blob):

        return False

    if PDX_XENO.search(blob) and not _real_include_signals(blob):

        return False

    return True





def _has_include_signal(blob: str, item: dict[str, Any]) -> tuple[bool, list[str]]:

    hits = _real_include_signals(blob)

    if hits:

        return True, hits



    if _pdc_clinical_tumor_default(item, blob):

        return True, ["pdc_clinical_tumor"]



    if CLINICAL_HUMAN.search(blob) and re.search(

        r"\b(tissue|ffpe|biopsy|plasma|serum|blood|cell\s+line|surgical|resected)\b", blob, re.I

    ):

        if not SPHEROID_ORGANOID.search(blob) and not CULTURE_3D.search(blob):

            return True, ["clinical_human"]



    return False, hits





def assess_sample_material(item: dict[str, Any], blob: str | None = None) -> dict[str, Any]:

    """

    Возвращает qc_status, qc_reasons, material_signals.

    """

    blob = blob or material_blob_from_item(item)

    excluded_hits: list[str] = []

    included_hits: list[str] = []



    if NON_HUMAN_ORG.search(blob) and not re.search(r"\bhuman|homo\s+sapiens|patient\b", blob, re.I):

        return _result("rejected", ["Организм не human (бактерия/растение/др.)"], [], [])



    if ANIMAL_TISSUE.search(blob):

        if not re.search(r"\b(patient|patients|clinical|human\s+tissue|human\s+plasma)\b", blob, re.I):

            return _result("rejected", ["Животные ткани без human component"], [], ["animal_tissue"])



    if NON_HUMAN_CELL.search(blob):

        if not HUMAN_CANCER_CELL_LINE.search(blob):

            return _result("rejected", ["Non-human cell line"], [], ["non_human_cell_line"])



    real_include = _real_include_signals(blob)

    has_non_cancer_cell = bool(NON_CANCER_HUMAN_CELL.search(blob))

    if has_non_cancer_cell and not real_include:

        return _result(

            "rejected",

            ["Human cell material не cancer cell line (MSC/fibroblast/iPSC и др.)"],

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

            or PATIENT_FLUID.search(blob)

            or NORMAL_ADJACENT.search(blob)

            or HUMAN_CANCER_CELL_LINE.search(blob)

        )

        if not human_comp:

            return _result(

                "rejected",

                ["Только PDX/xenograft без отдельного human component"],

                included_hits,

                excluded_hits,

            )



    if has_3d:

        excluded_hits.append("3d_model")

        mixed = bool(real_include) or (

            CLINICAL_HUMAN.search(blob)

            and re.search(r"\b(tissue|ffpe|biopsy|plasma|serum|blood)\b", blob, re.I)

        )

        if mixed:

            return _result(

                "requires_manual_check",

                ["Смешаны tissue/fluid/cell line и spheroids/organoids/3D — проверить вручную"],

                included_hits or real_include,

                excluded_hits,

            )

        return _result(

            "rejected",

            ["Только spheroids/organoids/tumoroids/3D culture"],

            [],

            excluded_hits,

        )



    if has_include:

        if has_non_cancer_cell and "human_cancer_cell_line" not in included_hits:

            return _result(

                "rejected",

                ["Human cell material не cancer cell line (MSC/fibroblast/iPSC и др.)"],

                included_hits,

                excluded_hits + ["non_cancer_human_cell"],

            )

        return _result("candidate", ["Материал соответствует критериям атласа"], included_hits, excluded_hits)



    if CLINICAL_HUMAN.search(blob) or (item.get("human") is True):

        return _result(

            "requires_manual_check",

            ["Human подтверждён, но тип материала (tissue/fluid/cell line) не ясен"],

            included_hits,

            excluded_hits,

        )



    return _result(

        "rejected",

        ["Нет подтверждённого human tumor/adjacent/fluid/cancer cell line материала"],

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


