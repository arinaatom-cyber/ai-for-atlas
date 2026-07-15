"""
Поштучный (postрочный) аудит: читает КАЖДОЕ поле строки каталога,
сверяет Organ / Tissue / Sample Type / Cell lines / Disease / счётчики образцов.
"""
from __future__ import annotations

import math
import re
from typing import Any

from atlas_agent.catalog.organ_classify import (
    canon_disease,
    classify_all_organs,
    classify_organ,
    hint_organs_from_text,
    is_healthy,
    map_project,
    material_bucket,
    normalize_sample_type,
    pick_organ_raw,
    split_organ_parts,
    trim_metastasis_organs,
)

# Колонки в порядке чтения строки (как в Excel TMT ATLAS)
ROW_READ_ORDER: list[str] = [
    "Database",
    "Project ID",
    "PMID",
    "Title",
    "Total Samples",
    "preCancer",
    "Case Cancer Untreated",
    "Case Cancer Treated",
    "Control Healthy",
    "Healthy Treated",
    "Patients / donors",
    "Tissue Cell Type Detailed",
    "Sample Type",
    "Tissue",
    "Organ",
    "Tumor Type",
    "Cell Line Name",
    "Cell Line Cancer;Normal",
    "Cell Line Organ",
    "Tumor type for cell lines",
    "Tissue for cell lines",
    "Disease",
    "Disease Subtype",
    "Experimental Design",
    "Short Description",
    "Platform MS (Unified)",
    "TMT Label (Unified)",
    "Proteins Quantified",
    "TMT Channels Used",
    "TMT Channels Comparison",
    "TMT Additional Channels",
    "Samples Original N",
    "Samples Used N",
    "Normalization Strategy",
    "Result Files",
    "URL",
    "Main_Finding",
]

ORGAN_BEARING = {
    "Organ": "curator (карта)",
    "Tissue": "Tissue",
    "Tissue Cell Type Detailed": "Detail",
    "Cell Line Organ": "Cell Line Organ",
    "Tissue for cell lines": "Tissue for CL",
    "Cell Line Name": "Cell Line Name",
    "Tumor type for cell lines": "CL Tumor Type",
    "Title": "Title",
    "Short Description": "Description",
    "Experimental Design": "Design",
    "Disease": "Disease",
    "Disease Subtype": "Subtype",
}

CELL_LINE_KNOWN: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"a[- ]?431", re.I), "Skin"),
    (re.compile(r"mcf[- ]?7|mcf7", re.I), "Breast"),
    (re.compile(r"u[- ]?251|u251", re.I), "Brain"),
    (re.compile(r"hcc827|nci-h322|nci-h358|a549|h1299", re.I), "Lung"),
    (re.compile(r"hep\s*g2|hepg2|sk-hep|huh-?7", re.I), "Liver"),
    (re.compile(r"hek293|hela|hs578t", re.I), "Other"),  # mixed — flag
    (re.compile(r"jurkat|k562|thp-?1|hl-?60", re.I), "Blood"),
    (re.compile(r"sw480|sw620|hct.?116|km12", re.I), "Colon"),
    (re.compile(r"ovcar|caov|ov-?90", re.I), "Ovary"),
    (re.compile(r"pc-?3|ln?cap|du145", re.I), "Prostate"),
]


def _s(v: Any) -> str:
    if v is None:
        return ""
    if isinstance(v, float) and math.isnan(v):
        return ""
    return str(v).strip()


def organs_from_field(col: str, raw: str, *, tumor_type: str) -> list[str]:
    """Органы, явно/readable из одного поля."""
    if not raw:
        return []
    if col == "Cell Line Name":
        found: set[str] = set()
        for part in re.split(r"[;\n]+", raw):
            part = part.strip()
            if not part:
                continue
            for pat, organ in CELL_LINE_KNOWN:
                if pat.search(part):
                    found.add(organ)
            found.update(hint_organs_from_text(part))
        return sorted(found)
    if col in ("Organ", "Tissue", "Tissue Cell Type Detailed", "Cell Line Organ", "Tissue for cell lines"):
        parts = split_organ_parts(raw)
        organs: set[str] = set()
        for p in parts:
            o = classify_organ(p)
            if o != "Other":
                organs.add(o)
            else:
                organs.update(hint_organs_from_text(p))
        if not organs:
            organs.update(hint_organs_from_text(raw))
        return sorted(trim_metastasis_organs(sorted(organs), tumor_type))
    return sorted(set(hint_organs_from_text(raw)))


def _num(v: Any) -> float | None:
    s = _s(v)
    if not s:
        return None
    try:
        return float(s.replace(",", ""))
    except ValueError:
        return None


def read_row_fields(row: dict[str, Any]) -> list[tuple[str, str]]:
    """Все непустые поля строки в порядке ROW_READ_ORDER, затем прочие."""
    out: list[tuple[str, str]] = []
    seen: set[str] = set()
    for col in ROW_READ_ORDER:
        val = _s(row.get(col))
        if val:
            out.append((col, val))
            seen.add(col)
    for col, v in row.items():
        if col in seen:
            continue
        val = _s(v)
        if val:
            out.append((col, val))
    return out


def audit_row_deep(row: dict[str, Any], *, row_index: int) -> dict[str, Any]:
    """Полный построчный разбор одной строки Excel."""
    fields = read_row_fields(row)
    mapped = map_project(row)
    pid = mapped["pid"]
    tumor_type = mapped["tumor_type"]
    sample_type = mapped["sample_type"]
    issues: list[dict[str, str]] = []

    field_organs: dict[str, dict[str, Any]] = {}
    for col, label in ORGAN_BEARING.items():
        raw = _s(row.get(col))
        if not raw:
            continue
        orgs = organs_from_field(col, raw, tumor_type=tumor_type)
        field_organs[col] = {"label": label, "raw": raw, "organs": orgs}

    organ_curator = _s(row.get("Organ"))
    map_organs = set(mapped["organs"])
    curator_parsed = set(
        trim_metastasis_organs(classify_all_organs(organ_curator), tumor_type)
        if organ_curator
        else []
    )

    # --- 1. Organ column vs map ---
    if not organ_curator:
        fb = map_organs - {"Other"}
        if fb:
            issues.append({
                "code": "organ_empty",
                "field": "Organ",
                "severity": "warn",
                "msg": f"Organ пуст — карта из fallback: {sorted(fb)} (заполните Organ в Excel)",
            })
        else:
            issues.append({
                "code": "organ_empty",
                "field": "Organ",
                "severity": "error",
                "msg": "Organ пуст и fallback не дал органа — только Other/Unknown",
            })
    elif curator_parsed != map_organs:
        issues.append({
            "code": "organ_map",
            "field": "Organ",
            "msg": f"Organ «{organ_curator[:80]}» → {sorted(curator_parsed)}; карта → {sorted(map_organs)}",
        })

    # --- 2. Каждое organ-поле vs curator Organ (если Organ задан) ---
    if organ_curator and not re.match(r"^(multiple organs|multi-organ)", organ_curator, re.I):
        enumerated = len(split_organ_parts(organ_curator)) >= 5
        for col, info in field_organs.items():
            if col == "Organ":
                continue
            fo = set(info["organs"]) - {"Other", "Multiple_Organs"}
            if not fo:
                continue
            if enumerated and col in ("Tissue Cell Type Detailed", "Tissue"):
                continue
            # Curator single-organ: контекст не должен противоречить
            if len(curator_parsed) == 1:
                cur = next(iter(curator_parsed))
                if fo and fo != {cur} and not fo.issubset(curator_parsed):
                    issues.append({
                        "code": "field_vs_organ",
                        "field": col,
                        "msg": f"{info['label']}: {sorted(fo)} не совпадает с Organ={cur} "
                        f"(«{info['raw'][:60]}»)",
                    })
            elif curator_parsed and not fo.issubset(curator_parsed | {"Multiple_Organs"}):
                extra = fo - curator_parsed
                if extra:
                    issues.append({
                        "code": "field_extra_organ",
                        "field": col,
                        "msg": f"{info['label']} упоминает {sorted(extra)}, нет в Organ "
                        f"({sorted(curator_parsed)})",
                    })

    # --- 3. Sample Type ↔ все поля ---
    detail = _s(row.get("Tissue Cell Type Detailed")).lower()
    cl_name = _s(row.get("Cell Line Name"))
    cl_organ = _s(row.get("Cell Line Organ"))
    tissue_col = _s(row.get("Tissue"))

    if sample_type == "Cell Lines":
        if not cl_name and not re.search(r"cell line", detail):
            issues.append({
                "code": "cl_missing_name",
                "field": "Cell Line Name",
                "msg": "Sample Type=Cell Lines, но Cell Line Name пуст и в Detail нет 'cell line'",
            })
        if not cl_organ and not organ_curator:
            issues.append({
                "code": "cl_missing_organ",
                "field": "Cell Line Organ",
                "msg": "Cell Lines без Cell Line Organ и без Organ",
            })
    elif sample_type == "Tissue":
        if cl_name and not re.search(r"cell line|organoid|xenograft|pdx", detail, re.I):
            issues.append({
                "code": "tissue_has_cl_name",
                "field": "Cell Line Name",
                "msg": f"Sample Type=Tissue, но Cell Line Name заполнен: «{cl_name[:50]}»",
            })
        if tissue_col and organ_curator:
            t_org = set(organs_from_field("Tissue", tissue_col, tumor_type=tumor_type))
            if t_org and curator_parsed and not (t_org & curator_parsed):
                issues.append({
                    "code": "tissue_vs_organ",
                    "field": "Tissue",
                    "msg": f"Tissue→{sorted(t_org)} не пересекается с Organ→{sorted(curator_parsed)}",
                })
    elif sample_type not in ("Cell Lines", "Tissue", "Unknown"):
        if sample_type == "Primary cells" and not organ_curator:
            issues.append({
                "code": "primary_no_organ",
                "field": "Organ",
                "msg": "Primary cells — нужен Organ (напр. Hematopoietic system → Blood)",
            })

    # --- 4. Tumor Type / Disease / healthy ---
    disease = _s(row.get("Disease"))
    subtype = _s(row.get("Disease Subtype"))
    healthy = mapped["healthy"]
    canon = canon_disease(tumor_type)

    if healthy and re.search(r"carcinoma|cancer|tumor|sarcoma|leukemia|lymphoma", tumor_type, re.I):
        issues.append({
            "code": "healthy_vs_tumor",
            "field": "Tumor Type",
            "msg": f"Tumor Type похож на cancer («{tumor_type[:50]}»), но классифицирован как normal",
        })
    if not healthy and _s(row.get("Tumor Type")).lower() in ("normal", "healthy"):
        if not re.search(r"adjacent|nat|non-tumor|non tumor", detail, re.I):
            issues.append({
                "code": "cancer_vs_normal_tt",
                "field": "Tumor Type",
                "msg": "Tumor Type=Normal/Healthy, но проект не marked healthy",
            })

    case_u = _num(row.get("Case Cancer Untreated")) or 0
    case_t = _num(row.get("Case Cancer Treated")) or 0
    pre = _num(row.get("preCancer")) or 0
    ctrl = _num(row.get("Control Healthy")) or 0
    ctrl_t = _num(row.get("Healthy Treated")) or 0
    total = _num(row.get("Total Samples"))
    donors = _num(row.get("Patients / donors"))
    sum_parts = case_u + case_t + pre + ctrl + ctrl_t
    if total and sum_parts and abs(total - sum_parts) > max(2, total * 0.15):
        issues.append({
            "code": "sample_count",
            "field": "Total Samples",
            "msg": f"Total={int(total)} vs сумма колонок Case/Control={int(sum_parts)}",
        })

    # --- 5. pick_organ_raw trace ---
    organ_raw = pick_organ_raw(row)
    if organ_raw == "Unknown" and organ_curator:
        issues.append({
            "code": "organ_raw_unknown",
            "field": "Organ",
            "msg": f"pick_organ_raw=Unknown при Organ=«{organ_curator[:60]}»",
        })

    # --- 6. Multi-organ / pan ---
    if len(map_organs) >= 3 and "Multiple_Organs" not in map_organs and not re.match(
        r"^multiple organs", organ_curator, re.I
    ):
        issues.append({
            "code": "multi_no_tag",
            "field": "Organ",
            "msg": f"{len(map_organs)} органов на карте без Multiple_Organs: {sorted(map_organs)}",
        })

    sev = "ok"
    for it in issues:
        it.setdefault("severity", "error" if it["code"] in ("organ_map", "organ_empty", "organ_raw_unknown") else "warn")
        if it["severity"] == "error":
            sev = "error"
        elif it["severity"] == "warn" and sev == "ok":
            sev = "warn"

    return {
        "row_index": row_index,
        "pid": pid,
        "database": _s(row.get("Database")),
        "title": _s(row.get("Title"))[:140],
        "fields": fields,
        "field_organs": field_organs,
        "mapped": mapped,
        "material": mapped["material"],
        "healthy": healthy,
        "canon_disease": canon,
        "organ_raw": organ_raw,
        "issues": issues,
        "status": sev,
        "issue_count": len(issues),
    }


def summarize_row_audits(records: list[dict[str, Any]]) -> dict[str, Any]:
    mat = {"clC": 0, "clN": 0, "tisC": 0, "tisN": 0, "other": 0}
    by_status: dict[str, int] = {}
    codes: dict[str, int] = {}
    pids: dict[str, list[int]] = {}

    for rec in records:
        by_status[rec["status"]] = by_status.get(rec["status"], 0) + 1
        m = rec["material"]
        mat[m if m in mat else "other"] = mat.get(m if m in mat else "other", 0) + 1
        pids.setdefault(rec["pid"], []).append(rec["row_index"])
        for iss in rec["issues"]:
            codes[iss["code"]] = codes.get(iss["code"], 0) + 1

    dup_pid = {p: rows for p, rows in pids.items() if len(rows) > 1}
    return {
        "rows": len(records),
        "unique_pids": len(pids),
        "duplicate_pid_rows": dup_pid,
        "by_status": by_status,
        "material_buckets": mat,
        "issue_codes": dict(sorted(codes.items(), key=lambda x: -x[1])),
    }


def format_row_markdown(rec: dict[str, Any]) -> list[str]:
    """Markdown-блок для одной строки (полный дамп)."""
    lines = [
        f"## Строка {rec['row_index']} · {rec['pid']} ({rec['database']}) · **{rec['status'].upper()}**",
        "",
        f"**Title:** {rec['title']}",
        "",
        "### Все поля строки",
        "",
        "| Колонка | Значение |",
        "|---------|----------|",
    ]
    for col, val in rec["fields"]:
        v = val.replace("|", "\\|").replace("\n", " ")
        if len(v) > 200:
            v = v[:197] + "…"
        lines.append(f"| {col} | {v} |")

    lines.extend(["", "### Органы по полям (поштучно)", ""])
    if rec["field_organs"]:
        lines.append("| Поле | Органы | Фрагмент |")
        lines.append("|------|--------|----------|")
        for col, info in rec["field_organs"].items():
            orgs = ", ".join(info["organs"]) or "—"
            raw = info["raw"].replace("|", "\\|")[:80]
            lines.append(f"| {info['label']} | {orgs} | {raw} |")
    else:
        lines.append("_Нет organ-bearing полей_")

    m = rec["mapped"]
    lines.extend([
        "",
        "### Итог для карты",
        "",
        f"- **pick_organ_raw:** `{rec['organ_raw'][:120]}`",
        f"- **Органы на карте:** {', '.join(m['organs'])}",
        f"- **Sample Type:** {m['sample_type']} → `{m['material']}`",
        f"- **Healthy:** {m['healthy']} · **Tumor Type:** {m['tumor_type'][:60]}",
        f"- **Disease group:** {rec['canon_disease'][:50]}",
        "",
    ])

    if rec["issues"]:
        lines.append("### Замечания")
        lines.append("")
        for iss in rec["issues"]:
            lines.append(f"- **[{iss.get('field', '?')}]** `{iss['code']}`: {iss['msg']}")
        lines.append("")
    else:
        lines.append("### Замечания\n\n✓ Построчная сверка без замечаний.\n")

    lines.append("---")
    lines.append("")
    return lines
