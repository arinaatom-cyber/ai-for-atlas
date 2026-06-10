# Функции платформы Atlas (май 2026)

Локальная платформа: таблица `data/projects.csv`, папки `tmt-projects/Projects/<PXD>/`, отчёты в `reports/`. **Без Google Sheets и без API-ключей** (ИИ — GPT4All/Ollama).

---

## 1. Компоненты

| Компонент | Файл | Назначение |
|-----------|------|------------|
| **Atlas Agent** | `run_agent.py` | Полный отчёт: правила, PRIDE, литература, локальный ИИ |
| **Mini-app** | `atlas_app.py` | Карточка проекта, todo, stat-планы |
| **Revisor** | `run_revisor.py` | Поиск ошибок, авто-правки, новые публикации |
| **Конфиг** | `config.yaml` | Пути, PRIDE, LLM |

---

## 2. Таблица `data/projects.csv`

### Загрузка
- `load_projects_table(path)` — CSV UTF-8
- `primary_project_id(raw)` — PXD из `PXD029216_BLAST` → `PXD029216`

### Полнота строки (зелёная / белая)
- `row_completeness(row)` — Unified-колонки → `complete` | `partial` | `todo`
- `audit_table(df)` → `data/workflow_audit.csv`

**Unified-колонки:** Platform MS, TMT Label, Normalization Strategy, FASTA, FDR, Result Files, Quantification_Format.

### Правила целостности
- `dependency_rules(df)` — TMT без нормализации, без Result Files, Organ/Tissue
- `column_coverage(df)` — % заполнения по группам колонок
- `normalization_landscape(df)` — сводка стратегий нормализации

---

## 3. Ревизор (`atlas_agent/revisor/`)

### Проверки (`checks.py`)
| Код | Смысл |
|-----|--------|
| `empty_project_id` | Пустая строка |
| `duplicate_primary_id` | Один PXD в нескольких строках |
| `incomplete_unified` / `partial_unified` | Не заполнены Unified |
| `tmt_no_normalization` | TMT без нормализации |
| `tmt_no_result_file` | TMT без файла результата |
| `invalid_pmid` / `pmid_format` | PMID исправим автоматически |
| `missing_project_folder` | Нет папки на диске |
| `result_file_not_on_disk` | Имя в таблице ≠ файл |

### Авто-правки (`fixes.py`) — только безопасные
- Обрезка пробелов в Project ID и текстовых полях
- PMID: `12345.0` → `12345`
- Перед записью: бэкап `projects_backup_YYYYMMDD_HHMMSS.csv`

### Мониторинг литературы (`literature_watch.py`)
- **Europe PMC** — новые human TMT статьи с 2023+
- **PRIDE** — human + TMT + submission ≥ 2020
- Исключение PMID/PXD уже в таблице

---

## 4. GitHub (только чтение)

См. [GITHUB_INTEGRATION.md](./GITHUB_INTEGRATION.md).

| Модуль | Функции |
|--------|---------|
| `sources/github_client.py` | `list_contents`, `get_file_text`, `list_pxd_directories` |
| `sources/github_analyzer.py` | `compare_sources`, `build_github_integration_report` |
| `run_github.py` | CLI: `repos`, `projects`, `compare`, `analyze`, `report` |

**Удаление и push на GitHub запрещены.**

---

## 5. Внешние источники

| Источник | Модуль | Функции |
|----------|--------|---------|
| PRIDE | `sources/pride.py` | `fetch_project`, `search_human_tmt_projects` |
| Europe PMC | `sources/literature.py` | `fetch_abstract`, `text_mentions_normalization` |
| Локальные файлы | `analysis/result_files.py` | `audit_local_files`, `inspect_matrix_file` |

---

## 6. TMT-каналы и матрица белков

Модуль `atlas_agent/analysis/tmt_channels.py`:

| Что | Откуда |
|-----|--------|
| Аннотация канала (126, 127N…) | `TMT Channels Used` / `Comparison` / `Additional` |
| Роль: референс / контроль / case | эвристика по тексту (Control, Healthy, Cancer, …) |
| Нормализация | `Normalization Strategy`, `Quantification_Format` + колонки `126/(126+127_N+…)` в файле |
| Матрица | `tmt-projects/Projects/<PXD>/_extracted/*.txt` |

```powershell
python atlas_app.py tmt PXD005410
python atlas_app.py tmt PXD005410 --html   # → reports/tmt_view_PXD005410.html
```

В HTML: таблицы каналов по ролям, описание нормализации, превью белков × сырые каналы.

---

## 7. Статистика по проектам

- `build_stats_plan(row)` — JSON + R-шаблон
- `project_card(df, pxd, tmt_root)` — всё в одной карточке для `lookup`
- Экспорт: `data/stats_plans/<PXD>_stats.R`, `<PXD>_plan.json`

---

## 8. ИИ (без ключей)

`atlas_agent/llm_client.py` — цепочка **auto**: Ollama → GPT4All → правила.

- `analyze_report(payload)` — резюме отчёта
- `ask_about_project(row, question)` — вопрос по одному PXD

---

## 9. Команды

```powershell
cd "C:\Users\Arina1996\Desktop\AI for atlas"

# Полный агент
python run_agent.py

# Ревизор
python run_revisor.py audit -v
python run_revisor.py fix              # что изменится
python run_revisor.py fix --apply      # записать + бэкап
python run_revisor.py scan             # новые PRIDE и статьи
python run_revisor.py all              # всё разом

# Mini-app
python atlas_app.py lookup PXD012173
python atlas_app.py sync
python atlas_app.py revisor audit
python atlas_app.py revisor scan
```

---

```powershell
python run_github.py compare
python run_github.py report
```

---

## 10. Рекомендуемый цикл работы

1. **`revisor audit`** — список ошибок и предупреждений  
2. **`revisor fix --apply`** — мелкие правки PMID/пробелов  
3. Вручную дозаполнить Unified в Excel → сохранить в `data/projects.csv`  
4. **`atlas_app sync`** — обновить `workflow_audit.csv`  
5. **`revisor scan`** — проверить новые публикации и PXD  
6. **`run_agent.py`** — итоговый отчёт с ИИ  

---

*Документ синхронизирован с кодом: revisor v1.0*
