"""Organ classification — mirrors human-proteome-atlas/app.js (TMT map)."""
from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

VAGUE_ORGAN = re.compile(r"^(not specified|unknown|n/a|na|—|-)$", re.I)

DIS_RULES: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"nsclc|non[- ]?small[- ]?cell lung|luad|lusc|lung adenocarcinoma|lung carcinoma|sclc|hcc827|nci-h322", re.I), "Lung cancer"),
    (re.compile(r"\bhcc\b|hepatocellular|liver cancer|hepatoma", re.I), "Liver cancer"),
]

HINT_RULES: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"epidermoid|a431\b", re.I), "Skin"),
    (re.compile(r"mcf[- ]?7|breast cancer|mammary", re.I), "Breast"),
    (re.compile(r"glioblastoma|glioma|u251|dao[y]?", re.I), "Brain"),
    (re.compile(r"lung cancer|hcc827|nci-h322|luad|nsclc", re.I), "Lung"),
    (re.compile(r"hepatocellular|liver|\bhcc\b", re.I), "Liver"),
    (re.compile(r"colon|colorectal|crc|rectal", re.I), "Colon"),
    (re.compile(r"pancrea|pdac", re.I), "Pancreas"),
    (re.compile(r"ovarian|ovary|hgsoc", re.I), "Ovary"),
    (re.compile(r"prostate|pca\b", re.I), "Prostate"),
    (re.compile(r"kidney|renal|rcc", re.I), "Kidney"),
    (re.compile(r"stomach|gastric", re.I), "Stomach"),
    (re.compile(r"melanoma", re.I), "Skin"),
    (re.compile(r"leukemia|aml|cll|myeloma|jurkat|k562|thp-1", re.I), "Blood"),
    (re.compile(r"fibroblast|skin", re.I), "Skin"),
    (re.compile(r"endometri", re.I), "Uterus"),
    (re.compile(r"esophag|barrett", re.I), "Esophagus"),
    (re.compile(r"thyroid", re.I), "Thyroid"),
    (re.compile(r"bladder|urothel", re.I), "Bladder"),
    (re.compile(r"sarcoma|osteosarcoma|fibrosarcoma", re.I), "Soft_Tissue"),
    (re.compile(r"b cell|t cell|pbmc|monocyte|cd14|cd4\+", re.I), "Blood"),
]

CANCER_KW = (
    "carcinoma", "cancer", "tumor", "tumour", "sarcoma", "leukemia", "leukaemia",
    "lymphoma", "myeloma", "melanoma", "glioma", "glioblastoma", "adenocarcinoma",
    "neuroblastoma", "medulloblastoma", "astrocytoma", "ependymoma", "metastasis",
    "metastatic", "malignant", "neoplasm", "blastoma",
)


@lru_cache(maxsize=1)
def _maps() -> tuple[dict[str, str], dict[str, str]]:
    path = Path(__file__).with_name("organ_maps.json")
    data = json.loads(path.read_text(encoding="utf-8"))
    return data["MAP"], data["ORGAN_EXACT"]


def split_organ_parts(raw: str) -> list[str]:
    if not raw:
        return []
    parts = re.split(r"[;\n,]+", raw)
    out: list[str] = []
    for p in parts:
        x = p.strip()
        x = re.sub(r"^multiple\s+organs?\s*", "", x, flags=re.I)
        x = re.sub(r"^\(\d+[^)]*\)\s*", "", x)
        x = x.strip()
        if x and not VAGUE_ORGAN.match(x):
            out.append(x)
    return out


def hint_organs_from_text(text: str) -> list[str]:
    if not text:
        return []
    found: set[str] = set()
    for pat, organ in HINT_RULES:
        if pat.search(text):
            found.add(organ)
    return sorted(found)


def classify_organ(name: str) -> str:
    l = (name or "").lower().strip()
    if not l:
        return "Other"
    _, exact = _maps()
    if l in exact:
        return exact[l]
    mp, _ = _maps()
    for k in sorted(mp.keys(), key=len, reverse=True):
        if k in l:
            return mp[k]
    return "Other"


def classify_all_organs(raw: str) -> list[str]:
    if not raw:
        return ["Other"]
    cleaned = raw.lower().strip()
    if re.search(r"multiple organs\s*\(\s*22\s*types?\s*\)", raw, re.I) or "22 lineages" in cleaned:
        return ["Multiple_Organs"]
    if cleaned in ("multiple organs", "multi-organ"):
        return ["Multiple_Organs"]
    parts = split_organ_parts(raw)
    if not parts:
        return ["Other"]
    organs: set[str] = set()
    for p in parts:
        o = classify_organ(p)
        if o != "Other" or p.lower() == "other":
            organs.add(o)
        else:
            organs.update(hint_organs_from_text(p))
    if not organs:
        organs.update(hint_organs_from_text(raw))
    if not organs:
        organs.add("Other")
    lst = sorted(organs)
    if len(lst) >= 3 and "Multiple_Organs" not in lst:
        lst.append("Multiple_Organs")
    return lst


def canon_disease(tumor_type: str) -> str:
    s = (tumor_type or "").strip()
    for pat, label in DIS_RULES:
        if pat.search(s):
            return label
    return s


def trim_metastasis_organs(organs: list[str], tumor_type: str) -> list[str]:
    if len(organs) < 2:
        return organs
    dc = canon_disease(tumor_type)
    if dc == "Lung cancer" and "Lung" in organs:
        return [o for o in organs if o != "Liver"]
    if dc == "Liver cancer" and "Liver" in organs:
        return [o for o in organs if o != "Lung"]
    return organs


def pick_organ_raw(row: dict[str, Any]) -> str:
    organ_main = str(row.get("Organ") or "").strip()
    parts: list[str] = []

    def add_parts(raw: str) -> None:
        for p in split_organ_parts(raw):
            if p and not VAGUE_ORGAN.match(p):
                parts.append(p)

    if organ_main and not VAGUE_ORGAN.match(organ_main):
        # Keep pan-organ labels intact (split strips "Multiple organs (22 types)" → empty)
        if classify_all_organs(organ_main) == ["Multiple_Organs"]:
            return organ_main
        add_parts(organ_main)
        return "; ".join(parts) if parts else organ_main

    for key in ("Cell Line Organ", "Tissue for cell lines", "Tissue"):
        add_parts(str(row.get(key) or ""))
    detail = str(row.get("Tissue Cell Type Detailed") or "").strip()
    if not parts and detail:
        add_parts(detail)
    if len(parts) <= 1 and re.search(r"cancer cell lines", detail, re.I):
        for o in hint_organs_from_text(detail):
            parts.append(o.replace("_", " "))
    return "; ".join(parts) if parts else "Unknown"


def normalize_sample_type(raw: str) -> str:
    s = (raw or "").strip()
    if re.match(r"^cell\s*lines?$", s, re.I):
        return "Cell Lines"
    if re.match(r"^tissue$", s, re.I):
        return "Tissue"
    return s or "Unknown"


def is_healthy(tumor_type: str, sample_type: str, title: str, disease: str) -> bool:
    t = (tumor_type or "").lower().strip()
    d = (disease or "").lower().strip()
    ti = (title or "").lower()
    for k in CANCER_KW:
        if k in t or k in d or k in ti:
            return False
    if t in ("", "normal", "healthy", "not specified", "not_specified"):
        return True
    if "normal" in t or "healthy" in t or "healthy" in d:
        return True
    return False


def material_bucket(sample_type: str, healthy: bool) -> str:
    is_cl = sample_type == "Cell Lines"
    if is_cl and healthy:
        return "clN"
    if is_cl and not healthy:
        return "clC"
    if not is_cl and healthy:
        return "tisN"
    return "tisC"


def normalize_project_id(raw: str) -> str:
    s = (raw or "").strip()
    m = re.match(r"^(IPX\d+)\s*\((PXD\d+)\)", s, re.I)
    if m:
        return m.group(2).upper()
    m = re.search(r"(PXD\d+|PDC\d+|MSV\d+|IPX\d+)", s, re.I)
    return m.group(1).upper() if m else s


def map_project(row: dict[str, Any]) -> dict[str, Any]:
    tumor_type = str(row.get("Tumor Type") or row.get("Disease Subtype") or row.get("Disease") or "Not specified")
    sample_type = normalize_sample_type(str(row.get("Sample Type") or ""))
    title = str(row.get("Title") or "")
    disease = str(row.get("Disease") or "")
    organ_raw = pick_organ_raw(row)
    organs = trim_metastasis_organs(classify_all_organs(organ_raw), tumor_type)
    healthy = is_healthy(tumor_type, sample_type, title, disease)
    return {
        "pid": normalize_project_id(str(row.get("Project ID") or "")),
        "organ_raw": organ_raw,
        "organs": organs,
        "sample_type": sample_type,
        "healthy": healthy,
        "material": material_bucket(sample_type, healthy),
        "tumor_type": tumor_type,
        "organ_column": str(row.get("Organ") or "").strip(),
    }
