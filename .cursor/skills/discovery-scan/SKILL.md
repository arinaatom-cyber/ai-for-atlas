---
name: discovery-scan
description: Runs Atlas Discovery Agent to find new TMT proteomics projects (PRIDE, PDC, Europe PMC) not in projects.csv. Use when the user asks for discovery scan, new projects, weekly search, discovery_index.html, or updating the discovery website.
---

# Discovery Scan

## Quick run

```powershell
cd "c:\Users\Arina1996\Desktop\AI for atlas"
python run_discovery.py scan
```

Expected ~1–2 min. On success:

- `data/discovery_history/latest.json` — full result
- `reports/discovery_index.html` — **website** with all new projects
- `reports/discovery_report_*.md` — human report

## Show results

```powershell
python run_discovery.py latest
start reports\discovery_index.html
streamlit run discovery_app.py
```

## Checklist after scan

```
- [ ] summary.new_projects > 0 or explain why 0
- [ ] reports/discovery_index.html exists and opens
- [ ] latest.json new_projects length matches summary.new_projects
- [ ] No writes to data/projects.csv
```

## If 0 new projects

1. Check `summary.source_stats` (PRIDE v3, PDC, literature_resolved)
2. Europe PMC 503 — retry; search still works via PRIDE+PDC
3. Do not fall back to showing PMID-only articles as "projects"

## Weekly automation

```powershell
powershell -File scripts/run_weekly_discovery.ps1
```

Task Scheduler: weekly, same command.

## UI / site

| Surface | Path |
|---------|------|
| Static HTML | `reports/discovery_index.html` |
| Streamlit | `discovery_app.py` → http://localhost:8501 |
| Dashboard | `reports/dashboard.html` (Discovery section) |

## Adding to catalog (manual only)

After user review:

```powershell
python run_revisor.py add --apply
```

Never auto-modify `projects.csv`.
