# TMT-канал → пациент (Protomix green + файлы)

## Что делает пайплайн

1. Берёт **зелёные** проекты (`complete` в `workflow_audit` = заполненные строки Protomix).
2. Собирает аннотации каналов из:
   - `TMT Channels Used` / `Comparison` / `Additional`
   - многострочных карт (`Patient 1 → 126`, `set_k_1 = X126 = Normal`, …)
   - Excel на диске (`*channel*mapping*`, `*sample*info*`)
   - GitHub `tmt-projects` (если есть `GITHUB_TOKEN`, read-only)
3. Сопоставляет **channel_tag** (126, 127N, …) с **patient_id** и **condition**.
4. **Обучает** простые правила по словам в label (для подсказок на неразмеченных каналах).

## Команды

```powershell
# Старт: только зелёные PDC (Protomix)
python run_channels.py build --pdc

python run_channels.py show PDC000110
python run_channels.py apply

python atlas_app.py channels build --pdc
python atlas_app.py channels show PDC000110
```

### Файлы PDC

- `data/channel_patient_dataset_pdc_green.csv`
- `data/channel_patient_model_pdc_green.json`

## Выходные файлы

| Файл | Содержание |
|------|------------|
| `data/channel_patient_dataset.csv` | все каналы green-проектов |
| `data/channel_patient_training_green.csv` | то же для обучения |
| `data/channel_patient_model.json` | правила token → patient |
| `data/channel_patient_suggestions.csv` | после `apply` — подсказки |

## Колонки датасета

- `project_id`, `channel_tag`, `label`, `patient_id`, `condition`, `role`
- `source` — откуда взято (csv, excel, local, github, learned)
- `confidence` — 0–1
- `protomix_status` — `complete` для зелёных

## Рекомендации

- В таблице пишите каналы в формате: `127N (Patient 2 tumor)` или таблицу Patient×Channel как в PXD026279.
- Кладите `*_channel_mapping*.xlsx` в папку проекта — они читаются автоматически.
- Для приватного GitHub: `$env:GITHUB_TOKEN = "..."` (только чтение).
