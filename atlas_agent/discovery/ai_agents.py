"""Unified catalog of Discovery AI agents / LLM providers."""
from __future__ import annotations

from typing import Any

from atlas_agent.llm_client import list_llm_engines, resolve_engine

# Static roles on the Discovery site (no version strings in UI).
AGENT_CATALOG: list[dict[str, str]] = [
    {
        "id": "pride_scan",
        "role_ru": "Поиск в PRIDE",
        "role_en": "PRIDE search",
        "detail_ru": (
            "Архив PRIDE: новые TMT-проекты вне каталога. Смотрим, есть ли TMT-плекс (7–18). "
            "Если плекс или материал не в карточке — читаем описание проекта и связанную статью."
        ),
        "detail_en": (
            "PRIDE Archive: new TMT projects outside the catalog. Check TMT plex (7–18). "
            "If plex or material is missing from the record, read the project description and the linked paper."
        ),
    },
    {
        "id": "pdc_scan",
        "role_ru": "Поиск в PDC (CPTAC)",
        "role_en": "PDC (CPTAC) search",
        "detail_ru": (
            "В PDC болезнь, орган и TMT уже в метаданных. Те же правила включения, что для PRIDE: "
            "не каждая PDC-запись попадает в список."
        ),
        "detail_en": (
            "PDC already carries disease, organ, and TMT in metadata. Same inclusion rules as PRIDE: "
            "not every PDC record is listed."
        ),
    },
    {
        "id": "massive_iprox",
        "role_ru": "MassIVE и iProX",
        "role_en": "MassIVE and iProX",
        "detail_ru": "Поиск по сайтам MassIVE и iProX теми же словами: TMT, human, cancer.",
        "detail_en": "Site search on MassIVE and iProX with the same TMT / human / cancer keywords.",
    },
    {
        "id": "abstract_reader",
        "role_ru": "Чтение абстрактов и статей",
        "role_en": "Abstract and paper reader",
        "detail_ru": (
            "По PMID открываем PubMed / Europe PMC: короткий текст, орган, материал, TMT. "
            "Если статьи нет — читаем карточку PRIDE или PDC."
        ),
        "detail_en": (
            "From PMID, open PubMed / Europe PMC: short text, organ, material, TMT. "
            "If there is no paper, read the PRIDE or PDC project card."
        ),
    },
    {
        "id": "filters",
        "role_ru": "Отбор по правилам",
        "role_en": "Rule-based selection",
        "detail_ru": (
            "Homo sapiens, TMT 7–18, ткань или раковая клеточная линия. "
            "Не прошло проверку — не показываем как проект."
        ),
        "detail_en": (
            "Homo sapiens, TMT 7–18, tissue or cancer cell line. "
            "Failed checks are not shown as projects."
        ),
    },
    {
        "id": "literature",
        "role_ru": "Статьи (Europe PMC)",
        "role_en": "Papers (Europe PMC)",
        "detail_ru": "Поиск по названиям и похожим публикациям в Europe PMC — не замена ID репозитория.",
        "detail_en": "Search by title and similar papers in Europe PMC — not a substitute for a repository ID.",
    },
]

LLM_PROVIDER_CATALOG: list[dict[str, str]] = [
    {"id": "zai", "name": "Z.AI GLM", "env": "ZAI_API_KEY", "trust": "high"},
    {"id": "qwen_cloud", "name": "Qwen (DashScope)", "env": "DASHSCOPE_API_KEY", "trust": "high"},
    {"id": "claude", "name": "Claude", "env": "ANTHROPIC_API_KEY", "trust": "high"},
    {"id": "grok", "name": "Grok (xAI)", "env": "XAI_API_KEY", "trust": "high"},
    {"id": "ollama", "name": "Ollama (local)", "env": "—", "trust": "medium"},
    {"id": "gpt4all", "name": "GPT4All (local)", "env": "—", "trust": "low"},
    {"id": "local_rules", "name": "Regex / rules", "env": "—", "trust": "rules"},
]


def llm_snapshot(cfg: dict[str, Any] | None = None) -> dict[str, Any]:
    """Runtime LLM status for manifest and site (no Python/platform versions)."""
    llm = (cfg or {}).get("llm") or {}
    prefer_cloud = bool(llm.get("prefer_cloud", True))
    engines = list_llm_engines(prefer_cloud=prefer_cloud, model=llm.get("model"))
    active = resolve_engine(
        str(llm.get("provider") or "auto"),
        llm.get("base_url"),
        prefer_cloud=prefer_cloud,
        model=llm.get("model"),
    )
    available = [e for e in engines if e.get("available")]
    return {
        "active_engine": active,
        "prefer_cloud": prefer_cloud,
        "provider_setting": str(llm.get("provider") or "auto"),
        "engines": engines,
        "available_count": len(available),
        "available_labels": [e["label"] for e in available],
    }


def agents_for_site(cfg: dict[str, Any] | None = None) -> dict[str, Any]:
    snap = llm_snapshot(cfg)
    active_label = next(
        (e["label"] for e in snap["engines"] if e.get("active")),
        snap["active_engine"],
    )
    return {
        "pipeline_agents": AGENT_CATALOG,
        "llm_providers": LLM_PROVIDER_CATALOG,
        "llm_active": active_label,
        "llm_available": snap["available_labels"],
        "llm_active_engine": snap["active_engine"],
    }
