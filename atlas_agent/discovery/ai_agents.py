"""Unified catalog of Discovery AI agents / LLM providers."""
from __future__ import annotations

from typing import Any

from atlas_agent.llm_client import list_llm_engines, resolve_engine

# Static roles on the Discovery site (no version strings in UI).
AGENT_CATALOG: list[dict[str, str]] = [
    {
        "id": "discovery_scan",
        "role_ru": "Сканирование репозиториев",
        "role_en": "Repository scan",
        "detail_ru": "PRIDE, PDC, MassIVE, iProX — rule-based фильтры TMT >6-plex",
        "detail_en": "PRIDE, PDC, MassIVE, iProX — rule-based TMT >6-plex filters",
    },
    {
        "id": "abstract_reader",
        "role_ru": "ИИ-разбор абстрактов",
        "role_en": "Abstract AI reader",
        "detail_ru": "Europe PMC: смысл, материал, TMT-плекс, atlas_fit",
        "detail_en": "Europe PMC: meaning, material, TMT plex, atlas_fit",
    },
    {
        "id": "evaluation",
        "role_ru": "Оценка строк таблицы",
        "role_en": "Table row evaluation",
        "detail_ru": "Tier A–D, evidence chain, display_fit (rules + LLM trust)",
        "detail_en": "Tier A–D, evidence chain, display_fit (rules + LLM trust)",
    },
    {
        "id": "cohort_literature",
        "role_ru": "Когорты из литературы",
        "role_en": "Literature cohorts",
        "detail_ru": "Europe PMC text mining, patient cohorts",
        "detail_en": "Europe PMC text mining, patient cohorts",
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
