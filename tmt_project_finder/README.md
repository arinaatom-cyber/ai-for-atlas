# TMT Project Finder

Python 3.11+ tool to search proteomics repositories for human TMT projects, classify them, and export Excel reports.

**No LLM.** Does not download result files. Does not modify `data/existing_database.xlsx`.

## Structure

```
tmt_project_finder/
├── app.py
├── config.yaml
├── dictionaries.yaml
├── requirements.txt
├── data/existing_database.xlsx   # read-only catalog
├── outputs/                      # generated Excel + report
└── src/
    ├── search_sources.py
    ├── parse_sources.py
    ├── extract_metadata.py
    ├── classify_projects.py
    ├── duplicate_check.py
    ├── deleted_check.py
    ├── save_outputs.py
    └── report.py
```

## Install

```bash
cd tmt_project_finder
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements.txt
python scripts/init_database.py
```

## Run

```bash
# CLI pipeline
python run.py

# Streamlit UI
streamlit run app.py
```

## UI tabs

- **Dashboard** — counts + last report
- **Search** — Run Search / Generate Report
- **Found / High / Medium / Manual / Rejected / Duplicates / Previously Removed**
- **Export** — download Excel files

## Classification

| Class | Rule |
|-------|------|
| `high_priority_check` | human + TMT >6 channels (7–18, incl. TMTpro18) + allowed material |
| `medium_priority_check` | human confirmed, partial metadata |
| `manual_check` | ambiguous TMT / organism / material |
| `reject` | rejected organism, TMT, or material |
| `duplicate` | match in main database sheet |
| `rejected_previously_removed` | match in Удалено / Deleted sheet |

## Database

`data/existing_database.xlsx`:

- Sheet **Database** — main catalog (duplicate check)
- Sheet **Удалено** — previously removed projects

Columns: `Project ID`, `PMID`, `DOI`, `Title`, `URL`

## Outputs

| File | Content |
|------|---------|
| `outputs/found_projects.xlsx` | All found |
| `outputs/high_priority.xlsx` | High priority |
| `outputs/medium_priority.xlsx` | Medium priority |
| `outputs/manual_check.xlsx` | Manual review |
| `outputs/rejected.xlsx` | Rejected |
| `outputs/duplicates.xlsx` | In catalog |
| `outputs/previously_removed.xlsx` | Deleted sheet matches |
| `outputs/report.md` | Summary report |
| `outputs/search_log.json` | Machine log |
