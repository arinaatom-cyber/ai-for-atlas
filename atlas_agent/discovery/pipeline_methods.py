"""Discovery pipeline toolchain for Methods section (site + manifest)."""
from __future__ import annotations

from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[2]
_STATS_PLANS = _REPO_ROOT / "data" / "stats_plans"


def _count_r_plans() -> int:
    if not _STATS_PLANS.is_dir():
        return 0
    return sum(1 for p in _STATS_PLANS.glob("*_stats.R") if p.is_file())


PIPELINE_STEPS: list[dict[str, str]] = [
    {
        "id": "catalog",
        "step": "1",
        "stage_ru": "Каталог атласа",
        "stage_en": "Atlas catalog",
        "language": "CSV",
        "script": "data/projects.csv",
        "agent": "—",
        "purpose_ru": "Мастер-таблица TMT-проектов (только чтение для Discovery)",
        "purpose_en": "Master TMT project table (read-only for Discovery)",
    },
    {
        "id": "scan",
        "step": "2",
        "stage_ru": "Сканирование репозиториев",
        "stage_en": "Repository scan",
        "language": "Python",
        "script": "run_discovery.py scan",
        "agent": "pride_scan / pdc_scan / massive_iprox",
        "purpose_ru": "PRIDE (карточка + статья), PDC/CPTAC, поиск по сайтам MassIVE и iProX",
        "purpose_en": "PRIDE (record + paper), PDC/CPTAC, MassIVE and iProX site search",
    },
    {
        "id": "filters",
        "step": "3",
        "stage_ru": "Rule-based фильтры",
        "stage_en": "Rule-based filters",
        "language": "Python",
        "script": "atlas_agent/discovery/filters.py",
        "agent": "filters",
        "purpose_ru": "Homo sapiens, TMT 7–18, ткань или раковая линия — иначе не в списке",
        "purpose_en": "Homo sapiens, TMT 7–18, tissue or cancer line — otherwise not listed",
    },
    {
        "id": "data_gate",
        "step": "4",
        "stage_ru": "Проверка файлов данных",
        "stage_en": "Data availability gate",
        "language": "Python",
        "script": "atlas_agent/discovery/qc_outputs.py",
        "agent": "discovery_scan",
        "purpose_ru": "Пример файла (.label.txt, matrix) — колонка «Данные / файлы»",
        "purpose_en": "Example file (.label.txt, matrix) — Data / files column",
    },
    {
        "id": "literature",
        "step": "5",
        "stage_ru": "Литература Europe PMC",
        "stage_en": "Europe PMC literature",
        "language": "Python",
        "script": "atlas_agent/discovery/abstract_reader.py",
        "agent": "abstract_reader",
        "purpose_ru": "Абстракт / статья: орган, материал, TMT; если статьи нет — карточка репозитория",
        "purpose_en": "Abstract / paper: organ, material, TMT; repository card if no paper",
    },
    {
        "id": "similarity",
        "step": "6",
        "stage_ru": "Коэффициент схожести",
        "stage_en": "Similarity score",
        "language": "Python",
        "script": "atlas_agent/revisor/similarity.py",
        "agent": "—",
        "purpose_ru": "Jaccard по токенам title/organ/disease vs каталог (0–100%)",
        "purpose_en": "Jaccard on title/organ/disease tokens vs catalog (0–100%)",
    },
    {
        "id": "evaluation",
        "step": "7",
        "stage_ru": "Вердикт строки",
        "stage_en": "Row verdict",
        "language": "Python",
        "script": "atlas_agent/discovery/evaluation/",
        "agent": "filters",
        "purpose_ru": "Candidate — прошло; иначе не в главном списке проектов",
        "purpose_en": "Candidate — passed; otherwise not in the main project list",
    },
    {
        "id": "cohorts",
        "step": "8",
        "stage_ru": "Когорты (литература)",
        "stage_en": "Literature cohorts",
        "language": "Python",
        "script": "scripts/run_cohort_literature.py",
        "agent": "literature",
        "purpose_ru": "Europe PMC: названия и похожие статьи, patient N если есть",
        "purpose_en": "Europe PMC: titles and similar papers, patient N when present",
    },
    {
        "id": "stats_r",
        "step": "9",
        "stage_ru": "Планы статистики атласа",
        "stage_en": "Atlas stats plans",
        "language": "R",
        "script": "data/stats_plans/*_stats.R",
        "agent": "—",
        "purpose_ru": "limma / DE для проектов уже в каталоге (не для новых кандидатов)",
        "purpose_en": "limma / DE for catalog projects (not new candidates)",
    },
    {
        "id": "publish",
        "step": "10",
        "stage_ru": "Публикация сайта",
        "stage_en": "Site publish",
        "language": "Python",
        "script": "scripts/enrich_and_publish_site.py",
        "agent": "—",
        "purpose_ru": "HTML-таблица, i18n RU/EN, GitHub Pages",
        "purpose_en": "HTML table, RU/EN i18n, GitHub Pages",
    },
]


def pipeline_for_manifest() -> dict[str, Any]:
    return {
        "steps": PIPELINE_STEPS,
        "similarity_method": "Jaccard token overlap (atlas_agent/revisor/similarity.py)",
        "example_data_file": "CPTAC4_Kids_First_AML_PNNL_Proteome.label.txt",
        "stats_plans_count": _count_r_plans(),
        "github_repo": "https://github.com/arinaatom-cyber/ai-for-atlas",
    }
