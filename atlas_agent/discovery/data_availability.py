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

QUANT_NAME = re.compile(
    r"(protein|gene|abundance|quant|expression|matrix|log2|ratio|"
    r"proteome|pgx|cdap|phospho.*(site|peptide)|site.*table)",
    re.I,
)
TABLE_EXT = re.compile(r"\.(tsv|txt|csv|xlsx|mztab)$", re.I)
PDC_TABLE = re.compile(
    r"\.(peptides|summary|qcmetrics|sample|label|protein|gene|site)\.(tsv|txt)$",
    re.I,
)
RAW_EXT = re.compile(r"\.(raw|mzml|mgf|wiff|d)$", re.I)
PSM_NAME = re.compile(r"\b(psm|peptide|mzid|identification)\b", re.I)


def _classify_files(names: list[str]) -> dict[str, Any]:
    quant: list[str] = []
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
        elif PSM_NAME.search(low) and not QUANT_NAME.search(low):
            psm.append(fn)
        elif TABLE_EXT.search(low) and (QUANT_NAME.search(low) or "protein" in low or PDC_TABLE.search(low)):
            quant.append(fn)
        elif TABLE_EXT.search(low):
            other.append(fn)

    if quant:
        status = "quant_table"
        label = "table"
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
        "quant_files": quant[:8],
        "psm_files": psm[:5],
        "raw_count": len(raw),
        "n_listed": len(names),
    }


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
    # MassIVE dataset file list (public)
    try:
        r = requests.get(
            f"https://massive.ucsd.edu/ProteoSAFe/dataset_files.jsp",
            params={"task": acc},
            timeout=timeout,
        )
        if r.status_code != 200:
            return []
        # fallback: parse filenames from HTML links — lightweight
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
        out.update({"status": "unknown", "label": "no ID"})
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

    out["sample_files"] = (classified.get("quant_files") or classified.get("psm_files") or names[:5])[:5]
    out["guidance"] = data_guidance(out)
    return out


def data_guidance(da: dict[str, Any]) -> str:
    """Краткая подсказка: где protein groups / supplementary / raw."""
    status = da.get("status") or "unknown"
    quant = da.get("quant_files") or []
    if status == "quant_table" and quant:
        return f"Protein groups / quant table: {quant[0]}"
    if status == "quant_table":
        return "Количественная таблица в репозитории (protein-level)"
    if status == "local_mirror":
        loc = (da.get("local_files") or [""])[0]
        return f"Локальная копия tmt-projects: {loc or 'matrix file'}"
    if status == "processed_psm":
        return "Только PSM/peptide — ищите protein groups в Supplementary или processed data"
    if status == "raw_only":
        return "Только raw MS — см. Methods; таблицы могут быть в Supplementary"
    if status == "maybe_table":
        return "Возможная таблица — проверьте файлы вручную / Supplementary"
    if status == "no_files":
        return "В API нет файлов — проверьте Data availability / Supplementary статьи"
    return "Проверьте репозиторий и Supplementary"


def literature_data_hint(pub: dict[str, Any]) -> str:
    """Подсказка по доступности данных из абстракта / Europe PMC."""
    text = " ".join(
        str(pub.get(k) or "")
        for k in ("data_availability", "abstract", "title")
    ).lower()
    if not text.strip():
        return "Data availability не указан — см. Supplementary"
    if "supplement" in text or "supplementary" in text or "table s" in text:
        return "Данные в Supplementary (см. текст Data availability)"
    if "pride" in text or "proteomexchange" in text or "pxd" in text:
        return "Депонировано в PRIDE — номер в Data availability"
    if "pdc" in text or "proteomic data commons" in text:
        return "Депонировано в PDC"
    if "massive" in text or "msv" in text:
        return "Депонировано в MassIVE"
    if "upon request" in text or "available on request" in text:
        return "По запросу авторам — не открытый доступ"
    if "github" in text:
        return "Код/данные на GitHub (см. статью)"
    return "Открытый доступ неясен — проверьте Supplementary и репозиторий"


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
    return counts
