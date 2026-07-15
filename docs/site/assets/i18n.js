/** Bilingual UI — единые подписи на всех страницах Discovery */
(function () {
  const STORAGE_KEY = "atlas_site_lang";

  const SHARED = {
    brand_title: "Sirius Human TMT Proteome Atlas",
    nav_home: { ru: "Главная", en: "Home" },
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
    footer_projects: { ru: "tmt-projects", en: "tmt-projects" },
    footer_live: { ru: "Live (GitHub Pages)", en: "Live (GitHub Pages)" },
    filter_all: { ru: "Все", en: "All" },
    filter_yes: { ru: "да", en: "yes" },
    filter_maybe: { ru: "maybe", en: "maybe" },
    filter_no: { ru: "нет", en: "no" },
    filter_pride: { ru: "PRIDE", en: "PRIDE" },
    filter_pdc: { ru: "PDC", en: "PDC" },
    filter_patients_yes: { ru: "пациенты: да", en: "patients: yes" },
    filter_patients_maybe: { ru: "пациенты: возможно", en: "patients: maybe" },
    th_id: { ru: "ID", en: "ID" },
    th_title: { ru: "Название", en: "Title" },
    th_source: { ru: "Источник", en: "Source" },
    th_plex: { ru: "Plex", en: "Plex" },
    th_design: { ru: "Дизайн", en: "Design" },
    th_similar: { ru: "Похож на", en: "Similar to" },
    th_ai: { ru: "ИИ-анализ", en: "AI analysis" },
    th_finding: { ru: "Что найдено", en: "Finding" },
    th_data: { ru: "Данные / файлы", en: "Data / files" },
    th_supplementary: { ru: "Supplementary", en: "Supplementary" },
    th_weight: { ru: "Вес", en: "Weight" },
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
    th_journal: { ru: "Журнал", en: "Journal" },
    th_score: { ru: "Оценка", en: "Score" },
    cell_empty: { ru: "—", en: "—" },
    pat_yes: { ru: "да", en: "yes" },
    pat_maybe: { ru: "возможно", en: "maybe" },
    pat_no: { ru: "нет / неясно", en: "no / unclear" },
    card_open: { ru: "Открыть", en: "Open" },
    card_json: { ru: "latest.json (API)", en: "latest.json (API)" },
    kpi_abstracts_ai: { ru: "абстрактов ИИ", en: "LLM abstracts" },
    no_rows: { ru: "Нет записей", en: "No records" },
  };

  const PAGE = {
    ru: {
      brand_sub: "Discovery · Когорты · QC · каталог read-only",
      footer_policy:
        "Каталог Excel не публикуется. На сайте — только новые кандидаты, литература и анализ.",
      disc_title: "Discovery — полный анализ",
      disc_lead:
        "Новые human TMT проекты · семантический разбор абстрактов · QC материала · доступность данных",
      disc_catalog_hidden: "каталог скрыт",
      disc_catalog_n: "проектов в атласе",
      kpi_new: "новых проектов",
      kpi_pride: "PRIDE",
      kpi_pdc: "PDC",
      kpi_manual: "ручная проверка",
      kpi_rejected: "отклонено",
      kpi_yes_maybe: "да / maybe",
      sec_projects: "Новые проекты",
      sec_projects_desc: "Только PXD / PDC / MSV / IPX, которых нет в TMT ATLAS",
      sec_abstracts: "ИИ-анализ абстрактов",
      sec_literature: "Статьи без accession",
      sec_literature_desc: "По смыслу похоже на атлас; номер проекта не найден",
      sec_qc: "QC — manual / rejected",
      search_projects: "Поиск по ID, названию…",
      search_abstracts: "Поиск по названию, анализу…",
      kpi_papers_no_id: "статей без ID",
      kpi_with_table: "с protein table",
      note_projects_unified:
        "ID и Source → репозиторий · Title → PubMed · Analysis · Data. Plex/Similar убраны. QC: qc.html.",
      sec_cohorts_on_discovery: "Крупные когорты (протеомика и мульти-омика)",
      sec_cohorts_on_discovery_desc: "Europe PMC — пациенты, N, омики, TMT, журнал, score",
      no_projects: "Нет новых проектов",
      no_pubs: "Нет проанализированных статей",
      no_literature: "Нет статей для ручной проверки",
      qc_title: "QC отчёт Discovery",
      qc_lead: "Кандидаты · ручная проверка · отклонённые · технический фильтр",
      qc_rules_title: "Правила материала",
      qc_rules:
        "Только Homo sapiens · опухоль / adjacent normal / плазма·сыворотка·кровь · линии рака OK · исключить organoids-only, PDX-only, xenograft-only, ткань животных · смешанное → manual check.",
      qc_candidate: "Кандидат",
      qc_manual: "Ручная проверка",
      qc_rejected: "Отклонено (материал)",
      qc_filtered: "Отфильтровано (техн.)",
      qc_pubs: "статей проанализировано",
      atlas_title: "Профиль атласа",
      atlas_lead: "Сводка Sirius Human TMT Proteome Atlas — только метаданные, без выгрузки каталога",
      atlas_datasets: "датасетов",
      atlas_publications: "уникальных ID",
      atlas_repos: "Репозитории",
      atlas_organs: "Топ органов / тканей",
      atlas_diseases: "Топ нозологий",
      atlas_tmt: "TMT-плексы",
      atlas_keywords: "Ключевые слова поиска",
      atlas_link: "Реестр на GitHub",
      atlas_discovery: "Анализ новых наборов",
      portal_title: "Atlas Discovery Portal",
      portal_lead:
        "Мониторинг human TMT в PRIDE, PDC, MassIVE, iProX · ИИ-разбор абстрактов · крупные когорты в литературе",
      card_discovery_title: "Полный анализ Discovery",
      card_discovery_desc: "Новые PXD/PDC · Europe PMC · QC · доступность Result Files",
      card_qc_title: "QC отчёт",
      card_qc_desc: "Кандидаты / manual / rejected с ИИ-анализом и колонкой данных",
      card_atlas_title: "Профиль атласа",
      card_atlas_desc: "Статистика каталога: репозитории, органы, нозологии, TMT-плексы",
      card_cohorts_title: "Крупные когорты",
      card_cohorts_desc: "Протеомика и мульти-омика: большие patient cohorts, text mining абстрактов",
      card_map_title: "Интерактивная карта",
      card_map_desc: "TMT-проекты по органам · диплинки ?organ= · каталог read-only",
      card_update_title: "Обновление данных",
      card_update_desc: "Локально: python run_discovery.py scan · publish · export для GitHub Pages",
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
    },
    en: {
      brand_sub: "Discovery · Cohorts · QC · read-only catalog",
      footer_policy:
        "Excel catalog is not published. Site shows new candidates, literature, and analysis only.",
      disc_title: "Discovery — full analysis",
      disc_lead:
        "New human TMT projects · semantic abstract screening · material QC · data availability",
      disc_catalog_hidden: "catalog hidden",
      disc_catalog_n: "projects in atlas",
      kpi_new: "new projects",
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
        "ID and Source → repository · Title → PubMed · Analysis (finding + LLM) · Data files. Plex/Similar removed. QC: qc.html.",
      sec_cohorts_on_discovery: "Large cohorts (proteomics & multi-omics)",
      sec_cohorts_on_discovery_desc: "Europe PMC text mining — patients, N, omics, TMT, journal, score",
      no_projects: "No new projects",
      no_pubs: "No analyzed publications",
      no_literature: "No papers for manual review",
      qc_title: "Discovery QC report",
      qc_lead: "Candidates · manual review · rejected · technical filter",
      qc_rules_title: "Material rules",
      qc_rules:
        "Homo sapiens only · tumor / adjacent normal / plasma·serum·blood · cancer cell lines OK · reject organoids-only, PDX-only, xenograft-only, animal tissue · mixed → manual check.",
      qc_candidate: "Candidate",
      qc_manual: "Manual review",
      qc_rejected: "Rejected (material)",
      qc_filtered: "Filtered (technical)",
      qc_pubs: "publications analyzed",
      atlas_title: "Atlas profile",
      atlas_lead: "Sirius Human TMT Proteome Atlas summary — metadata only, catalog not exported",
      atlas_datasets: "datasets",
      atlas_publications: "unique IDs",
      atlas_repos: "Repositories",
      atlas_organs: "Top organs / tissues",
      atlas_diseases: "Top diseases",
      atlas_tmt: "TMT plexes",
      atlas_keywords: "Discovery search keywords",
      atlas_link: "Registry on GitHub",
      atlas_discovery: "Analyze new datasets",
      portal_title: "Atlas Discovery Portal",
      portal_lead:
        "Monitor human TMT in PRIDE, PDC, MassIVE, iProX · LLM abstracts · large literature cohorts",
      card_discovery_title: "Full Discovery analysis",
      card_discovery_desc: "New PXD/PDC · Europe PMC · QC · Result Files availability",
      card_qc_title: "QC report",
      card_qc_desc: "Candidates / manual / rejected with AI analysis and data column",
      card_atlas_title: "Atlas profile",
      card_atlas_desc: "Catalog stats: repositories, organs, diseases, TMT plexes",
      card_cohorts_title: "Large cohorts",
      card_cohorts_desc: "Proteomics & multi-omics: large patient cohorts, abstract text mining",
      card_map_title: "Interactive organ map",
      card_map_desc: "TMT projects by organ · ?organ= deep links · read-only catalog",
      card_update_title: "Update data",
      card_update_desc: "Run: python run_discovery.py scan · publish · export for GitHub Pages",
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
    return "en";
  }

  function setLang(lang) {
    localStorage.setItem(STORAGE_KEY, lang);
    document.documentElement.lang = lang;
    apply(lang);
    document.querySelectorAll(".lang-toggle button").forEach((btn) => {
      btn.classList.toggle("active", btn.dataset.lang === lang);
    });
  }

  function apply(lang) {
    const dict = T[lang] || T.en;
    document.querySelectorAll("[data-i18n]").forEach((el) => {
      const key = el.getAttribute("data-i18n");
      if (dict[key] !== undefined) {
        if (el.tagName === "INPUT" && el.placeholder !== undefined) {
          el.placeholder = dict[key];
        } else {
          el.textContent = dict[key];
        }
      }
    });
    document.querySelectorAll("[data-i18n-placeholder]").forEach((el) => {
      const key = el.getAttribute("data-i18n-placeholder");
      if (dict[key] !== undefined) el.placeholder = dict[key];
    });
  }

  document.addEventListener("DOMContentLoaded", () => {
    const lang = getLang();
    document.documentElement.lang = lang;
    apply(lang);
    document.querySelectorAll(".lang-toggle button").forEach((btn) => {
      btn.classList.toggle("active", btn.dataset.lang === lang);
      btn.addEventListener("click", () => setLang(btn.dataset.lang));
    });
  });

  window.AtlasI18n = { setLang, getLang, T };
})();
