# GitHub — интеграция Atlas (только чтение)

## Политика безопасности

| Действие | Разрешено |
|----------|-----------|
| Просмотр репозиториев, списков файлов | Да |
| Чтение содержимого файлов | Да |
| Сравнение PXD: CSV ↔ GitHub ↔ локальный диск | Да |
| Поиск новых проектов для каталога | Да |
| **Удаление** файлов/веток на GitHub | **Нет** |
| **Push / commit** на GitHub | **Нет** (не реализовано) |

Ничего на GitHub не удаляется и не перезаписывается без вашего отдельного явного решения вне этой платформы.

## Репозитории (`config.yaml`)

| Ключ | Репозиторий | Папка проектов |
|------|-------------|----------------|
| `atlas_repo` | [arinaatom-cyber/TMT](https://github.com/arinaatom-cyber/TMT) | `projects/` |
| `data_repo` | [arinaatom-cyber/tmt-projects](https://github.com/arinaatom-cyber/tmt-projects) | `Projects/` |

`tmt-projects` может быть **приватным** → задайте токен:

```powershell
$env:GITHUB_TOKEN = "ghp_xxxx"   # только read / Contents read
python run_github.py repos
```

## Команды

```powershell
python run_github.py policy      # правила
python run_github.py repos       # доступность репо
python run_github.py projects    # все PXD на GitHub
python run_github.py compare     # расхождения с data/projects.csv
python run_github.py analyze PXD005410
python run_github.py ls projects --repo atlas
python run_github.py cat projects/PXD005410/README.md --repo atlas
python run_github.py report      # JSON → reports/github_integration_*.json
```

Через mini-app:

```powershell
python atlas_app.py github compare
python atlas_app.py github report
```

## Интеграция в пайплайн

- `python run_revisor.py scan` — блок `new_github_projects`
- `python run_agent.py` — секция `github_integration` в отчёте

## Кандидаты в каталог

PXD есть на GitHub, но нет в `data/projects.csv` → список `only_on_github` в compare/report.  
Добавление в CSV — только через `run_revisor.py add --apply` (локально, не на GitHub).
