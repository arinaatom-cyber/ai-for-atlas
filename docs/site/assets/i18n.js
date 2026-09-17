/** Bilingual UI — единые подписи на всех страницах Discovery */
(function () {
  const STORAGE_KEY = "atlas_site_lang";

  const SHARED = {
    brand_title: "Human Cancer-Associated TMT Proteome Atlas",
    nav_home: { ru: "Главная", en: "Home" },
    nav_ai: { ru: "ИИ поиск", en: "AI search" },
    nav_map: { ru: "Карта органов", en: "Organ map" },
    nav_atlas: { ru: "Атлас", en: "Atlas" },
    nav_discovery: { ru: "Discovery", en: "Discovery" },
    nav_cohorts: { ru: "Когорты", en: "Cohorts" },
    nav_qc: { ru: "QC", en: "QC" },
    meta_updated: { ru: "Обновлено", en: "Updated" },
    badge_readonly: { ru: "только чтение", en: "read-only" },
    meta_candidates: { ru: "кандидатов", en: "candidates" },
    meta_atlas_ids: { ru: "ID в атласе", en: "atlas IDs" },
    footer_github: { ru: "GitHub TMT", en: "GitHub TMT" },
    footer_code: { ru: "Код Discovery", en: "Discovery code" },
    footer_opensource: { ru: "Открытый код на GitHub", en: "Open source on GitHub" },
    footer_projects: { ru: "tmt-projects", en: "tmt-projects" },
    footer_live: { ru: "Live (GitHub Pages)", en: "Live (GitHub Pages)" },
    th_num: { ru: "№", en: "#" },
    th_disease: { ru: "Болезнь", en: "Disease" },
    th_organ: { ru: "Орган / ткань", en: "Organ / tissue" },
    th_abstract: { ru: "Абстракт", en: "Abstract" },
    filter_all: { ru: "Все", en: "All" },
    filter_yes: { ru: "да", en: "yes" },
    filter_maybe: { ru: "возможно", en: "maybe" },
    filter_no: { ru: "нет", en: "no" },
    filter_pride: { ru: "PRIDE", en: "PRIDE" },
      filter_pdc: { ru: "PDC", en: "PDC" },
      filter_massive: { ru: "MassIVE", en: "MassIVE" },
      filter_iprox: { ru: "iProX", en: "iProX" },
      filter_epmc: { ru: "Europe PMC", en: "Europe PMC" },
      filter_projects: { ru: "Проекты", en: "Projects" },
      filter_papers: { ru: "Статьи", en: "Papers" },
      filter_cohorts: { ru: "Когорты", en: "Cohorts" },
      filter_all_src: { ru: "Все источники", en: "All sources" },
    filter_patients_yes: { ru: "пациенты: да", en: "patients: yes" },
    filter_patients_maybe: { ru: "пациенты: возможно", en: "patients: maybe" },
    th_id: { ru: "ID", en: "ID" },
    th_project_id: { ru: "ID проекта", en: "Project ID" },
    th_project_id_hint: {
      ru: "PRIDE/PDC/MSV/IPX или Europe PMC",
      en: "PRIDE/PDC/MSV/IPX or Europe PMC",
    },
    th_type: { ru: "Тип", en: "Type" },
    th_confidence: { ru: "Уверенность", en: "Confidence" },
    th_confidence_hint: { ru: "A–D", en: "A–D" },
    th_title: { ru: "Название", en: "Title" },
    th_source: { ru: "Источник", en: "Source" },
    th_plex: { ru: "Plex", en: "Plex" },
    th_design: { ru: "Дизайн / TMT", en: "Design / TMT" },
    tmt_plex_unspecified: {
      ru: "TMT plex не прописан — нужна проверка",
      en: "TMT plex not specified — needs review",
    },
    tmt_plex_unspecified_hint: {
      ru: "PRIDE не указал число каналов TMT в метаданных; подтвердите >6-plex вручную",
      en: "PRIDE metadata lacks TMT channel count; confirm >6-plex manually",
    },
    th_similar: { ru: "Похож на", en: "Similar to" },
    th_ai: { ru: "ИИ-анализ", en: "AI analysis" },
    th_finding: { ru: "Что найдено", en: "Finding" },
    th_data: { ru: "Данные / файлы", en: "Data / files" },
    th_supplementary: { ru: "Supplementary", en: "Supplementary" },
    th_weight: { ru: "Вес", en: "Weight" },
    th_group_record: { ru: "Запись", en: "Record" },
    th_group_context: { ru: "Контекст", en: "Context" },
    th_group_details: { ru: "Детали", en: "Details" },
    th_fit: { ru: "Соответствие", en: "Fit" },
    th_material: { ru: "Материал", en: "Material" },
    th_theme: { ru: "Тема атласа", en: "Atlas theme" },
    th_analysis: { ru: "Анализ", en: "Analysis" },
    th_reason: { ru: "Причина", en: "Reason" },
    th_included: { ru: "Включено", en: "Included" },
    th_excluded: { ru: "Исключено", en: "Excluded" },
    th_pmid: { ru: "PMID", en: "PMID" },
    th_organism: { ru: "Организм", en: "Organism" },
    th_tmt: { ru: "TMT", en: "TMT" },
    th_ids: { ru: "ID репозитория", en: "Repository IDs" },
    th_pride: { ru: "PRIDE", en: "PRIDE" },
    th_reader: { ru: "Движок", en: "Reader" },
    th_link: { ru: "Ссылка", en: "Link" },
    th_links: { ru: "Ссылки", en: "Links" },
    th_link_open: { ru: "Открыть", en: "Open" },
    th_notes: { ru: "Примечания", en: "Notes" },
    th_description: { ru: "Описание", en: "Description" },
    th_patients: { ru: "Пациенты", en: "Patients" },
    th_n: { ru: "N", en: "N" },
    th_omics: { ru: "Омики", en: "Omics" },
    th_multi: { ru: "Мульти-омика", en: "Multi-omics" },
    th_year: { ru: "Год", en: "Year" },
    th_journal: { ru: "Журнал", en: "Journal" },
    th_score: { ru: "Оценка", en: "Score" },
    th_verdict: { ru: "Вердикт", en: "Verdict" },
    tab_projects: { ru: "Проекты", en: "Projects" },
    tab_guide: { ru: "Справка", en: "Guide" },
    tab_technical: { ru: "Методы", en: "Methods" },
    cell_empty: { ru: "—", en: "—" },
    pat_yes: { ru: "да", en: "yes" },
    pat_maybe: { ru: "возможно", en: "maybe" },
    pat_no: { ru: "нет", en: "no" },
    badge_project: { ru: "Проект", en: "Project" },
    badge_paper: { ru: "Статья", en: "Paper" },
    badge_cohort: { ru: "Когорта", en: "Cohort" },
    verdict_candidate: { ru: "Кандидат", en: "Candidate" },
    verdict_watch: { ru: "Наблюдение", en: "Watch" },
    verdict_exclude: { ru: "Исключить", en: "Exclude" },
    verdict_review: { ru: "Проверка", en: "Review" },
    no_accession: { ru: "Нет PXD/PDC/MSV/IPX", en: "No PXD/PDC/MSV/IPX" },
    link_epmc: { ru: "Europe PMC", en: "Europe PMC" },
    fit_llm_yes: { ru: "ИИ: да", en: "LLM yes" },
    fit_llm_maybe: { ru: "ИИ: возможно", en: "LLM maybe" },
    fit_llm_no: { ru: "ИИ: нет", en: "LLM no" },
    fit_llm_hint: {
      ru: "LLM-скрининг абстракта (обучен на исключениях каталога)",
      en: "LLM abstract screening (trained on catalog exclusions)",
    },
    badge_cohort_score: { ru: "когорта {n}", en: "cohort {n}" },
    badge_cohort_hint: { ru: "Релевантность когорты 0–100", en: "Cohort relevance 0–100" },
    data_quant_table: { ru: "Таблица белков", en: "Protein table" },
    data_local_mirror: { ru: "Локальное зеркало", en: "Local mirror" },
    data_maybe_table: { ru: "Возможная таблица", en: "Possible table" },
    data_psm_only: { ru: "Только PSM", en: "PSM only" },
    data_phospho_only: { ru: "Только phospho", en: "Phospho only" },
    data_raw_only: { ru: "Только RAW", en: "RAW only" },
    data_no_files: { ru: "Нет файлов", en: "No files" },
    data_mixed_protein_phospho: { ru: "protein+phospho", en: "mixed protein+phospho" },
    omics_proteomics: { ru: "протеомика", en: "proteomics" },
    omics_phospho: { ru: "фосфопротеомика", en: "phosphoproteomics" },
    omics_transcriptomics: { ru: "транскриптомика", en: "transcriptomics" },
    omics_genomics: { ru: "геномика", en: "genomics" },
    omics_metabolomics: { ru: "метаболомика", en: "metabolomics" },
    omics_lipidomics: { ru: "липидомика", en: "lipidomics" },
    omics_glycoproteomics: { ru: "гликопротеомика", en: "glycoproteomics" },
    omics_multi: { ru: "мульти-омика", en: "multi-omics" },
    data_mixed_hint: {
      ru: "Protein и phospho — ручная проверка",
      en: "Protein and phospho files — manual check",
    },
    count_rows: { ru: "{n} / {total} строк", en: "{n} / {total} rows" },
    toolbar_type: { ru: "Тип", en: "Type" },
    toolbar_view: { ru: "Просмотр", en: "View" },
    filter_view_simple: { ru: "Подошло", en: "Passed" },
    filter_view_all: { ru: "Весь поиск", en: "All search" },
    toolbar_source: { ru: "Источник", en: "Source" },
    toolbar_disease: { ru: "Болезнь", en: "Disease" },
    filter_all_disease: { ru: "Все болезни", en: "All diseases" },
    legacy_rescan: { ru: "Устаревший формат — перезапустите scan", en: "Legacy format — re-scan required" },
    link_open_repo: { ru: "Репозиторий", en: "Repository" },
    card_open: { ru: "Открыть", en: "Open" },
    card_json: { ru: "latest.json (API)", en: "latest.json (API)" },
    kpi_abstracts_ai: { ru: "абстрактов ИИ", en: "LLM abstracts" },
    no_rows: { ru: "Нет записей", en: "No records" },
  };

  const PAGE = {
    ru: {
      brand_sub: "Новые TMT проекты · похожесть на атлас",
      brand_link_ai: "Atlas AI",
      brand_link_technical: "Методы · версии скриптов",
      footer_policy:
        "Каталог Excel не публикуется. На сайте — только новые кандидаты, литература и анализ.",
      disc_title: "Discovery — новые TMT-проекты",
      disc_lead:
        "Еженедельный ИИ-скрининг PRIDE, PDC и Europe PMC. В таблице — только находки вне каталога атласа.",
      disc_catalog_hidden: "каталог скрыт",
      disc_catalog_n: "проектов в атласе",
      kpi_new: "Подошло (Candidate)",
      kpi_pride_manual: "PRIDE на проверке",
      kpi_pride: "PRIDE",
      kpi_pdc: "PDC",
      kpi_manual: "Ручная проверка",
      kpi_rejected: "Отклонено",
      kpi_yes_maybe: "да / возможно",
      sec_projects: "Новые проекты",
      sec_projects_desc: "Только PXD / PDC / MSV / IPX, которых нет в TMT ATLAS",
      sec_abstracts: "ИИ-анализ абстрактов",
      sec_literature: "Статьи без accession",
      sec_literature_desc: "По смыслу похоже на атлас; номер проекта не найден",
      sec_qc: "QC — manual / rejected",
      search_projects: "Поиск по ID, названию…",
      search_abstracts: "Поиск по названию, анализу…",
      kpi_papers_no_id: "Статей без ID",
      kpi_with_table: "с protein table",
      note_projects_unified:
        "ID → репозиторий (синяя ссылка). Название → клик на PRIDE/PDC или PubMed; под описанием — PMID и Europe PMC. PRIDE на ручной проверке — в таблице, но не в KPI.",
      sec_unified_discovery: "Реестр находок Discovery",
      sec_unified_discovery_desc:
        "Единая таблица последнего скана: новые PXD/PDC/MSV/IPX, статьи без repository accession и онкологические когорты из литературы.",
      sec_unified_count_hint: "Число всех строк таблицы (проекты + статьи + когорты)",
      note_scope_lead:
        "По умолчанию «Подошло»: только проекты с вердиктом Candidate. «Весь поиск» — полный список (ручная проверка, исключённые, статьи).",
      note_scope_row_types:
        "Типы строк: Project — PXD/PDC/MSV/IPX; Paper — PMID без accession; Cohort — крупная когорта из литературы.",
      note_scope_kpi:
        "KPI: сколько проектов прошло фильтры (Candidate). «PRIDE на проверке» — plex/дизайн неясны. «Отклонено» в KPI, не в главном списке.",
      note_scope_filter:
        "Фильтр «проекты» оставляет только репозиторные ID; «статьи» и «когорты» — Europe PMC без PXD/PDC.",
      note_scope_stat_new: "новых проектов (KPI)",
      note_scope_stat_total: "записей в таблице",
      note_kpi_new_projects:
        "KPI и вкладка «Подошло» — только Candidate. Исключённые и ручная проверка — во «Весь поиск».",
      sec_methods: "Методы и воронка",
      sec_methods_desc:
        "Пайплайн для Materials & Methods: агенты, скрипты, критерии включения. Цифры воронки — снимок последнего скана (см. дату выше).",
      funnel_viz_lead:
        "Воронка скрининга: слева — сжатие от API-хитов до кандидатов; справа — детализация по репозиториям, литературе и data gate.",
      funnel_svg_in: "API PRIDE + PDC",
      funnel_svg_out: "Кандидаты в таблице",
      methods_raw_stats: "Таблица чисел для supplementary (развернуть)",
      methods_funnel: "Воронка репозиториев",
      methods_literature: "Литература (Europe PMC)",
      methods_data_gate: "Data availability gate",
      methods_search_cfg: "Параметры поиска",
      methods_confidence: "Калибровка (benchmark)",
      methods_tier_legend: "A = protein table + design OK · B = quant files · C = watch · D = exclude",
      methods_confidence_note:
        "Tier A–D — rule-based, не калиброванная вероятность LLM. Benchmark — ручная разметка на hold-out.",
      methods_inclusion: "Критерии включения",
      methods_exclusion: "Критерии исключения",
      meta_pipeline: "Пайплайн",
      agents_lead: "Discovery использует несколько агентов: скан репозиториев, ИИ-чтение абстрактов, rule-based QC и оценку строк.",
      agents_active: "Активный LLM для абстрактов",
      agents_available: "Доступные провайдеры",
      agents_pipeline: "Компоненты пайплайна",
      agents_llm: "Поддерживаемые LLM",
      pipeline_lead: "Пошаговый пайплайн: язык, скрипт, агент и назначение каждого этапа.",
      pipeline_similarity: "Коэффициент схожести",
      pipeline_example_file: "Пример файла данных",
      pipeline_r_plans: "R-планов в каталоге",
      pipeline_github: "github.com/arinaatom-cyber/ai-for-atlas",
      pipe_th_step: "Шаг",
      pipe_th_stage: "Этап",
      pipe_th_lang: "Язык",
      pipe_th_script: "Скрипт / файл",
      pipe_th_agent: "Агент",
      pipe_th_purpose: "Назначение",
      meta_scan_date: "Дата скана",
      funnel_raw_repos: "Новые записи PRIDE+PDC",
      funnel_in_catalog: "Уже в каталоге",
      funnel_filtered: "Отфильтровано (техн.)",
      funnel_candidates: "Кандидаты",
      funnel_manual: "Ручная проверка",
      funnel_rejected: "Отклонено (материал)",
      lit_scanned: "Статей просмотрено",
      lit_llm_read: "Абстрактов прочитано LLM",
      lit_regex_only: "Только regex",
      lit_fit_yes: "Atlas fit: да",
      lit_fit_maybe: "Atlas fit: возможно",
      lit_resolved: "ID из Data availability",
      gate_quant_table: "Protein table",
      gate_omics_protein: "Global proteome",
      gate_raw_only: "Только RAW",
      gate_no_files: "Нет файлов в API",
      gate_unknown: "Omics unknown",
      cfg_years: "Годы",
      cfg_repo_search: "Репозитории (PRIDE, PDC, MassIVE, iProX)",
      cfg_unlimited: "без лимита",
      cfg_pride_max: "Лимит PRIDE",
      cfg_massive_max: "Лимит MassIVE",
      cfg_iprox_max: "Лимит iProX",
      cfg_pubs_max: "Лимит публикаций",
      cfg_llm: "LLM abstract read",
      cfg_llm_on: "вкл",
      cfg_llm_off: "выкл",
      cfg_mode: "Режим поиска",
      cfg_tmt_plex: "TMT plex",
      cfg_databases: "Базы",
      bench_literature: "Benchmark литература",
      bench_projects: "Benchmark проекты",
      inc_organism: "Homo sapiens (отклонять mouse/rat/chicken и mixed)",
      inc_quant: "TMT/isobaric >6-plex (TMT6 и ≤6-plex — нет; TMT18 — да)",
      inc_omics: "Global protein-level proteome (не phospho-only, не peptide-only)",
      inc_material: "Ткань (tumor/adjacent/normal) или линии рака; не plasma/serum/urine-only",
      inc_literature: "Europe PMC + ID только из Data availability",
      exc_1: "Non-human, mixed, xenograft-only",
      exc_2: "TMT6 или ≤6-plex",
      exc_3: "Plasma / serum / urine / blood-only",
      exc_4: "Phosphoproteomics-only",
      exc_5: "Peptide-level quantification only",
      exc_6: "Review / methods / software без когорты",
      exc_7: "Phospho-only или RAW-only в репозитории",
      note_unified_table:
        "ИИ-поиск на профиле TMT ATLAS + жёсткие исключения. Confidence A–D — rule-based. Verdict: Candidate / Watch / Exclude.",
      search_unified: "Поиск по ID, названию, анализу…",
      filter_projects: "Проекты",
      filter_papers: "Статьи",
      filter_cohorts: "Когорты",
      filter_all_src: "Все источники",
      filter_epmc: "Europe PMC",
      sec_cohorts_on_discovery: "Крупные когорты (протеомика и мульти-омика)",
      sec_cohorts_on_discovery_desc: "Europe PMC — пациенты, N, омики, TMT, журнал, score",
      no_projects: "Нет новых проектов",
      no_pubs: "Нет проанализированных статей",
      no_literature: "Нет статей для ручной проверки",
      qc_title: "QC отчёт Discovery",
      qc_lead: "Первый список — только то, что прошло QC (Candidate). Дальше: ручная проверка, Exclude, материал, техфильтр.",
      qc_rules_title: "Правила материала",
      qc_rules:
        "Homo sapiens. Ткань (tumor / adjacent / human tissue) или раковая клеточная линия должна быть прописана в метаданных или статье — иначе reject. Не берём plasma/serum/urine-only, organoids-only, PDX-only, животные. Смешанное tissue+organoid → ручная проверка.",
      qc_candidate: "Подошло (QC)",
      qc_candidate_desc: "Вердикт Candidate — материал и фильтры пройдены. Это же главный список на Discovery.",
      qc_manual: "Ручная проверка",
      qc_manual_desc: "PRIDE без plex/неясный дизайн + статьи без PXD. Не входят в «Подошло».",
      qc_exclude: "Исключено (вердикт)",
      qc_exclude_desc: "Дошли до кандидатов, но QC/данные дали Exclude — не в главном списке.",
      qc_rejected: "Отклонено (материал)",
      qc_filtered: "Отфильтровано (техн.)",
      qc_pubs: "статей проанализировано",
      atlas_title: "Профиль атласа",
      atlas_lead: "Сводка Human Cancer-Associated TMT Proteome Atlas — только метаданные, без выгрузки каталога",
      atlas_datasets: "датасетов",
      atlas_publications: "уникальных ID",
      atlas_repos: "Репозитории",
      atlas_organs: "Топ органов / тканей",
      atlas_diseases: "Топ нозологий",
      atlas_tmt: "TMT-плексы",
      atlas_keywords: "Ключевые слова поиска",
      atlas_link: "Реестр на GitHub",
      atlas_discovery: "Анализ новых наборов",
      portal_title: "Human Cancer-Associated TMT Proteome Atlas",
      portal_lead:
        "Мониторинг human TMT в PRIDE, PDC, MassIVE, iProX · ИИ-разбор абстрактов · крупные когорты в литературе",
      card_discovery_title: "Полный анализ Discovery",
      card_discovery_desc: "Единая таблица: PXD/PDC · статьи · когорты · QC · файлы",
      card_qc_title: "QC отчёт",
      card_qc_desc: "Подошло / ручная проверка / Exclude / rejected — те же правила, что в Discovery",
      card_atlas_title: "Профиль атласа",
      card_atlas_desc: "Статистика каталога: репозитории, органы, нозологии, TMT-плексы",
      card_cohorts_title: "Крупные когорты",
      card_cohorts_desc: "Протеомика и мульти-омика: большие patient cohorts, text mining абстрактов",
      card_map_title: "Интерактивная карта",
      card_map_desc: "TMT-проекты по органам · диплинки ?organ= · каталог read-only",
      card_ai_title: "ИИ поиск по ключевым словам",
      card_ai_desc: "PRIDE, PDC, Europe PMC по профилю атласа · LLM-скрининг абстрактов",
      ai_title: "ИИ поиск",
      ai_lead: "Поиск по репозиториям и литературе с LLM-оценкой — тот же движок, что в Discovery-портале",
      ai_how_title: "Как пользоваться",
      ai_step1: "Откройте live-приложение — вкладка «ИИ поиск» открыта по умолчанию",
      ai_step2: "Отредактируйте ключевые слова или оставьте профиль атласа (органы, нозологии, TMT)",
      ai_step3: "Нажмите Run search — шаги 1–4: репозитории → Europe PMC → фильтры → LLM",
      ai_step4: "Проверьте ID и публикации; в CSV только через run_revisor.py add --apply",
      ai_launch_title: "Запустить интерактивный поиск",
      ai_launch_desc: "Полный поиск в Streamlit (API + локальный LLM). projects.csv не меняется автоматически.",
      ai_launch_btn: "Открыть ИИ поиск",
      ai_view_discovery: "Последний Discovery scan",
      ai_keywords_title: "Ключевые слова атласа",
      ai_keywords_desc: "Из профиля каталога — вставьте в приложение или отредактируйте перед поиском",
      ai_iframe_fallback: "Если встроенный фрейм пустой — используйте кнопку выше (Streamlit может блокировать iframe).",
      ai_badge_live: "Live app",
      map_title: "Карта органов человека",
      map_lead: "Интерактивный TMT-каталог по органам — клик по регионам, фильтр проектов, ссылки PRIDE/PDC",
      map_how_title: "Как пользоваться",
      map_step1: "Кликните орган на силуэте или выберите быструю ссылку ниже",
      map_step2: "Просмотрите проекты ткани — откройте репозиторий или PubMed в боковой панели",
      map_step3: "Диплинки: добавьте ?organ=gastric (или другой ключ) к URL карты",
      map_open_full: "Открыть карту на весь экран",
      map_embed_hint: "Встроено с GitHub Pages TMT — прокручивайте внутри фрейма",
      map_organs_title: "Быстрые ссылки на органы",
      card_update_title: "Обновление данных",
      card_update_desc: "Локально: python run_discovery.py scan · publish · export для GitHub Pages",
      portal_deploy_note:
        "Карта органов: TMT/index.html (?organ=). Discovery-портал — в docs/ и docs/site/.",
      cohorts_title: "Крупные когорты — протеомика и мульти-омика",
      cohorts_lead: "Europe PMC + text mining: пациенты, N, омики, TMT",
      cohorts_method: "text mining · Europe PMC",
      cohorts_note:
        "Отбор: human proteomics/phosphoproteomics, крупные когорты (N≥50 из абстракта или large-scale/multi-omics). PMID из атласа исключены. N извлекается автоматически — проверяйте вручную.",
      kpi_cohorts: "статей в списке",
      kpi_with_n: "с числом N",
      kpi_multi_omics: "мульти-омика",
      kpi_scanned: "просмотрено EPMC",
      search_cohorts: "Поиск по названию, описанию…",
      sec_cohorts_table: "Список статей",
      no_cohorts: "Когортные статьи не найдены — запустите scan",
      guide_title: "Как читать таблицу",
      guide_lead:
        "Один экран — новые TMT-проекты вне каталога. По умолчанию показаны только строки типа «Project» (PXD/PDC/MSV/IPX).",
      guide_columns_title: "Колонки",
      table_scroll_hint: "Таблица широкая — прокрутите вправо, чтобы увидеть все колонки. Вкладка «Проекты» — данные; «Справка» — расшифровка колонок.",
      col_help_type: "Project — репозиторий с accession; Paper — статья без ID; Cohort — крупная когорта из литературы.",
      col_help_id:
        "Репозиторий: accession + синяя ссылка PRIDE/PDC/MassIVE/iProX. Статья: Europe PMC или PXD, если найден по PMID. PMID/PXD — также в «Название».",
      col_help_disease:
        "Нозология из метаданных или из названия/описания. Фильтр «Болезнь» над таблицей.",
      col_help_year: "Год публикации или submission из PRIDE/PDC или PubMed.",
      col_help_title: "Заголовок (клик → PRIDE/PDC или PubMed), описание и строка PMID / Europe PMC.",
      col_help_design: "Дизайн и TMT plex. Если PRIDE не указал plex — жёлтый бейдж «TMT plex не прописан — нужна проверка».",
      col_help_omics: "Тип омики: proteomics, phospho, multi-omics (для когорт).",
      col_help_patients: "Есть ли пациенты в тексте: да / возможно / нет.",
      col_help_n: "Число пациентов/образцов из абстракта (авто, проверяйте вручную).",
      col_help_verdict: "Candidate — в атлас; Watch — наблюдение; Exclude — не подходит.",
      col_help_confidence: "Уверенность A–D: A = protein table + дизайн OK; B = файлы есть; C = watch; D = exclude.",
      col_help_similar:
        "Схожесть с каталогом (Jaccard). Строка сворачивается — клик разворачивает все совпадения PXD/PDC · %.",
      col_help_fit: "LLM-оценка atlas fit (да/возможно/нет) или cohort score 0–100 для литературы.",
      col_help_analysis: "ИИ-резюме абстракта + цепочка evidence (фильтры, LLM, similarity).",
      col_help_data: "Наличие protein-level таблицы в репозитории или локальном mirror.",
      col_help_links: "Устарело — ссылки перенесены в колонку «Название».",
      guide_filters_title: "Фильтры над таблицей",
      guide_filters_type: "Тип строки: все / проекты / статьи / когорты.",
      guide_filters_source: "Источник: PRIDE, PDC, MassIVE, iProX, Europe PMC.",
      guide_filters_search: "Поиск по ID, названию, PMID, описанию и тексту анализа.",
      guide_similarity_title: "Похожесть на атлас",
      guide_similarity_desc:
        "Для каждого кандидата считается similarity score к проектам из projects.csv (title, tissue, disease, TMT). 80%+ — очень близко; 40–60% — та же тема; <30% — новая ниша. Клик по PXD в колонке Similar — карточка в PRIDE.",
      tech_title: "Пайплайн Discovery Agent",
      tech_lead: "Пошаговое описание последнего скана — готово для Methods / Supplementary.",
      tech_step1: "1. PRIDE Archive API v3 + PDC UI — keyword TMT, Homo sapiens, годы из config.yaml.",
      tech_step2: "2. MassIVE и iProX — те же ключевые слова профиля TMT ATLAS.",
      tech_step3: "3. Hard filters: organism, TMT >6 plex, tissue/cell line, reject plasma-only.",
      tech_step4: "4. Material QC + data availability gate (protein-level table в репозитории).",
      tech_step5: "5. Europe PMC — cohort literature; LLM abstract read (Ollama/API, если включено).",
      tech_step6: "6. Similarity vs projects.csv; confidence tier A–D; publish на сайт (каталог не меняется).",
      tech_llm_title: "LLM и модели",
      tech_llm_desc:
        "Abstract screening: локальный Ollama (Qwen) или облачный API (config.yaml). Verdict и tier — rule-based + LLM labels; не calibrated probability.",
      tech_manifest_title: "Полный manifest скана (JSON)",
    },
    en: {
      brand_sub: "New TMT projects · atlas similarity",
      brand_link_ai: "Atlas AI",
      brand_link_technical: "Methods · script versions",
      footer_policy:
        "Excel catalog is not published. Site shows new candidates, literature, and analysis only.",
      disc_title: "Discovery — new TMT projects",
      disc_lead:
        "Weekly AI scan of PRIDE, PDC, and Europe PMC. Table lists findings not yet in the atlas catalog.",
      disc_catalog_hidden: "catalog hidden",
      disc_catalog_n: "projects in atlas",
      kpi_new: "Passed (Candidate)",
      kpi_pride_manual: "PRIDE manual review",
      kpi_pride: "PRIDE",
      kpi_pdc: "PDC",
      kpi_manual: "manual review",
      kpi_rejected: "rejected",
      kpi_yes_maybe: "yes / maybe",
      sec_projects: "New projects",
      sec_projects_desc: "PXD / PDC / MSV / IPX not yet in TMT ATLAS",
      sec_abstracts: "LLM abstract analysis",
      sec_literature: "Papers without accession",
      sec_literature_desc: "Atlas-like by meaning; dataset ID not resolved",
      sec_qc: "QC — manual / rejected",
      search_projects: "Search ID, title…",
      search_abstracts: "Search title, analysis…",
      note_abstracts:
        "LLM reads abstracts by meaning (few-shot from TMT ATLAS). Accessions are not regex-extracted. PDC: TMT 10/11/12/16, CPTAC programs excluded.",
      kpi_papers_no_id: "papers w/o ID",
      kpi_with_table: "with protein table",
      note_projects_unified:
        "ID → repository (blue link). Title → PRIDE/PDC or PubMed; PMID and Europe PMC under the description. PRIDE manual-review rows are in the table but not in the KPI.",
      sec_unified_discovery: "Discovery findings registry",
      sec_unified_discovery_desc:
        "Unified table from the latest scan: novel PXD/PDC/MSV/IPX accessions, papers without a repository ID, and oncology cohort literature.",
      sec_unified_count_hint: "Total table rows (projects + papers + cohorts)",
      note_scope_lead:
        "Default «Passed»: Candidate projects only. «All search» is the full list (manual review, excluded, papers).",
      note_scope_row_types:
        "Row types: Project — PXD/PDC/MSV/IPX; Paper — PMID without accession; Cohort — large literature cohort.",
      note_scope_kpi:
        "KPI: how many projects passed filters (Candidate). «PRIDE manual review» = unclear plex/design. Rejected items are in the KPI, not the main list.",
      note_scope_filter:
        "Filter «projects» for repository IDs only; «papers» and «cohorts» show Europe PMC records without PXD/PDC.",
      note_scope_stat_new: "new projects (KPI)",
      note_scope_stat_total: "rows in table",
      note_kpi_new_projects:
        "KPI and «Passed» tab = Candidate only. Excluded and manual-review rows live under «All search».",
      note_unified_table:
        "AI search uses TMT ATLAS profile + hard exclusions. Confidence A–D is rule-based. Verdict: Candidate / Watch / Exclude.",
      sec_methods: "Methods & funnel",
      sec_methods_desc:
        "Pipeline for Materials & Methods: agents, scripts, inclusion criteria. Funnel counts are a snapshot of the last scan (see date above).",
      funnel_viz_lead:
        "Screening funnel: left — compression from API hits to table candidates; right — repository, literature, and data-gate breakdown.",
      funnel_svg_in: "API PRIDE + PDC",
      funnel_svg_out: "Table candidates",
      methods_raw_stats: "Numeric table for supplementary (expand)",
      methods_funnel: "Repository funnel",
      methods_literature: "Literature (Europe PMC)",
      methods_data_gate: "Data availability gate",
      methods_search_cfg: "Search parameters",
      methods_confidence: "Calibration (benchmark)",
      methods_tier_legend: "A = protein table + design OK · B = quant files · C = watch · D = exclude",
      methods_confidence_note:
        "Tiers A–D are rule-based, not calibrated LLM probability. Benchmark = manual labels on hold-out.",
      methods_inclusion: "Inclusion criteria",
      methods_exclusion: "Exclusion criteria",
      meta_pipeline: "Pipeline",
      agents_lead: "Discovery uses repository scan, abstract AI reader, rule-based QC, and row evaluation agents.",
      agents_active: "Active LLM for abstracts",
      agents_available: "Available providers",
      agents_pipeline: "Pipeline components",
      agents_llm: "Supported LLMs",
      pipeline_lead: "Step-by-step pipeline: language, script, agent, and purpose at each stage.",
      pipeline_similarity: "Similarity score",
      pipeline_example_file: "Example data file",
      pipeline_r_plans: "R stats plans in catalog",
      pipeline_github: "github.com/arinaatom-cyber/ai-for-atlas",
      pipe_th_step: "Step",
      pipe_th_stage: "Stage",
      pipe_th_lang: "Language",
      pipe_th_script: "Script / file",
      pipe_th_agent: "Agent",
      pipe_th_purpose: "Purpose",
      meta_scan_date: "Scan date",
      funnel_raw_repos: "Novel PRIDE+PDC hits",
      funnel_in_catalog: "Already in catalog",
      funnel_filtered: "Technically filtered",
      funnel_candidates: "Candidates",
      funnel_manual: "Manual check",
      funnel_rejected: "Rejected (material)",
      lit_scanned: "Publications scanned",
      lit_llm_read: "Abstracts LLM-read",
      lit_regex_only: "Regex only",
      lit_fit_yes: "Atlas fit: yes",
      lit_fit_maybe: "Atlas fit: maybe",
      lit_resolved: "IDs from data availability",
      gate_quant_table: "Protein table",
      gate_omics_protein: "Global proteome",
      gate_raw_only: "RAW only",
      gate_no_files: "No files in API",
      gate_unknown: "Omics unknown",
      cfg_years: "Years",
      cfg_repo_search: "Repositories (PRIDE, PDC, MassIVE, iProX)",
      cfg_unlimited: "no limit",
      cfg_pride_max: "PRIDE limit",
      cfg_massive_max: "MassIVE limit",
      cfg_iprox_max: "iProX limit",
      cfg_pubs_max: "Publication limit",
      cfg_llm: "LLM abstract read",
      cfg_llm_on: "on",
      cfg_llm_off: "off",
      cfg_mode: "Search mode",
      cfg_tmt_plex: "TMT plex",
      cfg_databases: "Databases",
      bench_literature: "Literature benchmark",
      bench_projects: "Project benchmark",
      inc_organism: "Homo sapiens only (reject mouse/rat/chicken and mixed)",
      inc_quant: "TMT/isobaric >6-plex (reject TMT6 / ≤6-plex; TMT18 allowed)",
      inc_omics: "Global protein-level proteome (reject phospho-only, peptide-only)",
      inc_material: "Human tissue or cancer cell lines (reject plasma/serum/urine-only)",
      inc_literature: "Europe PMC semantic screening; repo IDs from data availability only",
      exc_1: "Non-human, mixed, or xenograft-only",
      exc_2: "TMT6 or ≤6-plex",
      exc_3: "Plasma / serum / urine / blood-only (need tissue or cell line)",
      exc_4: "Phosphoproteomics-only emphasis",
      exc_5: "Peptide-level quantification only",
      exc_6: "Review / methods / software papers without cohort data",
      exc_7: "Phospho-only or RAW-only repository files",
      qc_filtered: "Filtered (technical)",
      search_unified: "Search ID, title, analysis…",
      filter_projects: "Projects",
      filter_papers: "Papers",
      filter_cohorts: "Cohorts",
      filter_all_src: "All sources",
      filter_epmc: "Europe PMC",
      sec_cohorts_on_discovery: "Large cohorts (proteomics & multi-omics)",
      sec_cohorts_on_discovery_desc: "Europe PMC text mining — patients, N, omics, TMT, journal, score",
      no_projects: "No new projects",
      no_pubs: "No analyzed publications",
      no_literature: "No papers for manual review",
      qc_title: "Discovery QC report",
      qc_lead: "First table = QC pass (Candidate). Then: manual review, Exclude, material reject, technical filter.",
      qc_rules_title: "Material rules",
      qc_rules:
        "Homo sapiens. Tissue (tumor / adjacent / human tissue) or a cancer cell line must be stated in metadata or the paper — otherwise reject. No plasma/serum/urine-only, organoids-only, PDX-only, animal tissue. Mixed tissue+organoid → manual review.",
      qc_candidate: "Passed (QC)",
      qc_candidate_desc: "Candidate verdict — material and filters passed. Same rows as Discovery «Passed».",
      qc_manual: "Manual review",
      qc_manual_desc: "PRIDE with missing plex/unclear design plus papers without PXD. Not in «Passed».",
      qc_exclude: "Excluded (verdict)",
      qc_exclude_desc: "Reached the candidate bucket but QC/data said Exclude — not in the main list.",
      qc_rejected: "Rejected (material)",
      qc_filtered: "Filtered (technical)",
      qc_pubs: "publications analyzed",
      atlas_title: "Atlas profile",
      atlas_lead: "Human Cancer-Associated TMT Proteome Atlas summary — metadata only, catalog not exported",
      atlas_datasets: "datasets",
      atlas_publications: "unique IDs",
      atlas_repos: "Repositories",
      atlas_organs: "Top organs / tissues",
      atlas_diseases: "Top diseases",
      atlas_tmt: "TMT plexes",
      atlas_keywords: "Discovery search keywords",
      atlas_link: "Registry on GitHub",
      atlas_discovery: "Analyze new datasets",
      portal_title: "Human Cancer-Associated TMT Proteome Atlas",
      portal_lead:
        "Monitor human TMT in PRIDE, PDC, MassIVE, iProX · LLM abstracts · large literature cohorts",
      card_discovery_title: "Full Discovery analysis",
      card_discovery_desc: "Unified table: new PXD/PDC · papers · cohorts · QC · data files",
      card_qc_title: "QC report",
      card_qc_desc: "Passed / manual / Exclude / rejected — same QC rules as Discovery",
      card_atlas_title: "Atlas profile",
      card_atlas_desc: "Catalog stats: repositories, organs, diseases, TMT plexes",
      card_cohorts_title: "Large cohorts",
      card_cohorts_desc: "Proteomics & multi-omics: large patient cohorts, abstract text mining",
      card_map_title: "Interactive organ map",
      card_map_desc: "TMT projects by organ · ?organ= deep links · read-only catalog",
      card_ai_title: "AI keyword search",
      card_ai_desc: "PRIDE, PDC, Europe PMC by atlas profile · LLM abstract screening",
      ai_title: "AI keyword search",
      ai_lead: "Repository + literature search with LLM scoring — same engine as the Discovery portal",
      ai_how_title: "How to use",
      ai_step1: "Open the live app — the «AI search» tab is selected by default",
      ai_step2: "Edit keywords or keep atlas profile defaults (organs, diseases, TMT)",
      ai_step3: "Click Run search — steps 1–4: repositories → Europe PMC → filters → LLM",
      ai_step4: "Review IDs and papers; add to CSV only via run_revisor.py add --apply",
      ai_launch_title: "Launch interactive search",
      ai_launch_desc: "Full search runs in Streamlit (APIs + local LLM). projects.csv is never auto-updated.",
      ai_launch_btn: "Open AI search app",
      ai_view_discovery: "View last Discovery scan",
      ai_keywords_title: "Default atlas keywords",
      ai_keywords_desc: "From catalog profile — paste into the app or edit before Run search",
      ai_iframe_fallback: "If the embed is blank, use the button above (Streamlit may block iframes).",
      ai_badge_live: "Live app",
      map_title: "Human body organ map",
      map_lead: "Interactive TMT catalog by organ — click regions, filter projects, open PRIDE/PDC",
      map_how_title: "How to use",
      map_step1: "Click an organ on the silhouette or use quick links below",
      map_step2: "Browse tissue projects — open repository or PubMed from the sidebar",
      map_step3: "Share deep links: add ?organ=gastric (or other organ key) to the map URL",
      map_open_full: "Open full-screen map",
      map_embed_hint: "Embedded from GitHub Pages TMT — scroll inside the frame if needed",
      map_organs_title: "Quick organ links",
      card_update_title: "Update data",
      card_update_desc: "Run: python run_discovery.py scan · publish · export for GitHub Pages",
      portal_deploy_note:
        "Organ map: TMT/index.html (?organ=). Discovery portal lives in docs/ and docs/site/.",
      cohorts_title: "Large cohorts — proteomics & multi-omics",
      cohorts_lead: "Europe PMC + text mining: patients, N, omics, TMT",
      cohorts_method: "text mining · Europe PMC",
      cohorts_note:
        "Selection: human proteomics/phosphoproteomics, large cohorts (N≥50 from abstract or large-scale/multi-omics). Atlas PMIDs excluded. N is auto-extracted — verify manually.",
      kpi_cohorts: "papers listed",
      kpi_with_n: "with patient N",
      kpi_multi_omics: "multi-omics",
      kpi_scanned: "EPMC scanned",
      search_cohorts: "Search title, description…",
      sec_cohorts_table: "Paper list",
      no_cohorts: "No cohort papers — run scan",
      guide_title: "How to read the table",
      guide_lead:
        "One screen for new TMT projects not in the catalog. Default view: Project rows only (PXD/PDC/MSV/IPX).",
      guide_columns_title: "Columns",
      table_scroll_hint: "Wide table — scroll right for all columns. Projects tab = data; Guide tab = column legend.",
      col_help_type: "Project = repository accession; Paper = literature without ID; Cohort = large cohort from Europe PMC.",
      col_help_id:
        "Repository: accession + blue PRIDE/PDC/MassIVE/iProX link. Paper: Europe PMC or PXD when resolved from PMID. Links also in Title.",
      col_help_disease:
        "Disease from metadata or inferred from title/description. Use Disease filter above the table.",
      col_help_year: "Publication or submission year from PRIDE/PDC or PubMed.",
      col_help_title: "Title (click → PRIDE/PDC or PubMed), description, and PMID / Europe PMC links.",
      col_help_design: "Design and TMT plex. If PRIDE omits plex — yellow badge «TMT plex not specified — needs review».",
      col_help_omics: "Omics type: proteomics, phospho, multi-omics (cohorts).",
      col_help_patients: "Patients mentioned in text: yes / maybe / no.",
      col_help_n: "Patient/sample N from abstract (auto-extracted — verify manually).",
      col_help_verdict: "Candidate = atlas fit; Watch = surveillance; Exclude = not suitable.",
      col_help_confidence: "Confidence A–D: A = protein table + design OK; B = quant files; C = watch; D = exclude.",
      col_help_similar:
        "Catalog similarity (Jaccard). Collapsed row — click to expand all PXD/PDC · % matches.",
      col_help_fit: "LLM atlas fit (yes/maybe/no) or cohort score 0–100 for literature.",
      col_help_analysis: "AI abstract summary + evidence chain (filters, LLM, similarity).",
      col_help_data: "Protein-level table in repository or local mirror.",
      col_help_links: "Deprecated — links moved to the Title column.",
      guide_filters_title: "Toolbar filters",
      guide_filters_type: "Row type: all / projects / papers / cohorts.",
      guide_filters_source: "Source: PRIDE, PDC, MassIVE, iProX, Europe PMC.",
      guide_filters_search: "Search ID, title, PMID, description, analysis text.",
      guide_similarity_title: "Atlas similarity",
      guide_similarity_desc:
        "Each candidate is scored against projects.csv (title, tissue, disease, TMT). 80%+ very close; 40–60% same theme; <30% new niche. Click catalog PXD in Similar column for PRIDE.",
      tech_title: "Discovery Agent pipeline",
      tech_lead: "Step-by-step description of the last scan — ready for Methods / Supplementary.",
      tech_step1: "1. PRIDE Archive API v3 + PDC UI — TMT keywords, Homo sapiens, years from config.yaml.",
      tech_step2: "2. MassIVE and iProX — same TMT ATLAS profile keywords.",
      tech_step3: "3. Hard filters: organism, TMT >6 plex, tissue/cell line, reject plasma-only.",
      tech_step4: "4. Material QC + data availability gate (protein-level table in repository).",
      tech_step5: "5. Europe PMC cohort literature; LLM abstract read (Ollama/API when enabled).",
      tech_step6: "6. Similarity vs projects.csv; confidence tier A–D; publish to site (catalog unchanged).",
      tech_llm_title: "LLM & models",
      tech_llm_desc:
        "Abstract screening: local Ollama (Qwen) or cloud API (config.yaml). Verdict and tier are rule-based + LLM labels; not calibrated probability.",
      tech_manifest_title: "Full scan manifest (JSON)",
    },
  };

  function buildDict(lang) {
    const dict = { brand_title: SHARED.brand_title };
    for (const [key, val] of Object.entries(SHARED)) {
      if (key === "brand_title") continue;
      dict[key] = val[lang] || val.en || val;
    }
    Object.assign(dict, PAGE[lang] || PAGE.en);
    return dict;
  }

  const T = { ru: buildDict("ru"), en: buildDict("en") };

  function getLang() {
    return localStorage.getItem(STORAGE_KEY) || "ru";
  }

  function setLang(lang) {
    localStorage.setItem(STORAGE_KEY, lang);
    document.documentElement.lang = lang;
    apply(lang);
    document.querySelectorAll(".lang-toggle button").forEach((btn) => {
      btn.classList.toggle("active", btn.dataset.lang === lang);
    });
  }

  const TAXON_RE = /\b(Homo sapiens|Mus musculus|Rattus norvegicus|Gallus gallus)\b/g;

  function taxonizeEl(el) {
    if (!el || el.querySelector(".taxon-name")) return;
    const text = el.textContent || "";
    if (!TAXON_RE.test(text)) return;
    TAXON_RE.lastIndex = 0;
    el.innerHTML = text.replace(
      TAXON_RE,
      '<span class="taxon-name">$1</span>'
    );
  }

  function apply(lang) {
    const dict = T[lang] || T.en;
    document.querySelectorAll("[data-i18n]").forEach((el) => {
      const key = el.getAttribute("data-i18n");
      if (dict[key] === undefined) return;
      let text = dict[key];
      const suffix = el.getAttribute("data-i18n-suffix");
      if (suffix) {
        text = String(text).replace("{n}", suffix).replace("{score}", suffix);
      }
      if (el.tagName === "INPUT") {
        el.placeholder = text;
      } else {
        el.textContent = text;
        taxonizeEl(el);
      }
    });
    document.querySelectorAll("[data-i18n-title]").forEach((el) => {
      const key = el.getAttribute("data-i18n-title");
      if (dict[key] !== undefined) el.title = dict[key];
    });
    document.querySelectorAll("[data-i18n-placeholder]").forEach((el) => {
      const key = el.getAttribute("data-i18n-placeholder");
      if (dict[key] !== undefined) el.placeholder = dict[key];
    });
    document.querySelectorAll(".lang-block").forEach((el) => {
      if (el.classList.contains("lang-en") && el.classList.contains("lang-ru")) {
        el.style.display = "";
        return;
      }
      if (lang === "ru") {
        el.style.display = el.classList.contains("lang-ru") ? "" : "none";
      } else {
        el.style.display = el.classList.contains("lang-en") ? "" : "none";
      }
    });
    if (lang === "ru") {
      document.querySelectorAll(".cell-stack.cell-analysis, .cell-title-block").forEach((wrap) => {
        const ruBlocks = wrap.querySelectorAll(".lang-block.lang-ru");
        if (!ruBlocks.length) return;
        wrap.querySelectorAll(".lang-block.lang-en:not(.lang-ru)").forEach((el) => {
          el.style.display = "none";
        });
      });
    }
    document.querySelectorAll(".cell-desc, .cell-summary, .note, .guide-row-desc").forEach(taxonizeEl);
    document.dispatchEvent(new CustomEvent("atlas:lang", { detail: { lang } }));
  }

  (function boot() {
    const lang = getLang();
    document.documentElement.lang = lang;
    apply(lang);
  })();

  document.addEventListener("DOMContentLoaded", () => {
    const lang = getLang();
    apply(lang);
    document.querySelectorAll(".lang-toggle button").forEach((btn) => {
      btn.classList.toggle("active", btn.dataset.lang === lang);
      btn.addEventListener("click", () => setLang(btn.dataset.lang));
    });
  });

  window.AtlasI18n = { setLang, getLang, T };
})();
