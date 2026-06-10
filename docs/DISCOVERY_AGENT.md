# Discovery Agent

Autonomous agent that searches the internet for **projects and papers similar to your atlas**, including PDC, CCLE, GTEx, CPTAC, and PRIDE.

## Safety

| Rule | Status |
|------|--------|
| Read `data/projects.csv` | Yes |
| Delete `data/projects.csv` | **Never** |
| Auto-add rows | **Never** (proposals only) |
| Auto-delete rows | **Never** |

## Sources

- **PRIDE** — TMT human proteomics (JSON API)
- **Europe PMC** — recent publications
- **PDC** — Proteomic Data Commons GraphQL
- **CCLE / GTEx / CPTAC** — literature + accession mentions

## Commands

```powershell
python run_discovery.py policy
python run_discovery.py profile    # what the agent knows about your atlas
python run_discovery.py scan
python run_discovery.py latest
python run_discovery.py history
```

## Weekly schedule

```powershell
# Windows Task Scheduler → weekly:
powershell -File scripts/run_weekly_discovery.ps1
```

Or enable GitHub Action: `.github/workflows/weekly_discovery.yml`

## Output

- `reports/discovery_report_YYYYMMDD_HHMMSS.md` — human-readable (local)
- `docs/site/discovery.html` — **public site: only new projects** (not catalog)
- `docs/site/qc.html` — QC report
- `data/discovery_history/latest.json` — last run

**Каталог `projects.csv` не публикуется на сайте** — только фильтр «уже есть».

## Any computer

```powershell
git clone https://github.com/arinaatom-cyber/ai-for-atlas.git
powershell -File scripts/setup_anywhere.ps1
python run_discovery.py scan
streamlit run discovery_app.py
```

Each candidate includes:

- `similar_in_catalog` — closest existing PXD/PDC in your table
- `processing_tips` — suggested normalization / pipeline notes
- `recommendation` — `review_for_catalog` or `skip_duplicate`

## Adding to catalog

Only after **your** review:

```powershell
python run_revisor.py add --apply   # creates backup first
```
