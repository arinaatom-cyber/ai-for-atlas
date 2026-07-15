# Human Cancser Assosiated TMT Proteome Atlas

A local, reproducible platform for **curating a human TMT proteomics atlas** and for
**discovering new TMT proteomics projects** across public repositories. It powers
**Human Cancser Assosiated TMT Proteome Atlas** and the interactive map at
[GitHub TMT](https://github.com/arinaatom-cyber/TMT) (live: https://arinaatom-cyber.github.io/TMT/).

It contains:

- **Discovery Agent** — weekly search of PRIDE, PDC, iProX and MassIVE (+ Europe PMC
  literature) for new human TMT (>6‑channel) projects **not already in the catalogue**.
- **Revisor** — validation/audit of the catalogue against local files and source records.
- **Channel mapper** — TMT channel → patient/sample annotation.
- **Static discovery site** — `docs/site/` (new projects, QC, cohorts) for GitHub Pages.

> **Catalogue safety:** `data/projects.csv` is **read‑only** for all agents — never
> deleted, overwritten, or pushed without an explicit, manual `run_revisor.py add --apply`
> (which makes a backup first).

---

## Install (any machine)

**Windows**
```powershell
git clone https://github.com/arinaatom-cyber/ai-for-atlas.git
cd ai-for-atlas
powershell -File scripts/setup_anywhere.ps1
```

**Linux / macOS**
```bash
git clone https://github.com/arinaatom-cyber/ai-for-atlas.git
cd ai-for-atlas
bash scripts/setup_anywhere.sh
pip install -r requirements.txt
```

Copy `config.example.yaml` → `config.yaml` and adjust local paths. Optional cloud LLM keys
in `.env` (`ZAI_API_KEY` for Z.AI GLM, or `DASHSCOPE_API_KEY` / `ANTHROPIC_API_KEY`).
Discovery works without keys (falls back to GPT4All or regex). Private data repo: `GITHUB_TOKEN`.

---

## Quick start

```bash
python run_discovery.py scan      # search PRIDE + PDC + iProX + MassIVE, run QC
python run_discovery.py latest    # show the latest scan result
python run_discovery.py policy    # print the active inclusion policy
streamlit run discovery_app.py    # desktop web UI → http://localhost:8501
```

---

## Components

| Component | Command | Purpose |
|---|---|---|
| **Discovery Agent** | `python run_discovery.py scan` | Find new TMT projects (PRIDE, PDC, iProX, MassIVE) |
| **Discovery UI** | `streamlit run discovery_app.py` | Desktop web UI |
| **Revisor** | `python run_revisor.py audit` | Validate catalogue + local files |
| **Channel mapper** | `python run_channels.py build --pdc` | Map TMT channels → patients/samples |
| **TMT viewer** | `python atlas_app.py tmt-all` | Channel matrices, HTML reports |

---

## Discovery policy (inclusion criteria)

A candidate is reported only if it is:

1. **Human**;
2. **TMT / TMTpro** with **>6 channels** (10/11/12/16‑plex; 6/7/8/9/18 rejected);
3. deposited in **PRIDE / PDC / iProX / MassIVE** with a stable accession;
4. **not already** in `data/projects.csv`;
5. passing **material QC** (sample type/tissue sanity).

The pipeline:

1. Reads `data/projects.csv` (**read‑only**) as the "already known" filter.
2. Queries PRIDE v3 search, PDC `uiStudySummary`, iProX, MassIVE, and Europe PMC.
3. Optionally reads abstracts with a **local, key‑free LLM** (Ollama → GPT4All → rules)
   to flag large patient cohorts.
4. Emits **only new** accessions and writes `data/discovery_history/latest.json`.
5. Publishes `docs/site/` (new projects, QC, cohorts) — the catalogue itself is never
   published, only used locally as a de‑duplication filter.

Selection criteria, organ classification and QC for the **published atlas** are
documented in the atlas repo: see
[`METHODS.md`](https://github.com/arinaatom-cyber/TMT/blob/main/METHODS.md).

### Adding to the catalogue (manual only)

```bash
python run_revisor.py add --apply   # creates a backup, then appends reviewed rows
```

---

## Published site (GitHub Pages)

After a scan, `docs/site/` is regenerated:

| Page | Contents |
|---|---|
| `docs/site/discovery.html` | **New** PXD/PDC/MSV/IPX not in the catalogue |
| `docs/site/qc.html` | QC: candidate / manual‑check / rejected |
| `docs/site/cohorts.html` | Large literature cohorts (Europe PMC) |
| `docs/index.html` | Portal + instructions |

```bash
python scripts/publish_site.py            # rebuild docs/site/
powershell -File scripts/push_site_github.ps1   # commit & push (Windows)
```

GitHub Pages: **Settings → Pages → Build: GitHub Actions** (`.github/workflows/pages.yml`).

---

## Related repositories

| Repo | Role |
|---|---|
| **ai-for-atlas** (this) | Discovery/curation code + discovery site |
| [arinaatom-cyber/TMT](https://github.com/arinaatom-cyber/TMT) | Interactive atlas web app (live map) |
| [arinaatom-cyber/tmt-projects](https://github.com/arinaatom-cyber/tmt-projects) | Raw project data (read‑only) |

---

## Repository layout

```
atlas_agent/            # core package
  discovery/            # search sources, policy, QC, cohort literature
  sources/              # PRIDE, PDC, iProX, MassIVE, PRIDE workbook clients
  catalog/              # organ classification, project audit
  revisor/              # catalogue validation & controlled additions
  viz/                  # HTML site builders (portal, atlas, cohorts, QC)
run_discovery.py        # scan / latest / policy / history CLI
run_revisor.py          # audit / add CLI
discovery_app.py        # Streamlit UI
config.example.yaml     # template config (copy to config.yaml)
docs/                   # published static site
tests/                  # unit tests
```

---

## Tests

```bash
pip install -r requirements.txt
python -m pytest -q
```

---

## License

MIT (code). Curated metadata aggregates public records from PRIDE, CPTAC/PDC, iProX and
MassIVE; the underlying datasets remain under the licenses of their original
repositories and publications.
