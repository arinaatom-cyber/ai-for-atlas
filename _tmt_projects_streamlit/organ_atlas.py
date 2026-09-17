# -*- coding: utf-8 -*-
"""Organ classification — ported from arinaatom-cyber/TMT app.js."""
from __future__ import annotations

import re
from collections import Counter, defaultdict

import pandas as pd

PAN_ORGAN_THRESHOLD = 8
VAGUE_ORGAN = re.compile(r"^(not specified|unknown|n/a|na|—|-)$", re.I)

ORGAN_EXACT = {
    "kidney": "Kidney", "cervix": "Cervix", "pancreas": "Pancreas", "liver": "Liver",
    "lung": "Lung", "brain": "Brain", "breast": "Breast", "colon": "Colon",
    "stomach": "Stomach", "spleen": "Spleen", "bone marrow": "Bone_Marrow",
    "blood": "Blood", "lymph node": "Lymph_Node", "ovary": "Ovary", "uterus": "Uterus",
    "prostate": "Prostate", "testis": "Testis", "thyroid": "Thyroid", "bladder": "Bladder",
    "muscle": "Muscle", "bone": "Bone", "skin": "Skin", "esophagus": "Esophagus",
    "heart": "Heart", "nerve": "Nerve", "pituitary": "Pituitary",
    "small intestine": "Small_Intestine", "adrenal gland": "Adrenal_Gland",
    "salivary gland": "Salivary_Gland", "adipose tissue": "Adipose_Tissue",
    "soft tissue": "Soft_Tissue", "multiple organs": "Multiple_Organs",
    "multiple organs (22 types)": "Multiple_Organs",
    "ovary; fallopian tube": "Ovary", "colon/rectum": "Colon", "brain/cns": "Brain",
}

ORGAN_MAP = {
    "hematopoietic system": "Blood", "hematopoietic": "Blood", "hematologic": "Blood",
    "bone marrow": "Bone_Marrow", "peripheral blood": "Blood", "pbmc": "Blood",
    "fallopian tube": "Ovary", "fallopian": "Ovary", "hgsoc": "Ovary", "ovarian": "Ovary",
    "colorectal": "Colon", "rectum": "Colon", "rectal": "Colon", "sigmoid": "Colon",
    "hepatocellular": "Liver", "hepat": "Liver", "gastric": "Stomach",
    "glioblastoma": "Brain", "medulloblastoma": "Brain", "cerebellum": "Brain",
    "cerebral cortex": "Brain", "neuroblastoma": "Bone_Marrow",
    "leukemia": "Blood", "leukaemia": "Blood", "lymphoma": "Lymph_Node", "aml": "Blood",
    "melanoma": "Skin", "sarcoma": "Soft_Tissue", "oral cavity": "Salivary_Gland",
    "head and neck": "Salivary_Gland", "endometri": "Uterus", "endometrium": "Uterus",
    "lymph nodes": "Lymph_Node", "multiple organs": "Multiple_Organs",
    "cancer cell line panel": "Multiple_Organs", "cancer cell lines": "Multiple_Organs",
    "brain": "Brain", "lung": "Lung", "breast": "Breast", "liver": "Liver",
    "pancrea": "Pancreas", "kidney": "Kidney", "renal": "Kidney", "thyroid": "Thyroid",
    "esophag": "Esophagus", "bladder": "Bladder", "prostate": "Prostate",
    "heart": "Heart", "skin": "Skin", "muscle": "Muscle", "bone": "Bone",
    "intestin": "Small_Intestine", "colon": "Colon", "ovary": "Ovary", "uterus": "Uterus",
    "cervix": "Cervix", "testis": "Testis", "pituitary": "Pituitary", "spleen": "Spleen",
    "adrenal": "Adrenal_Gland", "salivary": "Salivary_Gland", "eye": "Eye", "orbit": "Eye",
}

HINT_ORGANS = [
    (re.compile(r"epidermoid|a431\b", re.I), "Skin"),
    (re.compile(r"mcf[- ]?7|breast cancer|mammary", re.I), "Breast"),
    (re.compile(r"glioblastoma|glioma|u251", re.I), "Brain"),
    (re.compile(r"lung cancer|hcc827|luad|nsclc", re.I), "Lung"),
    (re.compile(r"hepat|liver|hcc", re.I), "Liver"),
    (re.compile(r"colon|colorectal|crc", re.I), "Colon"),
    (re.compile(r"pancrea|pdac", re.I), "Pancreas"),
    (re.compile(r"ovarian|ovary|hgsoc", re.I), "Ovary"),
    (re.compile(r"leukemia|aml|cll|thp-1|k562", re.I), "Blood"),
    (re.compile(r"melanoma", re.I), "Skin"),
]

CANCER_KW = (
    "carcinoma", "cancer", "tumor", "tumour", "sarcoma", "leukemia", "leukaemia",
    "lymphoma", "myeloma", "melanoma", "glioma", "glioblastoma", "adenocarcinoma",
    "neuroblastoma", "medulloblastoma", "metastasis", "metastatic", "malignant",
    "neoplasm", "blastoma",
)

DATABASE_CANON = {
    "PRIDE": "PRIDE",
    "PDC": "PDC",
    "MASSIVE": "MassIVE",
    "IPROX": "iProX",
    "GTEX": "GTEx",
    "CLLE": "CLLE",
    "CCLE": "CLLE",
}


def normalize_database(value: object) -> str:
    raw = str(value or "").strip()
    if not raw or raw.lower() in ("nan", "none"):
        return "Unknown"
    return DATABASE_CANON.get(raw.upper(), raw)


def _num(row: pd.Series, col: str) -> float:
    try:
        v = row.get(col)
        if v is None or (isinstance(v, float) and pd.isna(v)):
            return 0.0
        s = str(v).strip()
        if not s or s.lower() in ("nan", "none"):
            return 0.0
        return float(s)
    except (TypeError, ValueError):
        return 0.0


def is_healthy_row(row: pd.Series) -> bool:
    db = normalize_database(row.get("Database"))
    if db == "GTEx":
        return True
    if db == "CLLE":
        return False

    ctrl = _num(row, "Control Healthy") + _num(row, "Healthy Treated")
    case = _num(row, "Case Cancer Untreated") + _num(row, "Case Cancer Treated") + _num(row, "preCancer")
    if ctrl > 0 and case == 0:
        return True
    if case > 0 and ctrl == 0:
        return False

    sample_type = str(row.get("Sample Type", "") or "").lower()
    if sample_type == "cell lines":
        return False

    return is_healthy(
        str(row.get("Tumor Type", row.get("Disease", ""))),
        str(row.get("Sample Type", "")),
        str(row.get("Title", "")),
        str(row.get("Disease", "")),
    )


def split_organ_parts(raw: str) -> list[str]:
    parts = re.split(r"[;\n,]+", str(raw or ""))
    out = []
    for p in parts:
        p = p.strip()
        p = re.sub(r"^multiple\s+organs?\s*", "", p, flags=re.I)
        p = re.sub(r"^\(\d+[^)]*\)\s*", "", p)
        if p and not VAGUE_ORGAN.match(p):
            out.append(p)
    return out


def hint_organs_from_text(text: str) -> list[str]:
    found = set()
    for pat, organ in HINT_ORGANS:
        if pat.search(text or ""):
            found.add(organ)
    return list(found)


def classify_organ(name: str) -> str:
    low = (name or "").lower().strip()
    if not low:
        return "Other"
    if low in ORGAN_EXACT:
        return ORGAN_EXACT[low]
    for key in sorted(ORGAN_MAP, key=len, reverse=True):
        if key in low:
            return ORGAN_MAP[key]
    return "Other"


def classify_all_organs(raw: str) -> list[str]:
    cleaned = (raw or "").lower().strip()
    if any(x in cleaned for x in ("multiple organs", "multi-organ", "22 types", "22 lineages")):
        return ["Multiple_Organs"]
    parts = split_organ_parts(raw)
    if not parts:
        return ["Other"]
    organs: set[str] = set()
    for p in parts:
        o = classify_organ(p)
        if o != "Other":
            organs.add(o)
        else:
            for h in hint_organs_from_text(p):
                organs.add(h)
    if not organs:
        for h in hint_organs_from_text(raw):
            organs.add(h)
    if not organs:
        organs.add("Other")
    lst = list(organs)
    if len(lst) >= 3 and "Multiple_Organs" not in lst:
        lst.append("Multiple_Organs")
    return lst


def is_healthy(tumor_type: str, sample_type: str, title: str, disease: str) -> bool:
    t = (tumor_type or "").lower().strip()
    d = (disease or "").lower().strip()
    ti = (title or "").lower()
    for k in CANCER_KW:
        if k in t or k in d or k in ti:
            return False
    if t in ("", "normal", "healthy", "not specified", "not_specified"):
        return True
    return "normal" in t or "healthy" in t or "healthy" in d


def pick_organ_raw(row: pd.Series) -> str:
    parts: list[str] = []
    for col in ("Organ", "Tissue", "Cell Line Organ", "Tissue for cell lines"):
        for p in split_organ_parts(str(row.get(col, "") or "")):
            parts.append(p)
    detail = str(row.get("Tissue Cell Type Detailed", "") or "").strip()
    organ_main = str(row.get("Organ", "") or "").strip()
    if (not parts or VAGUE_ORGAN.match(organ_main)) and detail:
        parts.extend(split_organ_parts(detail))
    if len(parts) <= 1 and (
        "multiple" in organ_main.lower() or re.search(r"cancer cell lines", detail, re.I)
    ):
        parts.extend(hint_organs_from_text(detail))
    return "; ".join(parts) if parts else "Unknown"


def normalize_pid(project_id: str) -> str:
    pid = str(project_id or "").strip()
    m = re.search(r"(IPX\d+)\s*\((PXD\d+)\)", pid, re.I)
    return m.group(2) if m else pid


def enrich_projects(df: pd.DataFrame) -> pd.DataFrame:
    out = df[df["Project ID"].astype(str).str.strip() != ""].copy()
    out["Database"] = out["Database"].map(normalize_database) if "Database" in out.columns else "Unknown"
    out["project_key"] = out["Project ID"].map(normalize_pid)
    out["organ_raw"] = out.apply(pick_organ_raw, axis=1)
    out["organs"] = out["organ_raw"].map(classify_all_organs)
    out["healthy"] = out.apply(is_healthy_row, axis=1)
    out["is_pan"] = out["organs"].map(lambda xs: len(xs) >= PAN_ORGAN_THRESHOLD)
    return out


def organ_project_counts(df: pd.DataFrame) -> Counter:
    ctr: Counter = Counter()
    for organs in df["organs"]:
        for o in organs:
            ctr[o] += 1
    return ctr


def organ_stats(df: pd.DataFrame, organ: str) -> dict:
    rows = [r for _, r in df.iterrows() if organ in r["organs"]]
    seen = set()
    uniq = []
    for r in rows:
        if r["project_key"] not in seen:
            seen.add(r["project_key"])
            uniq.append(r)
    n_c = sum(1 for r in uniq if not r["healthy"])
    n_n = sum(1 for r in uniq if r["healthy"])
    n_pan = sum(1 for r in uniq if r["is_pan"])
    return {"n": len(uniq), "nC": n_c, "nN": n_n, "nPan": n_pan}


def all_organ_stats(df: pd.DataFrame) -> dict[str, dict]:
    organs = {o for organs in df["organs"] for o in organs}
    return {o: organ_stats(df, o) for o in organs}
