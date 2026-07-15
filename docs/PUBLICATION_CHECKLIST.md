# Чеклист публикации — Human Cancser Assosiated TMT Proteome Atlas + Discovery

Статус на 2026-07-15. Отмечайте `[x]` по мере выполнения.

---

## 1. Данные и каталог

| # | Критерий | Статус | Комментарий |
|---|----------|--------|-------------|
| 1.1 | Мастер-таблица TMT ATLAS (123+ строк) согласована с рукописью | ⬜ | Excel vs CSV: 124 vs 123 строк; дубликаты PXD021265, PXD031107 |
| 1.2 | Каждый проект → орган на карте (organ audit) | ⬜ | 122/123 OK; PXD015359 → Other (hPSC) |
| 1.3 | Числовые поля (Patients, Proteins) без артефактов | ⬜ | PXD066224 proteins=3 (ячейка-таблица каналов) |
| 1.4 | PMID / Project ID / Database согласованы | ⬜ | Ручная верификация выборки 10% |
| 1.5 | Политика read-only задокументирована | ✅ | `discovery.policy`, `.cursor/rules` |

---

## 2. GitHub и воспроизводимость

| # | Критерий | Статус | Комментарий |
|---|----------|--------|-------------|
| 2.1 | Репозиторий **ai-for-atlas** публичен | ✅ | GitHub Pages Actions |
| 2.2 | Репозиторий **TMT** (карта) + **tmt-projects** (данные) | ✅ | Pages на TMT |
| 2.3 | `config.example.yaml` без секретов | ✅ | `.env` в gitignore |
| 2.4 | CI: pytest на push | ⬜ | Добавить workflow `tests/` |
| 2.5 | Версия Python + `requirements.txt` зафиксированы | ⬜ | Pin major versions для статьи |
| 2.6 | DOI / Zenodo snapshot перед подачей | ⬜ | После финального коммита |

---

## 3. Discovery pipeline (Methods)

| # | Критерий | Статус | Комментарий |
|---|----------|--------|-------------|
| 3.1 | Multi-stage pipeline описан в Methods | ⬜ | `docs/DISCOVERY_PIPELINE_RU.md` — черновик |
| 3.2 | Критерии включения (human, TMT≥10ch, plex) | ✅ | `filters.py`, `policy.py` |
| 3.3 | Источники API с датами сканов | ⬜ | Последний scan: 2026-06-18 |
| 3.4 | ИИ: модель, промпт, fallback (regex) | ⬜ | Z.AI ключ не в .env |
| 3.5 | Оценка false positive / manual check | ⬜ | QC tab + rejected counts |
| 3.6 | Еженедельный scan автоматизирован | ⬜ | `run_weekly_discovery.ps1` — проверить Task Scheduler |

---

## 4. Streamlit portal (UI)

| # | Критерий | Статус | Комментарий |
|---|----------|--------|-------------|
| 4.1 | Вкладка **органы → GitHub папки** | ✅ | `discovery_app.py` + `portal_index.py` |
| 4.2 | Вкладка **Discovery** (candidate/manual/rejected) | ✅ | |
| 4.3 | Вкладка **поиск по ключевым словам** + finding_note | ✅ | Не только заголовок статьи |
| 4.4 | Прямые ссылки: PRIDE, PubMed, карта, tmt-projects | ✅ | |
| 4.5 | i18n RU/EN на статическом сайте | ✅ | `site/assets/i18n.js` |
| 4.6 | Деплой Streamlit (опционально) | ⬜ | Streamlit Cloud / внутренний сервер |

---

## 5. Сайт и визуализация

| # | Критерий | Статус | Комментарий |
|---|----------|--------|-------------|
| 5.1 | `docs/site/discovery.html` актуален | ⬜ | Обновить после свежего scan |
| 5.2 | KPI (проекты / пациенты / белки) с каталога | ⬜ | Синхронизация с Excel |
| 5.3 | QC report (`qc.html`) для рецензентов | ✅ | |
| 5.4 | Карта органов не перезаписывается Discovery | ✅ | `export_site_for_tmt.ps1` только `discovery/` |

---

## 6. Тесты и качество кода

| # | Критерий | Статус | Комментарий |
|---|----------|--------|-------------|
| 6.1 | `pytest tests/` зелёный | ✅ | 25+ тестов |
| 6.2 | E2E `verify_discovery_e2e.py` | ⬜ | Прогнать после scan |
| 6.3 | Organ classify vs human-proteome-atlas | ⬜ | `audit_project_organs.py` |
| 6.4 | Нет секретов в репозитории | ✅ | `.env` ignored |

---

## 7. Рукопись (текст)

| # | Критерий | Статус | Комментарий |
|---|----------|--------|-------------|
| 7.1 | §2.8 Discovery pipeline в Methods | ⬜ | Черновик в прошлых сессиях |
| 7.2 | Схема воронки (mermaid / Fig.) | ⬜ | `DISCOVERY_PIPELINE_RU.md` |
| 7.3 | Ограничения: read-only, ручное добавление в каталог | ⬜ | |
| 7.4 | Ссылки на live portal URL | ⬜ | ai-for-atlas + TMT |
| 7.5 | Литература Discovery — APA 7 | ⬜ | Когорты / PMID в сайте |

---

## 8. Приоритетные следующие шаги (top 5)

1. **ZAI_API_KEY** в `.env` → свежий `run_discovery.py scan` → `publish` → `push_site_github.ps1`
2. **Исправить в Excel** PXD066224 (proteins), сверить 124 строки
3. **CI workflow** с `pytest` на GitHub Actions
4. **Обновить Methods §2.8** из `DISCOVERY_PIPELINE_RU.md`
5. **Zenodo DOI** после freeze версии

---

## Быстрая проверка перед подачей

```powershell
python -m pytest tests/ -q
python run_discovery.py scan
python run_discovery.py publish
python scripts/verify_discovery_e2e.py
streamlit run discovery_app.py
```

Ожидаемо: тесты OK · scan без ошибок · сайт открывается · Streamlit показывает органы + Discovery + keywords.
