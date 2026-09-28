---
name: discovery-scan
description: Runs Atlas Discovery Agent to find new TMT proteomics projects (PRIDE, PDC, Europe PMC) not in projects.csv. Use when the user asks for discovery scan, new projects, weekly search, discovery_index.html, or updating the discovery website.
---

# Discovery Scan

## Quick run

```powershell
cd "C:\Users\Sirius\Desktop\ai-for-atlas"
python run_discovery.py scan
python run_discovery.py publish
```

Expected ~1–2 min. On success:

- `data/discovery_history/latest.json` — full result
- `docs/site/discovery.html` — website
- `docs/site/qc.html` — accepted projects only

## Show results

```powershell
python run_discovery.py latest
start docs\site\qc.html
```

## Checklist after scan

```
- [ ] summary.new_projects > 0 or explain why 0
- [ ] docs/site/qc.html and discovery.html open
- [ ] Checked / Accepted KPIs match on Discovery and QC
- [ ] No writes to data/projects.csv
```

## If 0 new projects

1. Check `summary.source_stats` (PRIDE v3, PDC, literature_resolved)
2. Europe PMC 503 — retry; search still works via PRIDE+PDC
3. Do not fall back to showing PMID-only articles as "projects"

## Weekly automation (Monday, local neural net)

```powershell
powershell -File scripts/install_weekly_task.ps1
powershell -File scripts/run_weekly_discovery.ps1
```

Task Scheduler: every Monday 09:00, Ollama / Qwen on this computer.

## UI / site

| Surface | Path |
|---------|------|
| Static HTML | `docs/site/discovery.html` |
| Quality control | `docs/site/qc.html` |
| Streamlit | `discovery_app.py` → http://localhost:8501 |

## Adding to catalog (manual only)

After user review:

```powershell
python run_revisor.py add --apply
```

Never auto-modify `projects.csv`.
