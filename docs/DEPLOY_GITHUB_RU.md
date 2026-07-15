# Почему 404 и как исправить

## Архитектура URL (важно)

| URL | Файл | Назначение |
|-----|------|------------|
| `https://…/TMT/` | **`index.html` (корень)** | Интерактивная карта органов, `?organ=Bladder` |
| `https://…/TMT/discovery/` | `discovery/index.html` | Портал Discovery (карточки) |
| `https://…/TMT/discovery/discovery.html` | … | Полный анализ кандидатов |
| `https://…/ai-for-atlas/` | `docs/index.html` | Портал (локальный репо) |
| `https://…/ai-for-atlas/site/…` | `docs/site/*` | Страницы Discovery |

**Нельзя** заливать портал в корень TMT — сломаются диплинки `?organ=`.

---

Скриншот **«There isn't a GitHub Pages site here»** = по этому URL **нет опубликованного сайта**.

Сейчас репозиторий **`arinaatom-cyber/ai-for-atlas` не существует** на GitHub.  
Код лежит только на вашем ПК — Pages не из чего собраться.

---

## Вариант A (быстрее): положить сайт в репозиторий **TMT**

У вас **уже работает** Pages: https://arinaatom-cyber.github.io/TMT/

### Шаги

1. В PowerShell в папке проекта:

```powershell
powershell -File scripts\export_site_for_tmt.ps1
```

Скрипт обновляет **только** `human-proteome-atlas/discovery/` (+ `export_for_tmt/discovery/`).  
Корневой `index.html` (карта) **не трогается**.

2. В репозитории TMT: commit + push папки `discovery/`

**https://arinaatom-cyber.github.io/TMT/discovery/discovery.html**

---

## Вариант B: отдельный репозиторий ai-for-atlas

1. Установите [GitHub CLI](https://cli.github.com)

2. В PowerShell:

```powershell
cd "C:\Users\Arina1996\Desktop\AI for atlas"
gh auth login
```

(браузер → войти в GitHub → подтвердить)

3. Создать репо и залить:

```powershell
powershell -File scripts\setup_github_pages.ps1
```

4. GitHub → репозиторий → **Settings → Pages → Source: GitHub Actions**

5. URL:

**https://arinaatom-cyber.github.io/ai-for-atlas/site/discovery.html**

---

## Локально (без GitHub)

```powershell
powershell -File scripts\serve_site.ps1
```

→ http://localhost:8765/site/discovery.html

---

## Частые ошибки

| Ошибка | Причина |
|--------|---------|
| 404 на ai-for-atlas | Репо не создан / не запушен |
| 404 на /TMT/discovery/ | Папка `discovery/` не загружена в TMT |
| Actions красные | Settings → Pages → включить GitHub Actions |
