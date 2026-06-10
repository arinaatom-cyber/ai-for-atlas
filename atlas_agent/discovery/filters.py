"""
Фильтры атласа для Discovery Agent.

Правила (из вашего каталога + запрос):
- Human only (без mouse/rat)
- TMT >6 каналов, обычно до 16-plex (как в атласе)
- Healthy-only / cancer-only / case-control (с healthy) — OK
- PMID, PXD, PDC, MSV, IPX, iProX — извлечение из текста
- Уже в каталоге → not recommended
"""
from __future__ import annotations

import re
from typing import Any

import pandas as pd

from atlas_agent.discovery.sample_material_qc import assess_sample_material, material_blob_from_item
from atlas_agent.sources.projects_table import primary_project_id

# ID в тексте
ID_PATTERNS = {
    "PXD": re.compile(r"\b(PXD\d{6,9})\b", re.I),
    "PDC": re.compile(r"\b(PDC\d{6,9})\b", re.I),
    "MSV": re.compile(r"\b(MSV\d{6,12})\b", re.I),
    "IPX": re.compile(r"\b(IPX\d{6,12})\b", re.I),
    "PMID": re.compile(r"\b(?:PMID[:\s]*)?(\d{7,9})\b", re.I),
    "CPTAC": re.compile(r"\b(CPTAC-[A-Z0-9-]+)\b", re.I),
}

NON_HUMAN = re.compile(
    r"\b(mouse|mice|murine|mus\s+musculus|rat\b|rodent|porcine|pig\b|chlamydomonas|"
    r"xenograft\s+in\s+mouse|mc38|b16|hela\s+mouse|nude\s+mice|salmonella|"
    r"escherichia|bacterial|maize|arabidopsis|yeast|protist)\b",
    re.I,
)
LABEL_FREE_ONLY = re.compile(r"\blabel[- ]?free\b", re.I)
HUMAN = re.compile(
    r"\b(human|homo\s+sapiens|patient|clinical|donor|pbmc|plasma\s+from\s+patients)\b",
    re.I,
)
HEALTHY = re.compile(
    r"\b(healthy|normal|control|adjacent\s+normal|benign|non[- ]?smoker|"
    r"never[- ]?smoker|wild[- ]?type\s+control)\b",
    re.I,
)
REVIEW_ONLY = re.compile(
    r"\b(review|editorial|protocol|methods? paper|perspective|commentary|tutorial)\b",
    re.I,
)
CANCER = re.compile(
    r"\b(cancer|carcinoma|tumor|tumour|malignant|adenocarcinoma|hcc|melanoma|"
    r"smoker|smoking|disease|metastasis|glioblastoma)\b",
    re.I,
)
TMT_PLEX = re.compile(
    r"tmtpro\s*[- ]?(\d{1,2})|tmt\s*[- ]?(\d{1,2})\s*[- ]?plex|tmt(\d{1,2})\b|(\d{1,2})\s*plex",
    re.I,
)
ATLAS_TMT_PLEXES = (10, 11, 12, 16)


def default_filter_config() -> dict[str, Any]:
    return {
        "human_only": True,
        "allowed_tmt_plexes": list(ATLAS_TMT_PLEXES),  # >6ch: 10, 11, 12, 16, TMTpro16
        "min_tmt_channels": 10,
        "max_tmt_channels": 16,
        "allow_healthy_only": True,
        "allow_cancer_only": True,
        "allow_case_control": True,    # smokers vs healthy OK
        "allowed_databases": ["PRIDE", "PDC", "iProX", "MassIVE", "IPX", "MSV"],
        "reject_non_human": True,
    }


def extract_ids_from_text(text: str) -> dict[str, list[str]]:
    found: dict[str, list[str]] = {}
    for kind, pat in ID_PATTERNS.items():
        hits = sorted({m.group(1).upper() if kind != "PMID" else m.group(1) for m in pat.finditer(text or "")})
        if hits:
            found[kind] = hits
    return found


def build_catalog_index(df: pd.DataFrame) -> dict[str, set[str]]:
    pmids: set[str] = set()
    accessions: set[str] = set()
    for _, r in df.iterrows():
        pid = primary_project_id(str(r.get("Project ID", "")))
        if pid:
            accessions.add(pid.upper())
        pm = re.sub(r"\D", "", str(r.get("PMID", "") or ""))
        if pm:
            pmids.add(pm)
        for col in ("Title", "Short Description", "Experimental Design", "URL"):
            if col in r.index:
                for ids in extract_ids_from_text(str(r.get(col, ""))).values():
                    accessions.update(x.upper() for x in ids if not x.isdigit())
                    pmids.update(x for x in ids if x.isdigit())
    return {"pmids": pmids, "accessions": accessions}


def _infer_plex(blob: str) -> int | None:
    m = TMT_PLEX.search(blob or "")
    if m:
        for g in m.groups():
            if g:
                return int(g)
    return None


def plex_allowed(plex: int | None, cfg: dict[str, Any], *, blob: str = "") -> bool:
    """TMT >6 каналов: только 10, 11, 12, 16 (TMTpro16 → 16)."""
    allowed = cfg.get("allowed_tmt_plexes") or list(ATLAS_TMT_PLEXES)
    if plex is not None:
        return int(plex) in allowed
    if re.search(r"tmtpro\s*[- ]?16|tmt\s*[- ]?16", blob, re.I):
        return 16 in allowed
    return False


def is_confirmed_human(item: dict[str, Any], blob: str) -> bool:
    """Строго: только подтверждённый human (Homo sapiens / patient / clinical)."""
    if item.get("human") is False:
        return False
    if item.get("human") is True:
        return True

    src = str(item.get("source") or item.get("consortium") or "").lower()
    if src in ("pdc_api", "pdc") or item.get("consortium") == "PDC":
        return True

    org_parts = []
    for o in item.get("organisms") or []:
        org_parts.append(str(o.get("name", o) if isinstance(o, dict) else o))
    org_text = " ".join(org_parts).lower()
    if "homo" in org_text or "human" in org_text:
        return True

    if re.search(r"\b(mouse|mice|murine|rat\b|porcine|chlamydomonas)\b", blob, re.I):
        if not re.search(r"\b(patient|patients|clinical|donor|cohort|subjects|volunteer)\b", blob, re.I):
            return False

    if NON_HUMAN.search(blob) and not HUMAN.search(blob):
        return False

    return bool(HUMAN.search(blob)) or bool(
        re.search(r"\b(patient|patients|clinical|donor|cohort)\b", blob, re.I)
    )


def _infer_sample_design(blob: str) -> str:
    has_h = bool(HEALTHY.search(blob))
    has_c = bool(CANCER.search(blob))
    if has_h and has_c:
        return "case_control"
    if has_h:
        return "healthy_only"
    if has_c:
        return "cancer_only"
    return "unknown"


def classify_candidate(
    item: dict[str, Any],
    catalog_index: dict[str, set[str]],
    *,
    cfg: dict | None = None,
) -> dict[str, Any]:
    """Возвращает item с полями: verdict, filter_reasons, extracted_ids."""
    cfg = cfg or default_filter_config()
    blob = material_blob_from_item(item)
    blob_lower = blob.lower()

    extracted = extract_ids_from_text(blob)
    for key in ("accession", "pmid"):
        v = str(item.get(key) or "").strip()
        if v:
            kind = "PMID" if key == "pmid" and v.isdigit() else None
            if kind:
                extracted.setdefault("PMID", []).append(v)
            elif v.upper().startswith(("PXD", "PDC", "MSV", "IPX")):
                extracted.setdefault(v[:3], []).append(v.upper())

    accs = set()
    for ids in extracted.values():
        for x in ids:
            if x.isdigit():
                if x in catalog_index["pmids"]:
                    accs.add(f"PMID:{x}")
            else:
                if x.upper() in catalog_index["accessions"]:
                    accs.add(x.upper())

    direct = (item.get("accession") or "").upper()
    if direct and direct in catalog_index["accessions"]:
        accs.add(direct)
    pmid = str(item.get("pmid") or "").strip()
    if pmid and pmid in catalog_index["pmids"]:
        accs.add(f"PMID:{pmid}")

    reasons: list[str] = []
    verdict = "recommended"

    if accs:
        verdict = "already_in_catalog"
        reasons.append(f"Уже в каталоге: {', '.join(sorted(accs)[:5])}")

    if cfg.get("human_only") and verdict == "recommended":
        if not is_confirmed_human(item, blob):
            verdict = "filtered_out"
            reasons.append("Human only: не подтверждён Homo sapiens")
    elif cfg.get("reject_non_human") and NON_HUMAN.search(blob) and not is_confirmed_human(item, blob):
        verdict = "filtered_out"
        reasons.append("Не human (mouse/rat/rodent/бактерии)")

    plex = item.get("inferred_plex") or _infer_plex(blob)
    if item.get("experiment_type"):
        exp_plex = _infer_plex(str(item.get("experiment_type")))
        if exp_plex:
            plex = exp_plex

    if item.get("tmt_detected") is False and verdict == "recommended":
        if "tmt" not in blob_lower and "isobaric" not in blob_lower:
            verdict = "filtered_out"
            reasons.append("TMT не обнаружен в метаданных")

    if (
        verdict == "recommended"
        and LABEL_FREE_ONLY.search(blob)
        and "tmt" not in blob_lower
        and "isobaric" not in blob_lower
        and not item.get("experiment_type", "").upper().startswith("TMT")
    ):
        verdict = "filtered_out"
        reasons.append("Label-free, не TMT")
    allowed_plex = cfg.get("allowed_tmt_plexes") or list(ATLAS_TMT_PLEXES)
    if verdict == "recommended" and not plex_allowed(plex, cfg, blob=blob):
        if plex is not None:
            reasons.append(f"TMT plex {plex} не в атласе (только {allowed_plex})")
        else:
            reasons.append(f"TMT plex не определён (нужен {allowed_plex})")
        verdict = "filtered_out"

    design = _infer_sample_design(blob)
    allowed_designs = []
    if cfg.get("allow_healthy_only"):
        allowed_designs.append("healthy_only")
    if cfg.get("allow_cancer_only"):
        allowed_designs.append("cancer_only")
    if cfg.get("allow_case_control"):
        allowed_designs.append("case_control")
    if design == "unknown" and verdict == "recommended":
        reasons.append("Дизайн образцов не ясен — проверить healthy/cancer")
    elif design not in allowed_designs and design != "unknown" and verdict == "recommended":
        verdict = "filtered_out"
        reasons.append(f"Дизайн не подходит: {design}")

    if item.get("has_close_match") and verdict == "recommended":
        verdict = "duplicate_similar"
        sim = (item.get("similar_in_catalog") or [{}])[0]
        reasons.append(f"Очень похож на {sim.get('project_id')} (score {sim.get('score')})")

    has_project_id = bool(extracted.get("PXD") or extracted.get("PDC") or extracted.get("MSV") or extracted.get("IPX"))
    has_pmid = bool(extracted.get("PMID") or item.get("pmid"))
    if (
        verdict == "recommended"
        and REVIEW_ONLY.search(blob)
        and not has_project_id
        and not (item.get("accession") or "").startswith(("PXD", "PDC", "MSV", "IPX"))
    ):
        verdict = "filtered_out"
        reasons.append("Обзор/методы без номера проекта (PXD/PDC/MSV/IPX)")

    out = dict(item)
    out["verdict"] = verdict
    out["filter_reasons"] = reasons
    out["extracted_ids"] = extracted
    out["inferred_plex"] = plex
    if plex and re.search(r"tmtpro", blob_lower):
        out["tmt_label"] = f"TMTpro {plex}-plex"
    elif plex:
        out["tmt_label"] = f"TMT {plex}-plex"
    out["sample_design"] = design
    out["catalog_matches"] = sorted(accs)

    if verdict == "recommended":
        mq = assess_sample_material(out, blob)
        out.update(mq)
        if mq["qc_status"] == "requires_manual_check":
            out["verdict"] = "requires_manual_check"
            out["filter_reasons"] = reasons + mq["qc_reasons"]
        elif mq["qc_status"] == "rejected":
            out["verdict"] = "rejected"
            out["filter_reasons"] = reasons + mq["qc_reasons"]
        else:
            out["qc_status"] = "candidate"
    elif verdict not in ("already_in_catalog",):
        mq = assess_sample_material(out, blob)
        out.update(mq)

    return out


PROJECT_PREFIXES = ("PXD", "PDC", "MSV", "IPX")


def get_project_accession(item: dict) -> str | None:
    """Номер проекта (не PMID)."""
    acc = (item.get("accession") or item.get("project_accession") or "").strip().upper()
    if acc.startswith(PROJECT_PREFIXES):
        return acc
    extracted = item.get("extracted_ids") or {}
    for kind in ("PXD", "PDC", "MSV", "IPX"):
        for x in extracted.get(kind) or []:
            return str(x).upper()
    return None


def select_new_projects(
    items: list[dict],
    known_accessions: set[str],
    *,
    verdict: str = "recommended",
    qc_status: str = "candidate",
) -> list[dict]:
    """
    Только новые проекты с номером PXD/PDC/MSV/IPX, которых нет в каталоге.
    Статьи только с PMID — не включаются.
    """
    seen: set[str] = set()
    out: list[dict] = []
    for item in items:
        if item.get("verdict") != verdict:
            continue
        if verdict == "recommended" and item.get("qc_status") != qc_status:
            continue
        acc = get_project_accession(item)
        if not acc or acc in known_accessions or acc in seen:
            continue
        row = dict(item)
        row["project_accession"] = acc
        row["accession"] = acc
        row["is_new_project"] = True
        seen.add(acc)
        out.append(row)
    return out


def apply_filters(
    items: list[dict],
    df: pd.DataFrame,
    *,
    cfg: dict | None = None,
) -> dict[str, list[dict]]:
    index = build_catalog_index(df)
    fcfg = {**default_filter_config(), **(cfg or {})}
    classified = [classify_candidate(it, index, cfg=fcfg) for it in items]
    buckets: dict[str, list[dict]] = {
        "recommended": [],
        "requires_manual_check": [],
        "rejected": [],
        "already_in_catalog": [],
        "filtered_out": [],
        "duplicate_similar": [],
    }
    for it in classified:
        v = it.get("verdict", "recommended")
        buckets.setdefault(v, []).append(it)
    return buckets
