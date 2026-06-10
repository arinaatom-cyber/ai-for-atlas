from __future__ import annotations

import os
import re
from pathlib import Path

import pandas as pd

SKIP_NAME = re.compile(
    r"\bpsm\b|perc_psm|mqpar|sdrf|design|checksum|\.pdf$|\.fasta$|\.xml$|\.rar$|"
    r"readme|sample.?info|reference.?file|_reference_",
    re.I,
)
UNIPROT_RE = re.compile(
    r"\b([OPQ][0-9][A-Z0-9]{3}[0-9]|[A-NR-Z][0-9](?:[A-Z][A-Z0-9]{2}[0-9]){1,2})\b",
    re.I,
)
LOG_HINT = re.compile(r"log\s*2|log2|ln\s*\(|natural\s*log", re.I)
MEDIAN_HINT = re.compile(r"median|reference\s*channel|126\s*ref", re.I)
TMT_COL = re.compile(r"126|127|128|129|130|131|tmt", re.I)


def first_result_file(cell: str) -> str:
    for line in (cell or "").split("\n"):
        x = line.strip().lstrip("•- ").strip()
        if x and len(x) < 200 and "→" not in x:
            return x
    return ""


def inspect_matrix_file(path: Path, max_rows: int = 500) -> dict:
    """Эвристики по колонкам/значениям матрицы (без полного парсинга атласа)."""
    info: dict = {"path": str(path), "format": path.suffix.lower(), "columns_sample": [], "hints": []}
    try:
        if path.suffix.lower() in (".tsv", ".txt"):
            df = pd.read_csv(path, sep="\t", nrows=max_rows, low_memory=False)
        elif path.suffix.lower() == ".csv":
            df = pd.read_csv(path, nrows=max_rows, low_memory=False)
        elif path.suffix.lower() in (".xlsx", ".xls"):
            df = pd.read_excel(path, nrows=max_rows)
        else:
            return info
    except Exception as e:
        info["error"] = str(e)
        return info

    cols = list(df.columns.astype(str))
    info["columns_sample"] = cols[:30]
    col_blob = " ".join(cols)
    if TMT_COL.search(col_blob):
        info["hints"].append("Колонки похожи на TMT-каналы (126–131)")
    if any(LOG_HINT.search(c) for c in cols):
        info["hints"].append("В названиях колонок есть log2/ln")
    numeric = df.select_dtypes(include="number")
    if not numeric.empty:
        sample = numeric.iloc[: min(200, len(numeric)), : min(20, numeric.shape[1])]
        vals = sample.to_numpy().ravel()
        vals = vals[~pd.isna(vals)]
        if len(vals):
            vmin, vmax = float(vals.min()), float(vals.max())
            if vmin >= -0.5 and vmax <= 25 and vmax > 2:
                info["hints"].append("Числа в диапазоне, похожем на log2-интенсивности")
            elif vmin >= 0 and vmax > 1000:
                info["hints"].append("Большие положительные значения — возможно сырые интенсивности")
    return info


def audit_local_files(df: pd.DataFrame, projects_root: str, limit: int = 30) -> list[dict]:
    from atlas_agent.sources.projects_table import primary_project_id

    root = Path(projects_root)
    if not root.is_dir():
        return [{"error": f"Папка не найдена: {projects_root}"}]

    rows = []
    subset = df.head(limit) if limit else df
    for _, r in subset.iterrows():
        pid = primary_project_id(str(r.get("Project ID", "")))
        rf = first_result_file(str(r.get("Result Files", "")))
        folder = root / pid
        entry = {
            "project_id": pid,
            "sheet_result_file": rf,
            "folder_exists": folder.is_dir(),
            "normalization_sheet": str(r.get("Normalization Strategy", "") or "").strip(),
        }
        if not folder.is_dir():
            rows.append(entry)
            continue
        candidates = []
        for fn in os.listdir(folder):
            if SKIP_NAME.search(fn):
                continue
            fp = folder / fn
            if fp.is_file() and fp.suffix.lower() in (".tsv", ".txt", ".csv", ".xlsx"):
                candidates.append(fp)
        ex = folder / "_extracted"
        if ex.is_dir():
            for p in ex.rglob("*"):
                if p.is_file() and p.suffix.lower() in (".tsv", ".txt", ".csv", ".xlsx"):
                    if not SKIP_NAME.search(p.name):
                        candidates.append(p)
        if rf:
            match = [p for p in candidates if rf.lower() in p.name.lower()]
            target = match[0] if match else None
        else:
            target = candidates[0] if candidates else None
        entry["local_files"] = [p.name for p in candidates[:8]]
        if target:
            entry["inspected"] = inspect_matrix_file(target)
        rows.append(entry)
    return rows
