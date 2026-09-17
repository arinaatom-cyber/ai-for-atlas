#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from docx import Document
from docx.oxml import OxmlElement
from docx.text.paragraph import Paragraph

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DOCX = Path(
    r"C:\Users\Arina1996\Desktop\статья тмт атлас\Human Cancser Assosiated TMT Proteome Atlas.docx"
)

SECTION_27 = [
    "2.7. Трёхуровневая архитектура интеграции: Presence, Abundance, Effect",
    "",
    "Прямое объединение абсолютных или относительных TMT-интенсивностей из независимых исследований методологически некорректно: количественные шкалы, схемы нормализации, состав референсного канала, глубина протеома и экспериментальный дизайн различаются между датасетами и репозиториями. Для систематического повторного использования атласа без ложной сопоставимости была реализована трёхуровневая схема аналитической интеграции.",
    "",
    "Presence layer (слой присутствия). На этом уровне для каждого датасета формируется бинарная или полуколичественная матрица «белок × набор данных», отражающая факт детекции белка при заданном пороге FDR. Слой не предполагает сравнения абсолютных уровней экспрессии между когортами и допускает включение гетерогенных дизайнов: paired tumor–normal, unpaired case–control, case-only, normal-only, клеточные линии и reference-channel эксперименты.",
    "",
    "Abundance layer (слой относительной обилия). Интеграция на уровне относительных количественных значений допускается только при согласованном типе биоматериала, единой или сопоставимой схеме TMT-плекса (TMT10, TMT11, TMT12, TMT16, TMTpro16, TMTpro18), документированной нормализации и отсутствии смешения протеомного и фосфопротеомного слоёв в одной матрице.",
    "",
    "Effect layer (слой эффектов). Количественные контрасты рассчитываются внутри каждого датасета с учётом его экспериментального дизайна; межкогортное сопоставление выполняется через ранговые мета-аналитические процедуры, а не через прямое усреднение reporter-ion intensities между независимыми исследованиями.",
    "",
    "Каждому проекту присваивается допустимый набор аналитических слоёв по метаданным (материал, дизайн, TMT-plex, контроли, quant files). Поле PMID_group сохраняет независимые когорты одной публикации как отдельные аналитические единицы.",
]

METHODS_HEADINGS = (
    ("Общая стратегия", "2.1. Источники данных и общая стратегия курирования"),
    ("Критерии включения", "2.1.1. Критерии включения"),
    ("Критерии исключения", "2.1.2. Критерии исключения"),
    ("Конвейер автоматизированной фильтрации PRIDE", "2.2. Конвейер автоматизированной фильтрации PRIDE"),
    ("Конвейер фильтрации MassIVE", "2.3. Конвейер фильтрации MassIVE"),
    ("Обработка iProX и PDC/CPTAC", "2.4. Обработка iProX и PDC/CPTAC"),
    ("Сопоставление PXD, PMID и DOI", "2.5. Сопоставление PXD, PMID и DOI"),
    (
        "Стандартизация метаданных, файловая структура и аннотация",
        "2.6. Стандартизация метаданных, файловая структура и аннотация",
    ),
)

TEXT_FIXES = (
    ("????и TMT", "истории развития реагентов TMT"),
    ("исходя из ????", "исходя из истории развития реагентов"),
    ("а для PRIDE э совпадение", "а для PRIDE — при совпадении"),
    (
        "(TMT10, TMT11, TMTpro16, TMTpro18)",
        "(TMT10, TMT11, TMT12, TMT16, TMTpro16, TMTpro18)",
    ),
    (
        "TMT10, TMT11, TMTpro16), документированной",
        "TMT10, TMT11, TMT12, TMT16, TMTpro16, TMTpro18), документированной",
    ),
)

SECTION_28 = [
    "2.8. Автоматизированный мониторинг протеомных репозиториев и литературы для расширения атласа",
    "",
    "Для систематического пополнения Human Cancser Assosiated TMT Proteome Atlas развёрнут конвейер автоматизированного обнаружения (discovery pipeline) в режиме read-only относительно эталонного каталога (`project of Proteomics.xlsx`, лист «TMT ATLAS»; `data/projects.csv` — программное зеркало/fallback; n = 123 accession). Каталог используется только для дедупликации и семантического контекста; конвейер не изменяет мастер-таблицу — окончательное включение выполняется экспертом.",
    "",
    "2.8.1. Архитектура и источники данных",
    "",
    "Единый прогон опрашивает PRIDE Archive (REST API v3), NCI Proteomic Data Commons (GraphQL, uiStudySummary), MassIVE, iProX и Europe PMC (2024–2026). Идентификаторы нормализуются (PXD, PDC, MSV, IPX) и сверяются с каталогом. Код: репозиторий github.com/arinaatom-cyber/ai-for-atlas, скрипт run_discovery.py.",
    "",
    "2.8.2. Критерии отбора наборов данных",
    "",
    "Иерархия фильтров: (i) accession уже в каталоге → «already in catalog»; (ii) Homo sapiens; (iii) TMT/isobaric 7–18 plex (включая TMTpro16/18; отклонение TMT6 и ≤6-plex); (iv) exclusion engine (mouse/xenograft-only, phospho-only, peptide-only, method papers); (v) программное исключение CPTAC/Broad/CCLE; (vi) sample design QC (case–control, paired, cancer-only или manual). Ранжирование репозиторных tier A–D выполняется по наличию protein-level quant table и дизайну — без LLM.",
    "",
    "2.8.3. Семантический анализ публикаций с использованием языковой модели",
    "",
    "Языковая модель в конвейере Discovery используется только для семантической оценки публикаций, предварительно найденных программными средствами. Поиск проектов в PRIDE, PDC, MassIVE и iProX, сопоставление с уже включёнными accession, применение формальных критериев отбора и оценка репозиторных записей выполняются отдельными детерминированными модулями. Языковая модель не изменяет основной каталог и не используется для генерации или извлечения идентификаторов PXD, PDC, MSV или IPX.",
    "",
    "Основной каталог (`project of Proteomics.xlsx`, лист «TMT ATLAS»; `data/projects.csv` используется как программное зеркало/fallback) загружается в режиме read-only. Перед анализом литературы из него автоматически формируется catalog_profile, характеризующий уже курированный массив данных. Профиль содержит наиболее представленные органы, нозологии и TMT-схемы, а также примеры экспериментальных дизайнов, включая парные tumor/adjacent-normal исследования, клинические когорты и панели опухолевых клеточных линий. Таким образом, новая публикация оценивается относительно фактической структуры Human Cancer-Associated TMT Proteome Atlas, а не только по наличию отдельных ключевых слов.",
    "",
    "Литературный поиск выполняется через Europe PMC для публикаций начиная с 2023 года. После предварительной программной фильтрации в модуль семантического анализа передаются не более 25 публикаций за один запуск (abstract_llm_max = 25). Для каждой записи языковой модели предоставляются название статьи, абстракт и доступный текст Data Availability. В текущей реализации длина передаваемого названия ограничена 500 символами, абстракта — 3500 символами, а Data Availability — 1500 символами. Полные тексты публикаций моделью автоматически не анализируются.",
    "",
    "LLM-backend реализован как заменяемый компонент. При режиме provider = auto программное обеспечение может использовать Z.AI, Qwen Cloud, Claude, локальный Ollama или GPT4All в зависимости от доступности соответствующего backend; при отсутствии доступной языковой модели используется rule-based fallback. В пилотном прогоне, результаты которого представлены ниже, фактически использовалась локальная модель Qwen2.5-3B (qwen2.5:3b) через Ollama, что было непосредственно зарегистрировано в отчёте Discovery как abstract_reader = ollama:qwen2.5:3b. Для OpenAI-compatible интерфейса использовалась температура 0,3. Хотя глобальное значение max_tokens в конфигурации составляет 2048, для анализа абстрактов оно программно ограничивается максимум 900 генерируемыми токенами.",
    "",
    "Системная инструкция определяет модель как вспомогательный инструмент куратора TMT-протеомного атласа и требует формировать ответ только на основании предоставленного текста. Модели явно запрещено искать или возвращать repository accession. Ответ запрашивается в структурированном JSON-формате и включает поля atlas_fit (yes, maybe или no), atlas_fit_score, semantic_evidence, similar_atlas_theme, organism, tmt, material, human_suitable, material_suitable и summary_ru. В инструкции также задаётся консервативная интерпретация публикаций и указано исключать исследования с TMT6/≤6-plex, phosphoproteomics-only и peptide-only quantification.",
    "",
    "Полученный от модели ответ программно разбирается как JSON. Если модель недоступна, абстракт отсутствует или ответ не удаётся интерпретировать как структурированный результат, используется детерминированный модуль _regex_extract. Он оценивает признаки организма, TMT-мультиплекса, типа биоматериала и уровня протеомного анализа. После успешного LLM-разбора дополнительно применяется rule-based post-processing (apply_literature_exclusions). Этот этап независимо от семантической оценки модели исключает явно non-human/xenograft-only публикации, обзоры, методические и программные работы без клинической когорты, а также phosphoproteomics-only исследования. Таким образом, генеративная модель используется как семантический фильтр, тогда как критические критерии исключения дополнительно контролируются детерминированным кодом.",
    "",
    "Идентификаторы репозиториев не принимаются из ответа LLM: поля accessions в результате семантического анализа принудительно остаются пустыми. Отдельный модуль Discovery настроен на разрешение repository accession из Data Availability (abstract_resolve_accessions = true), после чего найденные идентификаторы могут быть сопоставлены с существующим каталогом. Публикации с потенциальным соответствием атласу, для которых подходящий repository accession не подтверждён, сохраняются как записи для экспертной проверки, а не как автоматически включённые проекты.",
    "",
    "Языковая модель не используется для присвоения confidence tiers A–D репозиторным проектам. Эти категории формируются rule-based компонентами на основании доступности количественных protein-level таблиц, типа molecular layer, экспериментального дизайна и других формализованных признаков. Окончательное включение нового проекта в каталог требует ручной проверки или явной операции run_revisor.py add --apply; автоматическое изменение мастер-каталога в Discovery запрещено.",
    "",
    "2.8.4. Классификация исходов и отчётность",
    "",
    "Итоговые корзины: candidates (новые tier A/B); manual_check (литература); repository_manual (неясный sample design); rejected_material; filtered_out; already_in_catalog. Формировались QC-отчёт и веб-сводка (GitHub Pages: arinaatom-cyber.github.io/TMT/discovery/; Streamlit: human-cancser-tmt-proteome-atlas.streamlit.app). Запуск — еженедельно (run_discovery.py scan).",
]

SECTION_39 = [
    "3.9. Пилотный прогон семантического литературного скрининга",
    "",
    "При пилотном запуске Discovery 10 августа 2026 года исходный каталог содержал 123 уникальных accession. После предварительного этапа отбора в литературный слой поступили восемь публикаций Europe PMC; все восемь абстрактов были обработаны языковой моделью Qwen2.5-3B через локальный Ollama backend. Четыре публикации получили итоговую метку atlas_fit = maybe, тогда как записей с atlas_fit = yes выявлено не было. Для четырёх потенциально релевантных публикаций была назначена ручная проверка. Автоматического добавления литературных находок в основной каталог не выполнялось. В данном запуске модуль разрешения accession из литературных записей не установил ни одного нового repository identifier (literature_resolved = 0).",
    "",
    "Встроенный контрольный набор использовался только как программная проверка корректности детерминированных правил Discovery и не рассматривался как независимая валидация языковой модели. Для четырёх тестовых литературных случаев rule-based screening правильно классифицировал три случая (3/4; 75%), тогда как для трёх тестовых репозиторных записей rule-based tier classification совпала с заранее заданными категориями во всех трёх случаях (3/3). Из-за малого размера контрольного набора эти показатели не интерпретировались как оценки чувствительности, специфичности или обобщающей способности LLM.",
]


def insert_before(anchor: Paragraph, text: str) -> Paragraph:
    new_p = OxmlElement("w:p")
    anchor._element.addprevious(new_p)
    new_para = Paragraph(new_p, anchor._parent)
    if text:
        new_para.add_run(text)
    return new_para


def insert_after(anchor: Paragraph, text: str) -> Paragraph:
    new_p = OxmlElement("w:p")
    anchor._element.addnext(new_p)
    new_para = Paragraph(new_p, anchor._parent)
    if text:
        new_para.add_run(text)
    return new_para


def insert_block_before(anchor: Paragraph, lines: list[str]) -> None:
    for line in lines:
        insert_before(anchor, line)


def remove_paragraph(p: Paragraph) -> None:
    p._element.getparent().remove(p._element)


def find_para(doc: Document, substring: str, start: int = 0) -> Paragraph | None:
    for i, p in enumerate(doc.paragraphs):
        if i >= start and substring in p.text:
            return p
    return None


SECTION_28_MARKERS = (
    "2.8. Автоматизированный мониторинг",
    "2.8.1. Архитектура и источники",
    "2.8.2. Критерии отбора",
    "2.8.3. Семантический анализ публикаций",
    "2.8.4. Классификация исходов",
    "Итоговые корзины: candidates",
    "discovery pipeline) в режиме read-only",
)


def _section_28_start(text: str) -> bool:
    t = text.strip()
    return t.startswith("2.8.") or t.startswith("2.8 ")


def _section_28_marker(text: str) -> bool:
    return _section_28_start(text) or any(m in text for m in SECTION_28_MARKERS)


def _section_39_marker(text: str) -> bool:
    t = text.strip()
    return (
        t.startswith("3.9.")
        or "При пилотном запуске Discovery 10 августа 2026" in t
        or "Полный прогон выполнен 10 августа 2026" in t
        or t.startswith("Репозиторный слой. PRIDE")
        or t.startswith("Литературный слой. Europe PMC")
        or t.startswith("Benchmark exclusion")
        or t.startswith("Встроенный контрольный набор")
    )


def remove_section_27(doc: Document) -> None:
    start = end = None
    for i, p in enumerate(doc.paragraphs):
        if p.text.strip().startswith("2.7. Трёхуровневая архитектура"):
            start = i
        if start is not None and i > start:
            t = p.text.strip()
            if (
                t.startswith("2.8.")
                or t.startswith("Стандартизация метаданных")
                or t.startswith("2.6. Стандартизация")
            ):
                end = i
                break
    if start is not None and end is not None and start < end:
        for p in list(doc.paragraphs[start:end]):
            remove_paragraph(p)


def replace_section_27(doc: Document) -> None:
    remove_section_27(doc)
    anchor = find_para(doc, "2.8. Автоматизированный мониторинг")
    if anchor is None:
        anchor = find_para(doc, "2.8. Автоматизированный")
    if anchor is None:
        raise SystemExit("Не найден якорь для §2.7")
    insert_block_before(anchor, SECTION_27)


def renumber_methods_headings(doc: Document) -> None:
    for p in doc.paragraphs:
        t = p.text.strip()
        for old, new in METHODS_HEADINGS:
            if t == old or t == new:
                p.text = new
                break


def apply_text_fixes(doc: Document) -> None:
    for p in doc.paragraphs:
        text = p.text
        new = text
        for old, repl in TEXT_FIXES:
            new = new.replace(old, repl)
        if new != text:
            p.text = new


def remove_section_28(doc: Document) -> None:
    start = end = None
    for i, p in enumerate(doc.paragraphs):
        if start is None and _section_28_marker(p.text):
            start = i
        if start is not None and (
            "Программное обеспечение и статистическая" in p.text
            or p.text.strip().startswith("2.9.")
        ):
            end = i
            break
    if start is not None and end is not None and start < end:
        for p in list(doc.paragraphs[start:end]):
            remove_paragraph(p)


def remove_section_39(doc: Document) -> None:
    start = end = None
    for i, p in enumerate(doc.paragraphs):
        if _section_39_marker(p.text):
            start = i if start is None else min(start, i)
        if start is not None and p.text.strip() == "DISCUSSION":
            end = i
            break
    if start is not None and end is not None and start < end:
        for p in list(doc.paragraphs[start:end]):
            remove_paragraph(p)


def replace_section_28(doc: Document) -> None:
    remove_section_28(doc)
    anchor = find_para(doc, "Программное обеспечение и статистическая обработка")
    if anchor is None:
        anchor = find_para(doc, "2.9. Доступность данных")
    if anchor is None:
        raise SystemExit("Не найден якорь для §2.8")
    insert_block_before(anchor, SECTION_28)


def replace_section_39(doc: Document, section_39: list[str]) -> None:
    remove_section_39(doc)
    anchor = find_para(doc, "DISCUSSION")
    if anchor is None:
        raise SystemExit("Не найден якорь DISCUSSION для §3.9")
    insert_block_before(anchor, section_39)


def _is_junk_multiomics(text: str) -> bool:
    t = text.strip()
    if not t:
        return False
    markers = (
        "pip install git+https://github.com/arinaatom-cyber/multiomics-platform",
        "from proteomics_explorer import ProteomicsExplorer",
        "2.8.9.3",
        "explorer = ProteomicsExplorer",
        "explorer.df.to_csv",
        "explorer.df.to_excel",
        "print(projects)",
        "projects = explorer.list_projects",
        "print(result)",
        "result = explorer.search",
        "print(\"Установка успешна!\")",
        "Установка из репозитория:",
        "Проверка установки:",
        "Инициализация и просмотр проектов:",
        "Поиск объектов:",
        "Сохранение результатов:",
    )
    return any(m in t for m in markers)


def patch_docx(path: Path) -> None:
    doc = Document(str(path))

    for p in list(doc.paragraphs):
        if _is_junk_multiomics(p.text):
            remove_paragraph(p)

    renumber_methods_headings(doc)
    apply_text_fixes(doc)

    replace_section_27(doc)

    disc_idx = next(
        (i for i, p in enumerate(doc.paragraphs) if "Конвейер мониторинга новых депонирований" in p.text),
        None,
    )
    if disc_idx is not None:
        remove_paragraph(doc.paragraphs[disc_idx])
        if disc_idx < len(doc.paragraphs) and "read-only конвейер мониторинга" in doc.paragraphs[disc_idx].text:
            remove_paragraph(doc.paragraphs[disc_idx])
    replace_section_28(doc)

    for p in doc.paragraphs:
        if p.text.strip() in (
            "Доступность данных, кода и веб-интерфейса",
            "2.9. Доступность данных, кода и веб-интерфейса",
        ):
            p.text = "2.9. Доступность данных, кода и веб-интерфейса"
            break

    replace_section_39(doc, SECTION_39)

    for p in doc.paragraphs:
        if "tmt-projects-j6vqdccqua9qym6apskrkw.streamlit.app" in p.text:
            p.text = p.text.replace(
                "https://tmt-projects-j6vqdccqua9qym6apskrkw.streamlit.app/",
                "https://human-cancser-tmt-proteome-atlas.streamlit.app/",
            )

    doc.save(str(path))
    print(f"Patched: {path}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Patch manuscript docx with Discovery sections")
    parser.add_argument("--docx", type=Path, default=DEFAULT_DOCX, help="Path to .docx")
    args = parser.parse_args()
    if not args.docx.is_file():
        print(f"File not found: {args.docx}", file=sys.stderr)
        return 1
    patch_docx(args.docx)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
