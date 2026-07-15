"""Проверка доступности Result Files / количественных таблиц для кандидатов Discovery."""
from __future__ import annotations

import re
import time
from pathlib import Path
from typing import Any

import requests

from atlas_agent.analysis.result_files import SKIP_NAME, inspect_matrix_file
from atlas_agent.sources.projects_table import primary_project_id

PRIDE_FILES_API = "https://www.ebi.ac.uk/pride/ws/archive/v2/projects/{acc}/files"
PDC_GRAPHQL = "https://pdc.cancer.gov/graphql"

TABLE_EXT = re.compile(r"\.(tsv|txt|csv|xlsx|mztab)$", re.I)
RAW_EXT = re.compile(r"\.(raw|mzml|mgf|wiff|d)$", re.I)
PSM_NAME = re.compile(r"\b(psm|peptide|mzid|identification)\b", re.I)

# Protein-level tables (global proteome / protein groups)
PROTEOME_FILE = re.compile(
    r"(?<![\w-])(?:protein\.txt|protein[_ ]?groups?|"
    r"(?<![\w-])proteome(?![\w-])|global[_ ]?proteome|whole[_ ]?proteome|"
    r"gene[_ ]?abund|abundance|expression|pgx|cdap)",
    re.I,
)

# Phospho-PTM tables — must NOT share status with protein-level proteome
PHOSPHO_FILE = re.compile(
    r"phospho|p\s*site|phosphosite|phosphopeptide|kinase\s*substrate|"
    r"phosphoryl|_phos[_\.]|[_\.\-]phos[_\.\-]|\.site\.|site[_ ]?table",
    re.I,
)

QUANT_GENERIC = re.compile(
    r"(protein|gene|abundance|quant|expression|matrix|log2|ratio)",
    re.I,
)

PDC_TABLE = re.compile(
    r"\.(peptides|summary|qcmetrics|sample|label|protein|gene)\.(tsv|txt)$",
    re.I,
)


def _file_omics_kind(name: str) -> str | None:
    """Return 'proteome', 'phospho', 'generic_quant', or None for non-quant tables."""
    low = (name or "").lower()
    if not TABLE_EXT.search(low):
        return None
    # Phospho before proteome — *Phosphoproteome* also contains "proteome"
    if "phosphoproteome" in low or PHOSPHO_FILE.search(low):
        return "phospho"
    if low.endswith("protein.txt") or "proteome" in low or PROTEOME_FILE.search(low):
        return "proteome"
    if QUANT_GENERIC.search(low) or PDC_TABLE.search(low):
        return "generic_quant"
    return None


def _resolve_omics_layer(proteome: list[str], phospho: list[str], generic: list[str]) -> str:
    if proteome:
        return "mixed" if phospho else "protein"
    if phospho and not proteome and not generic:
        return "phospho_only"
    if phospho and not proteome:
        return "phospho_only"
    if generic:
        return "unknown"
    return "unknown"


def _classify_files(names: list[str]) -> dict[str, Any]:
    proteome_quant: list[str] = []
    phospho_quant: list[str] = []
    generic_quant: list[str] = []
    psm: list[str] = []
    raw: list[str] = []
    other: list[str] = []

    for name in names:
        fn = (name or "").strip()
        if not fn or SKIP_NAME.search(fn):
            continue
        low = fn.lower()
        if RAW_EXT.search(low):
            raw.append(fn)
            continue
        kind = _file_omics_kind(fn)
        if kind == "proteome":
            proteome_quant.append(fn)
        elif kind == "phospho":
            phospho_quant.append(fn)
        elif kind == "generic_quant":
            generic_quant.append(fn)
        elif TABLE_EXT.search(low):
            if PSM_NAME.search(low):
                psm.append(fn)
            else:
                other.append(fn)
        elif PSM_NAME.search(low):
            psm.append(fn)

    omics_layer = _resolve_omics_layer(proteome_quant, phospho_quant, generic_quant)
    quant_all = (proteome_quant + generic_quant + phospho_quant)[:8]

    if proteome_quant or generic_quant:
        status = "quant_table"
        label = "table"
    elif phospho_quant:
        status = "phospho_table"
        label = "phospho only"
    elif psm:
        status = "processed_psm"
        label = "PSM only"
    elif raw:
        status = "raw_only"
        label = "raw only"
    elif other:
        status = "maybe_table"
        label = "file?"
    else:
        status = "no_files"
        label = "no data"

    return {
        "status": status,
        "label": label,
        "omics_layer": omics_layer,
        "quant_files": quant_all,
        "proteome_files": proteome_quant[:8],
        "phospho_files": phospho_quant[:8],
        "psm_files": psm[:5],
        "raw_count": len(raw),
        "n_listed": len(names),
    }


def partition_phospho_only_candidates(
    candidates: list[dict[str, Any]],
    *,
    reject_phospho_only: bool = True,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Move phospho-only file listings out of the candidate bucket."""
    if not reject_phospho_only:
        return list(candidates), []
    kept: list[dict[str, Any]] = []
    moved: list[dict[str, Any]] = []
    for item in candidates:
        da = item.get("data_availability") or {}
        layer = da.get("omics_layer")
        status = da.get("status")
        if layer == "phospho_only" or status == "phospho_table":
            row = dict(item)
            row["verdict"] = "filtered_out"
            reasons = list(row.get("filter_reasons") or [])
            msg = "Phosphoproteomics only (repository files) — atlas needs protein-level proteome"
            if msg not in reasons:
                reasons.append(msg)
            row["filter_reasons"] = reasons
            moved.append(row)
        else:
            kept.append(item)
    return kept, moved


def _pride_file_names(accession: str, *, timeout: int = 45) -> list[str]:
    acc = accession.strip().upper()
    if not acc.startswith("PXD"):
        return []
    try:
        r = requests.get(PRIDE_FILES_API.format(acc=acc), timeout=timeout)
        if r.status_code != 200:
            return []
        data = r.json()
        files = data if isinstance(data, list) else data.get("_embedded", {}).get("files", [])
        return [str(f.get("fileName") or f.get("name") or "") for f in files]
    except requests.RequestException:
        return []


def _pdc_file_names(accession: str, *, timeout: int = 45) -> list[str]:
    acc = accession.strip().upper()
    if not acc.startswith("PDC"):
        return []
    names: list[str] = []
    offset = 0
    page = 500
    while True:
        q = (
            "{ filesPerStudy(pdc_study_id: \""
            + acc
            + "\", offset: "
            + str(offset)
            + ", limit: "
            + str(page)
            + ") { file_name data_category file_type file_format } }"
        )
        try:
            r = requests.post(PDC_GRAPHQL, json={"query": q}, timeout=timeout)
            if r.status_code != 200:
                break
            body = r.json()
            if body.get("errors"):
                break
            rows = body.get("data", {}).get("filesPerStudy") or []
            if not rows:
                break
            batch = [str(x.get("file_name") or "") for x in rows if x.get("file_name")]
            if not batch:
                break
            names.extend(batch)
            if len(rows) < page:
                break
            offset += page
        except requests.RequestException:
            break
    return names


def _massive_file_names(accession: str, *, timeout: int = 45) -> list[str]:
    acc = accession.strip().upper()
    if not acc.startswith("MSV"):
        return []
    try:
        r = requests.get(
            "https://massive.ucsd.edu/ProteoSAFe/dataset_files.jsp",
            params={"task": acc},
            timeout=timeout,
        )
        if r.status_code != 200:
            return []
        names = re.findall(r'filename=([^&"\'>\s]+)', r.text)
        return [n.replace("%20", " ") for n in names[:200]]
    except requests.RequestException:
        return []


def _local_mirror(accession: str, tmt_root: str | Path | None) -> dict[str, Any]:
    if not tmt_root:
        return {"local_mirror": False}
    root = Path(tmt_root)
    pid = primary_project_id(accession)
    folder = root / pid
    if not folder.is_dir():
        return {"local_mirror": False, "local_path": None}
    candidates = []
    for fp in folder.rglob("*"):
        if not fp.is_file():
            continue
        if fp.suffix.lower() not in (".tsv", ".txt", ".csv", ".xlsx"):
            continue
        if SKIP_NAME.search(fp.name):
            continue
        candidates.append(fp)
    inspected = None
    if candidates:
        inspected = inspect_matrix_file(candidates[0])
    return {
        "local_mirror": True,
        "local_path": str(folder),
        "local_files": [p.name for p in candidates[:8]],
        "local_inspected": inspected,
    }


def check_item_data_availability(
    item: dict[str, Any],
    *,
    tmt_root: str | Path | None = None,
    fetch_remote: bool = True,
) -> dict[str, Any]:
    """Вернуть блок data_availability для одного кандидата."""
    acc = primary_project_id(str(item.get("project_accession") or item.get("accession") or ""))
    out: dict[str, Any] = {"accession": acc, "source_checked": None}

    if not acc:
        out.update({"status": "unknown", "label": "no ID", "omics_layer": "unknown"})
        return out

    local = _local_mirror(acc, tmt_root)
    out.update(local)

    names: list[str] = []
    if fetch_remote:
        if acc.startswith("PXD"):
            names = _pride_file_names(acc)
            out["source_checked"] = "PRIDE"
        elif acc.startswith("PDC"):
            names = _pdc_file_names(acc)
            out["source_checked"] = "PDC"
        elif acc.startswith("MSV"):
            names = _massive_file_names(acc)
            out["source_checked"] = "MassIVE"
        else:
            out["source_checked"] = "none"

    classified = _classify_files(names)
    out.update(classified)

    if local.get("local_mirror") and local.get("local_files"):
        out["status"] = "local_mirror"
        out["label"] = "local"

    preferred = (
        classified.get("proteome_files")
        or classified.get("quant_files")
        or classified.get("psm_files")
        or names[:5]
    )
    out["sample_files"] = preferred[:5]
    out["guidance"] = data_guidance(out)
    return out


def data_guidance(da: dict[str, Any]) -> str:
    """Short hint: where to find protein groups / supplementary / raw files."""
    status = da.get("status") or "unknown"
    layer = da.get("omics_layer") or "unknown"
    proteome = da.get("proteome_files") or []
    phospho = da.get("phospho_files") or []
    quant = da.get("quant_files") or []

    if status == "phospho_table" or layer == "phospho_only":
        top = phospho[0] if phospho else (quant[0] if quant else "")
        return f"Phosphoproteomics table only (not global proteome){': ' + top if top else ''}"
    if status == "quant_table" and proteome:
        return f"Protein-level table: {proteome[0]}"
    if status == "quant_table" and quant:
        return f"Quant table: {quant[0]}"
    if status == "quant_table":
        return "Quant table in repository (protein-level)"
    if status == "local_mirror":
        loc = (da.get("local_files") or [""])[0]
        return f"Local copy in tmt-projects: {loc or 'matrix file'}"
    if status == "processed_psm":
        return "PSM/peptide only — look for protein groups in Supplementary or processed data"
    if status == "raw_only":
        return "Raw MS only — check Methods; tables may be in Supplementary"
    if status == "maybe_table":
        return "Possible table — verify files manually / Supplementary"
    if status == "no_files":
        return "No files in API — check Data availability / paper Supplementary"
    return "Check repository and Supplementary"


def literature_data_hint(pub: dict[str, Any]) -> str:
    """Data availability hint from abstract / Europe PMC."""
    text = " ".join(
        str(pub.get(k) or "")
        for k in ("data_availability", "abstract", "title")
    ).lower()
    if not text.strip():
        return "Data availability not stated — see Supplementary"
    if "supplement" in text or "supplementary" in text or "table s" in text:
        return "Data in Supplementary (see Data availability text)"
    if "pride" in text or "proteomexchange" in text or "pxd" in text:
        return "Deposited in PRIDE — accession in Data availability"
    if "pdc" in text or "proteomic data commons" in text:
        return "Deposited in PDC"
    if "massive" in text or "msv" in text:
        return "Deposited in MassIVE"
    if "upon request" in text or "available on request" in text:
        return "Available on request — not open access"
    if "github" in text:
        return "Code/data on GitHub (see paper)"
    return "Open access unclear — check Supplementary and repository"


def annotate_data_availability(
    items: list[dict[str, Any]],
    *,
    tmt_root: str | Path | None = None,
    fetch_remote: bool = True,
    delay_s: float = 0.15,
) -> list[dict[str, Any]]:
    """Добавить data_availability к каждому элементу (in-place + return)."""
    for i, item in enumerate(items):
        item["data_availability"] = check_item_data_availability(
            item, tmt_root=tmt_root, fetch_remote=fetch_remote
        )
        if fetch_remote and delay_s and i < len(items) - 1:
            time.sleep(delay_s)
    return items


def summarize_availability(items: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in items:
        da = item.get("data_availability") or {}
        st = da.get("status") or "unknown"
        counts[st] = counts.get(st, 0) + 1
        layer = da.get("omics_layer")
        if layer:
            key = f"omics_{layer}"
            counts[key] = counts.get(key, 0) + 1
    return counts
