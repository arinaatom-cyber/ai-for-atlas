"""RU fallback strings for static HTML (mirrors site_assets/i18n.js PAGE.ru + SHARED)."""
from __future__ import annotations

# Shared keys (same in both languages or RU default)
_SHARED: dict[str, str] = {
    "brand_title": "Sirius Human TMT Proteome Atlas",
    "nav_atlas": "Атлас",
    "nav_discovery": "Discovery",
    "nav_cohorts": "Когорты",
    "nav_qc": "QC",
    "meta_updated": "Обновлено",
    "badge_readonly": "только чтение",
    "meta_candidates": "кандидатов",
    "meta_atlas_ids": "ID в атласе",
    "footer_github": "GitHub TMT",
    "footer_projects": "tmt-projects",
    "footer_live": "Live (GitHub Pages)",
    "filter_all": "Все",
    "filter_pride": "PRIDE",
    "filter_pdc": "PDC",
    "card_open": "Открыть",
    "card_json": "latest.json (API)",
    "th_link_open": "Открыть",
    "cell_empty": "—",
}

_RU: dict[str, str] = {
    "brand_sub": "Discovery · Когорты · QC · каталог read-only",
    "nav_home": "Главная",
    "nav_map": "Карта органов",
    "footer_policy": (
        "Каталог Excel не публикуется. На сайте — только новые кандидаты, литература и анализ."
    ),
    "portal_title": "Atlas Discovery Portal",
    "portal_lead": (
        "Мониторинг human TMT в PRIDE, PDC, MassIVE, iProX · ИИ-разбор абстрактов · "
        "крупные когорты в литературе"
    ),
    "card_discovery_title": "Полный анализ Discovery",
    "card_discovery_desc": "Новые PXD/PDC · Europe PMC · QC · доступность Result Files",
    "card_qc_title": "QC отчёт",
    "card_qc_desc": "Кандидаты / manual / rejected с ИИ-анализом и колонкой данных",
    "card_atlas_title": "Профиль атласа",
    "card_atlas_desc": "Статистика каталога: репозитории, органы, нозологии, TMT-плексы",
    "card_cohorts_title": "Крупные когорты",
    "card_cohorts_desc": "Протеомика и мульти-омика: большие patient cohorts, text mining абстрактов",
    "card_map_title": "Интерактивная карта",
    "card_map_desc": "TMT-проекты по органам · диплинки ?organ= · каталог read-only",
    "card_update_title": "Обновление данных",
    "card_update_desc": "Локально: python run_discovery.py scan · publish · export для GitHub Pages",
    "disc_title": "Discovery — полный анализ",
    "disc_lead": (
        "Новые human TMT проекты · семантический разбор абстрактов · QC материала · "
        "доступность данных"
    ),
    "disc_catalog_hidden": "каталог скрыт",
    "disc_catalog_n": "проектов в атласе",
    "atlas_title": "Профиль атласа",
    "atlas_lead": "Сводка Sirius Human TMT Proteome Atlas — только метаданные, без выгрузки каталога",
    "atlas_datasets": "датасетов",
    "atlas_publications": "уникальных ID",
    "atlas_repos": "Репозитории",
    "atlas_organs": "Топ органов / тканей",
    "atlas_diseases": "Топ нозологий",
    "atlas_tmt": "TMT-плексы",
    "atlas_keywords": "Ключевые слова поиска",
    "atlas_link": "Реестр на GitHub",
    "atlas_discovery": "Анализ новых наборов",
    "qc_title": "QC отчёт Discovery",
    "qc_lead": "Кандидаты · ручная проверка · отклонённые · технический фильтр",
    "cohorts_title": "Крупные когорты — протеомика и мульти-омика",
    "cohorts_lead": "Europe PMC + text mining: пациенты, N, омики, TMT",
}


def ru(key: str) -> str:
    if key in _RU:
        return _RU[key]
    if key in _SHARED:
        return _SHARED[key]
    return key
