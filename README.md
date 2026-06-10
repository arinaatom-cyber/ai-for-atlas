# Atlas TMT Proteomics Platform

Local platform for curating a **human TMT proteomics atlas**: project table, channel annotations, normalization checks, and a **Discovery Agent** that finds new projects on PRIDE and PDC.

**`data/projects.csv` is never deleted or overwritten by agents.**

---

## Discovery — на любом компьютере

### Быстрая установка

**Windows:**
```powershell
git clone https://github.com/arinaatom-cyber/ai-for-atlas.git
cd ai-for-atlas
powershell -File scripts/setup_anywhere.ps1
```

**Linux / macOS:**
```bash
git clone https://github.com/arinaatom-cyber/ai-for-atlas.git
cd ai-for-atlas
bash scripts/setup_anywhere.sh
```

### Поиск новых проектов

```bash
pip install -r requirements.txt
python run_discovery.py scan      # PRIDE + PDC + QC
python run_discovery.py latest    # последний результат
streamlit run discovery_app.py    # UI → http://localhost:8501
```

### Сайт (GitHub Pages)

После скана публикуется **`docs/site/`**:

| Страница | Содержимое |
|----------|------------|
| `docs/site/discovery.html` | **Только новые** PXD/PDC/MSV/IPX (не в каталоге) |
| `docs/site/qc.html` | QC: candidate / manual-check / rejected |
| `docs/index.html` | Портал + инструкция |

**Важно:** проекты из `projects.csv` **никогда не попадают на сайт**. Каталог используется только локально для фильтра «уже есть».

```bash
python scripts/publish_site.py   # обновить docs/site/ вручную
```

GitHub Pages: Settings → Pages → Source: **GitHub Actions** (workflow `discovery_pages.yml`).

---

## Components

| Component | Command | Purpose |
|-----------|---------|---------|
| **Discovery Agent** | `python run_discovery.py scan` | New TMT projects (PRIDE, PDC) |
| **Discovery UI** | `streamlit run discovery_app.py` | Desktop web UI |
| **Revisor** | `python run_revisor.py audit` | Validate table + local files |
| **Channel mapper** | `python run_channels.py build --pdc` | TMT channel → patient |
| **TMT viewer** | `python atlas_app.py tmt-all` | Channels, matrix HTML |

---

## Discovery policy

1. Reads `data/projects.csv` (**read-only**)
2. Searches PRIDE v3, PDC uiStudySummary, Europe PMC
3. Filters: human only, TMT 10/11/12/16, material QC
4. Outputs **only new** project accessions
5. Saves `data/discovery_history/latest.json`
6. Publishes `docs/site/` (new projects only)

```bash
python run_discovery.py policy
python run_discovery.py profile
python run_discovery.py history
```

### Adding to catalog (manual only)

```bash
python run_revisor.py add --apply   # creates backup first
```

---

## GitHub

| Repo | Role |
|------|------|
| This repo (`ai-for-atlas`) | Discovery code + site |
| [arinaatom-cyber/TMT](https://github.com/arinaatom-cyber/TMT) | Atlas web |
| [arinaatom-cyber/tmt-projects](https://github.com/arinaatom-cyber/tmt-projects) | Raw data (read-only) |

```bash
python run_github.py compare   # CSV vs GitHub (read-only)
```

### Push code

```bash
git init
git add .
git commit -m "Atlas Discovery platform"
gh auth login
gh repo create arinaatom-cyber/ai-for-atlas --public --source=. --push
```

---

## Structure

```
data/projects.csv           # catalog (read-only for agents)
data/discovery_history/     # scan JSON logs
docs/site/                  # public site (new projects only)
run_discovery.py
discovery_app.py
atlas_agent/discovery/      # search + QC
```

---

## Weekly automation

**Windows:** `scripts/run_weekly_discovery.ps1`  
**GitHub Actions:** `.github/workflows/discovery_pages.yml`
