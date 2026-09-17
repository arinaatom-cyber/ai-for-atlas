from __future__ import annotations

import json
import shutil
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from atlas_agent.viz.export_flat_candidates import write_candidates_csv

DEST = Path.home() / "Desktop" / "Atlas_Discovery_export"


METHODS = """Материалы и методы
Human Cancer-Associated TMT Proteome Atlas — Discovery

1. Каталог (только чтение)
Кураторский каталог — мастер-таблица уже включённых TMT-проектов. Discovery его только читает: не добавляет, не удаляет и не перезаписывает строки. Автоматического включения нового проекта в атлас нет; запись в каталог возможна только после явного действия куратора.

Локальные файлы:
  data/projects.csv — runtime-каталог для Discovery (мастер-таблица, только чтение)
  project of Proteomics.xlsx (лист TMT ATLAS) — рабочая копия куратора
Сверка ID и ключевых колонок: python scripts/sync_tmt_projects_csv.py (по умолчанию ничего не пишет).
Экспорт Excel → CSV только явно: python scripts/sync_tmt_projects_csv.py --apply.
Автослияния нет: если файлы разойдутся, это видно в отчёте сверки.

2. Поиск
Каталог сформирован по состоянию на снимок скана (см. дату внизу). Автоматический мониторинг новых поступлений в PRIDE / PDC / MassIVE / iProX покрывает период с 2024 года (config discovery.year_from). Более ранние записи добавлены вручную при первичном формировании каталога.

  PRIDE Archive
    Поиск по API (TMT / isobaric, human). Проверяется TMT-плекс 7–18 каналов; TMT6 отклоняется. Если плекс или материал образца не указаны в карточке PRIDE, читаются описание проекта и связанная статья (абстракт PubMed / Europe PMC). Нераспознанный plex даёт вердикт tmt_plex_unspecified (видно в QC).

  PDC (CPTAC / Proteomic Data Commons)
    В метаданных уже есть болезнь, орган/сайт и схема TMT. Правила включения те же, что для PRIDE. Поле organism в GraphQL uiStudySummary отсутствует: исследования считаются человеческими по охвату PDC/CPTAC, если в тексте метаданных нет non-human организма. TMT без распознанного plex не отбрасывается на источнике — уходит в тот же tmt_plex_unspecified, что и PRIDE.

  MassIVE / iProX
    Поиск по API с пагинацией. Описание передаётся в фильтры целиком (до 2500 символов). Неудачные HTTP-запросы считаются в methods_manifest.json (failed_source_requests).

  Europe PMC (статьи)
    Поиск по названиям и похожим публикациям. Статья без номера проекта (PXD / PDC / MSV / IPX) не считается проектом.
    Препринты (Europe PMC source PPR, pubType preprint, bioRxiv/medRxiv) не отбрасываются: поле is_preprint / publication_status=preprint, на сайте бейдж «Препринт». Рецензируемые записи — publication_status=journal.

3. Правила отбора
В список Candidate попадает только то, что одновременно:
  — организм Homo sapiens (явный human / Homo sapiens / patient / известная человеческая раковая линия; мышь, крыса, смесь, только ксенограф — нет);
  — изобарная метка TMT, 7–18 plex (TMT6 и label-free — нет);
  — материал: человеческая ткань (опухоль / adjacent / норма) или раковая клеточная линия человека — это должно быть в метаданных или в статье;
  — только плазма / сыворотка / моча, только органоиды, только PDX — нет;
  — целевой слой: глобальный protein-level протеом (только фосфопротеомика или только пептиды — нет);
  — в репозитории есть protein-level таблица квантификации, если файлы перечислены.

Если плекс, дизайн или материал не прошли проверку, запись не выдаётся как список проектов. Смесь ткань + органоид/3D — единственная корзина смешанного материала. Совпадение голого 7–9-значного числа с PMID каталога не исключает проект автоматически (possible_pmid_match → ручная проверка).

4. Чтение абстракта и карточки проекта
LLM обрабатывает первые N публикаций по релевантности (prefilter score ≥ 0.40; N = abstract_llm_max, по умолчанию 25). Остальные проходят детерминированный keyword-скрининг (regex) как fallback; список regex-only выводится в qc.html для ручной проверки. Полные тексты статей моделью не читаются (title ≤500, abstract ≤3500, Data Availability ≤1500 символов). Провайдер и модель LLM, git-commit пайплайна и лимит N фиксируются в methods_manifest.json рядом со снимком скана.

Орган, болезнь и колонка «Кратко» считаются тем же кодом, что таблица сайта, и пишутся плоскими полями в candidates.csv (supplementary).


5. Схожесть с каталогом
Жёсткий дубликат: тот же PXD/PDC/MSV/IPX (все accession в ячейке Project ID, например IPX… (PXD…)), PMID или DOI — already in catalog.
Jaccard по токенам (название, орган, болезнь, TMT): ≥0.18 — колонка «Похож на»; ≥0.72 — requires_manual_check (тот же датасет в другом репозитории или новый accession после ревизии). Порог 0.72 не исключает запись автоматически.

6. Что получается после скана
  — список Candidate (то, что прошло);
  — таблицы контроля качества (исключено / отклонён материал / техфильтр);
  — JSON-снимок скана (latest.json);
  — статический сайт (discovery.html, qc.html).

Файл каталога этот пайплайн не записывает.

Снимок скана в этой выгрузке: 2026-09-17 (UTC).
"""


LINKS = """Куда выгружаются файлы
======================

НА ЭТОМ КОМПЬЮТЕРЕ
  Папка проекта
    C:\\Users\\Arina1996\\Desktop\\AI for atlas

  Эта выгрузка (копия важных файлов)
    C:\\Users\\Arina1996\\Desktop\\Atlas_Discovery_export

  Каталог (только чтение)
    C:\\Users\\Arina1996\\Desktop\\AI for atlas\\data\\projects.csv
    C:\\Users\\Arina1996\\Desktop\\AI for atlas\\project of Proteomics.xlsx

  Последний скан
    C:\\Users\\Arina1996\\Desktop\\AI for atlas\\data\\discovery_history\\latest.json

  Локальные файлы сайта
    C:\\Users\\Arina1996\\Desktop\\AI for atlas\\docs\\site\\discovery.html
    C:\\Users\\Arina1996\\Desktop\\AI for atlas\\docs\\site\\qc.html

GITHUB (код)
  Код Discovery
    https://github.com/arinaatom-cyber/ai-for-atlas

  Исходники карты органов / сайт TMT
    https://github.com/arinaatom-cyber/TMT

  Папки данных по проектам
    https://github.com/arinaatom-cyber/tmt-projects/tree/main/Projects

САЙТЫ (что открывать в браузере)
  Таблица Discovery (этот репозиторий, GitHub Pages)
    https://arinaatom-cyber.github.io/ai-for-atlas/site/discovery.html

  Контроль качества
    https://arinaatom-cyber.github.io/ai-for-atlas/site/qc.html

  Карта органов
    https://arinaatom-cyber.github.io/TMT/

  Копия Discovery на сайте TMT
    https://arinaatom-cyber.github.io/TMT/discovery/discovery.html

  Streamlit
    https://human-cancser-tmt-proteome-atlas.streamlit.app/

ОТКУДА ИДЁТ ПОИСК (публичные архивы)
  PRIDE Archive
    https://www.ebi.ac.uk/pride/archive

  PDC (CPTAC)
    https://proteomic.datacommons.cancer.gov/pdc/

  MassIVE
    https://massive.ucsd.edu/

  iProX
    https://www.iprox.cn/

  Europe PMC / PubMed
    https://europepmc.org/
    https://pubmed.ncbi.nlm.nih.gov/
"""


def _copy_tree(src: Path, dest: Path) -> None:
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(src, dest)


def _write_candidates_csv(report: dict, path: Path) -> int:
    rows = report.get("candidates") or report.get("new_projects") or []
    return write_candidates_csv(rows, path)


def main() -> int:
    DEST.mkdir(parents=True, exist_ok=True)
    (DEST / "data").mkdir(exist_ok=True)
    (DEST / "catalog").mkdir(exist_ok=True)

    latest = ROOT / "data" / "discovery_history" / "latest.json"
    report = json.loads(latest.read_text(encoding="utf-8")) if latest.is_file() else {}

    shutil.copy2(latest, DEST / "data" / "latest.json")
    _copy_tree(ROOT / "docs" / "site", DEST / "site")

    csv_src = ROOT / "data" / "projects.csv"
    if csv_src.is_file():
        shutil.copy2(csv_src, DEST / "catalog" / "projects.csv")
    xlsx = ROOT / "project of Proteomics.xlsx"
    if xlsx.is_file():
        shutil.copy2(xlsx, DEST / "catalog" / xlsx.name)

    n = _write_candidates_csv(report, DEST / "candidates.csv")

    (DEST / "Materials_and_Methods.txt").write_text(METHODS, encoding="utf-8")
    (DEST / "LINKS.txt").write_text(LINKS, encoding="utf-8")

    readme = (
        "Atlas Discovery — выгрузка важных файлов\n"
        f"Дата выгрузки: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
        "Откройте:\n"
        "  LINKS.txt                     — куда всё выгружается (GitHub и сайты)\n"
        "  Materials_and_Methods.txt     — мат. и методы\n"
        "  site\\discovery.html           — таблица Discovery (откройте в браузере)\n"
        "  site\\qc.html                  — контроль качества\n"
        "  candidates.csv                — список Candidate (Excel, разделитель ;)\n"
        "  data\\latest.json              — полный снимок последнего скана\n"
        "  catalog\\projects.csv          — каталог атласа (только копия, не менять здесь)\n"
        "\n"
        "Каталог в этой папке — копия. Рабочий оригинал: "
        "C:\\Users\\Arina1996\\Desktop\\AI for atlas\\data\\projects.csv\n"
    )
    (DEST / "README.txt").write_text(readme, encoding="utf-8")

    print(f"Export: {DEST}")
    print(f"  candidates.csv — {n} rows")
    print(f"  site/ — {DEST / 'site'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
