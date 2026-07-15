"""Normalize discovery scan payloads to English before static site publish."""
from __future__ import annotations

import re
from typing import Any

# Legacy Russian strings from older scans / filters (exact or substring)
_RU_TO_EN: list[tuple[str, str]] = [
    ("Материал соответствует критериям атласа", "Material matches atlas criteria"),
    ("Дизайн образцов не ясен — проверить healthy/cancer", "Sample design unclear — check healthy/cancer labels"),
    ("По смыслу похоже на TMT ATLAS — проверить вручную (PRIDE/PDC), номер в абстракте не ищем",
     "Semantically similar to TMT ATLAS — verify manually in PRIDE/PDC (accession not extracted from abstract)"),
    ("PDC: сверить с CPTAC pipeline; проверить PSM vs protein matrix",
     "PDC: compare with CPTAC pipeline; check PSM vs protein matrix"),
    ("CCLE: часто cell-line TMT — учесть batch по плексам", "CCLE: often cell-line TMT — watch batch by plex"),
    ("GTEx: tissue reference — сопоставить с organ-level atlas", "GTEx: tissue reference — map to organ-level atlas"),
    ("Ваши plex:", "Atlas plexes:"),
    ("Добавить в CSV только после ручной проверки (projects.csv не меняется автоматически)",
     "Add to CSV only after manual review (projects.csv is never modified automatically)"),
    ("Похож на ваш", "Similar to catalog"),
    ("Уже в каталоге:", "Already in catalog:"),
    ("Не human (mouse/rat/rodent/бактерии)", "Not human (mouse/rat/rodent/bacteria)"),
    ("Human only: не подтверждён Homo sapiens", "Human only: Homo sapiens not confirmed"),
    ("TMT не обнаружен в метаданных", "TMT not detected in metadata"),
    ("Label-free, не TMT", "Label-free, not TMT"),
    ("TMT plex", "TMT plex"),  # partial — rest often English already
    ("не в атласе (только", "not in atlas (allowed:"),
    ("не определён (нужен", "unknown (need"),
    ("Дизайн не подходит:", "Design not allowed:"),
    ("Очень похож на", "Very similar to"),
    ("Фосфопротеомика", "Phosphoproteomics"),
    ("нужен proteome белков", "need protein-level proteome"),
]

_CYRILLIC = re.compile(r"[А-Яа-яЁё]")


def translate_legacy_text(text: str) -> str:
    s = str(text or "").strip()
    if not s or not _CYRILLIC.search(s):
        return s
    for ru, en in _RU_TO_EN:
        if ru in s:
            s = s.replace(ru, en)
    if _CYRILLIC.search(s):
        return "Legacy note — re-run discovery scan for English metadata"
    return s


def _translate_list(values: list[Any] | None) -> list[str]:
    out: list[str] = []
    for v in values or []:
        t = translate_legacy_text(str(v))
        if t and t not in out:
            out.append(t)
    return out


def sanitize_discovery_item(item: dict[str, Any]) -> None:
    """In-place English cleanup for one discovery item."""
    from atlas_agent.discovery.fit_rules import apply_literature_exclusions, sanitize_summary

    item["qc_reasons"] = _translate_list(item.get("qc_reasons"))
    item["filter_reasons"] = _translate_list(item.get("filter_reasons"))
    item["processing_tips"] = _translate_list(item.get("processing_tips"))

    ai = item.get("abstract_ai")
    if isinstance(ai, dict):
        if ai.get("summary_en"):
            ai["summary_en"] = sanitize_summary(ai["summary_en"])
            ai.pop("summary_ru", None)
        elif ai.get("summary_ru"):
            ai["summary_en"] = sanitize_summary(ai["summary_ru"])
            if not ai["summary_en"]:
                ai.pop("summary_ru", None)
    apply_literature_exclusions(item)
    ai = item.get("abstract_ai")
    if isinstance(ai, dict):
        ai.pop("atlas_fit_score", None)
    if item.get("summary_ru") and not item.get("summary_en"):
        if not _CYRILLIC.search(str(item["summary_ru"])):
            item["summary_en"] = sanitize_summary(item["summary_ru"])


def sanitize_report_for_site(report: dict[str, Any]) -> dict[str, Any]:
    """Ensure all user-visible scan fields are English before HTML/JSON publish."""
    from atlas_agent.discovery.cohort_literature import build_description_en
    from atlas_agent.viz.portal_index import format_finding_note

    buckets = (
        "candidates",
        "new_projects",
        "manual_check",
        "rejected_material",
        "filtered_out",
        "literature_semantic",
        "publications_analyzed",
    )
    for key in buckets:
        for item in report.get(key) or []:
            sanitize_discovery_item(item)
            item["finding_note"] = format_finding_note(item)

    for item in report.get("cohort_literature") or []:
        item["description_en"] = build_description_en(item)
        item.pop("description_ru", None)

    for pub in report.get("publications_analyzed") or []:
        sanitize_discovery_item(pub)
        if pub.get("data_hint"):
            pub["data_hint"] = translate_legacy_text(str(pub["data_hint"]))

    return report
