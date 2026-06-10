"""
TMT-каналы: аннотации из таблицы, роли (reference / control / case), матрица, нормализация.
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

import pandas as pd

from atlas_agent.analysis.result_files import first_result_file

# Не отбрасывать PSM-таблицы с TMT-каналами (в result_files perc_psm фильтруется)
MATRIX_SKIP = re.compile(
    r"\.pdf$|\.fasta$|\.xml$|\.rar$|readme\.txt$|checksum|_reference_",
    re.I,
)

# 126, 127N, 127C, 128N, 130C, 131 ...
CHANNEL_LABEL_RE = re.compile(
    r"(\d{3})\s*([NC])?\s*\(([^)]+)\)",
    re.I,
)
CHANNEL_BARE_RE = re.compile(r"(\d{3})\s*([NC])?", re.I)
TMT_COL_RE = re.compile(r"^(\d{3})(?:[_\s]*([NC]))?$", re.I)
RATIO_COL_RE = re.compile(r"^(\d{3})(?:[_\s]*([NC]))?\s*/\s*\(", re.I)
PROTEIN_ID_COLS = (
    "Protein Group Accessions",
    "Protein Groups",
    "Master Protein Accessions",
    "Gene",
    "UniProt",
    "Protein",
)


class ChannelRole(str, Enum):
    REFERENCE = "reference"
    CONTROL = "control"  # здоровый / mock / untreated
    CASE = "case"  # больной / treated / stimulus
    OTHER = "other"
    UNKNOWN = "unknown"


@dataclass
class ChannelAnnotation:
    tag: str  # e.g. 127N
    label: str  # e.g. Control 2
    role: ChannelRole
    source_field: str  # Used / Comparison / Additional
    notes: str = ""


@dataclass
class MatrixColumnInfo:
    name: str
    kind: str  # raw | ratio | meta
    tag: str | None = None
    denominator: str | None = None


_ROLE_KEYWORDS: dict[ChannelRole, tuple[str, ...]] = {
    ChannelRole.REFERENCE: (
        "ref",
        "reference",
        "pool",
        "bridge",
        "universal",
        "global ref",
        "126 ref",
    ),
    ChannelRole.CONTROL: (
        "control",
        "healthy",
        "normal",
        "mock",
        "untreated",
        "wild type",
        "wt",
        "benign",
        "adjacent normal",
    ),
    ChannelRole.CASE: (
        "cancer",
        "tumor",
        "tumour",
        "disease",
        "case",
        "treated",
        "pervanadate",
        "mitotic",
        "stim",
        "nicotine",
        "patient",
        "malignant",
        "adenocarcinoma",
    ),
}


def _classify_label(label: str, *, is_used_field: bool) -> ChannelRole:
    low = (label or "").lower()
    for role, words in _ROLE_KEYWORDS.items():
        if any(w in low for w in words):
            return role
    # TMT 10-plex: 126 часто reference, если не указано иное
    if is_used_field and re.search(r"\b126\b", label) and "control" in low:
        return ChannelRole.CONTROL
    if re.match(r"^126\b", label.strip()) and "control" not in low and "nicotine" not in low:
        return ChannelRole.REFERENCE
    return ChannelRole.UNKNOWN


def _parse_channel_field(text: str, source_field: str, *, is_used: bool) -> list[ChannelAnnotation]:
    if not text or str(text).strip().lower() in ("nan", "", "—", "-"):
        return []
    out: list[ChannelAnnotation] = []
    for part in re.split(r"[;\n]+", str(text)):
        part = part.strip()
        if not part:
            continue
        m = CHANNEL_LABEL_RE.search(part)
        if m:
            num, nc, label = m.group(1), (m.group(2) or "").upper(), m.group(3).strip()
            tag = f"{num}{nc}" if nc else num
            role = _classify_label(f"{tag} {label}", is_used_field=is_used)
            out.append(
                ChannelAnnotation(
                    tag=tag,
                    label=label,
                    role=role,
                    source_field=source_field,
                )
            )
            continue
        m2 = CHANNEL_BARE_RE.match(part)
        if m2:
            num, nc = m2.group(1), (m2.group(2) or "").upper()
            tag = f"{num}{nc}" if nc else num
            out.append(
                ChannelAnnotation(
                    tag=tag,
                    label=part,
                    role=_classify_label(part, is_used_field=is_used),
                    source_field=source_field,
                )
            )
    return out


def parse_channels_from_row(row: pd.Series) -> list[ChannelAnnotation]:
    """Все каналы из projects.csv для одной строки."""
    channels: list[ChannelAnnotation] = []
    fields = [
        ("TMT Channels Used", True),
        ("TMT Channels Comparison", False),
        ("TMT Additional Channels", False),
    ]
    for col, is_used in fields:
        if col in row.index:
            channels.extend(_parse_channel_field(str(row.get(col, "")), col, is_used=is_used))
    return channels


def channels_summary_table(channels: list[ChannelAnnotation]) -> list[dict]:
    role_ru = {
        ChannelRole.REFERENCE: "референс",
        ChannelRole.CONTROL: "контроль / здоровый",
        ChannelRole.CASE: "больной / воздействие",
        ChannelRole.OTHER: "другое",
        ChannelRole.UNKNOWN: "не ясно",
    }
    return [
        {
            "tag": c.tag,
            "label": c.label,
            "role": c.role.value,
            "role_ru": role_ru.get(c.role, c.role.value),
            "from_column": c.source_field,
        }
        for c in channels
    ]


def _score_matrix_candidate(path: Path, hint: str) -> int:
    if MATRIX_SKIP.search(path.name):
        return -1
    try:
        with open(path, encoding="latin-1", errors="replace") as f:
            head = f.readline()
    except OSError:
        return -1
    if "\t" not in head and "," not in head:
        return -1
    if not re.search(r"\b12[6-9]\b|127|128|129|130|131", head):
        return -1
    score = 10
    if hint and hint.lower() in path.name.lower():
        score += 50
    if "tmt" in path.name.lower():
        score += 20
    if "Protein" in head or "Gene" in head:
        score += 5
    score += min(int(path.stat().st_size / 1_000_000), 30)
    return score


def find_matrix_path(project_dir: Path, result_file_hint: str = "") -> Path | None:
    if not project_dir.is_dir():
        return None
    hint = (result_file_hint or "").split(".")[0]
    best: tuple[int, Path] | None = None
    for root in (project_dir / "_extracted", project_dir):
        if not root.is_dir():
            continue
        for p in root.rglob("*"):
            if not p.is_file():
                continue
            if p.suffix.lower() not in (".tsv", ".txt", ".csv", ".xlsx"):
                continue
            if p.stat().st_size > 400_000_000:
                continue
            sc = _score_matrix_candidate(p, hint)
            if sc < 0:
                continue
            if best is None or sc > best[0]:
                best = (sc, p)
    return best[1] if best else None


def _read_header(path: Path) -> tuple[list[str], str]:
    encodings = ("utf-8", "latin-1", "cp1252")
    for enc in encodings:
        try:
            with open(path, encoding=enc, errors="replace") as f:
                line = f.readline()
            sep = "\t" if "\t" in line else ","
            cols = [c.strip() for c in line.rstrip("\n").split(sep)]
            return cols, sep
        except OSError:
            continue
    return [], "\t"


def classify_matrix_columns(columns: list[str]) -> list[MatrixColumnInfo]:
    out: list[MatrixColumnInfo] = []
    for c in columns:
        c_strip = c.strip()
        m_ratio = RATIO_COL_RE.match(c_strip)
        if m_ratio or "/" in c_strip and re.search(r"\d{3}", c_strip):
            num = m_ratio.group(1) if m_ratio else re.search(r"(\d{3})", c_strip).group(1)
            nc = (m_ratio.group(2) or "") if m_ratio else ""
            tag = f"{num}{nc.upper()}" if nc else num
            out.append(MatrixColumnInfo(name=c_strip, kind="ratio", tag=tag))
            continue
        m_raw = TMT_COL_RE.match(c_strip.replace(" ", ""))
        if m_raw:
            num, nc = m_raw.group(1), (m_raw.group(2) or "").upper()
            tag = f"{num}{nc}" if nc else num
            out.append(MatrixColumnInfo(name=c_strip, kind="raw", tag=tag))
            continue
        out.append(MatrixColumnInfo(name=c_strip, kind="meta", tag=None))
    return out


def _tag_to_col_names(tag: str, columns: list[str]) -> list[str]:
    """Сопоставление 127N → колонка 127_N или 127N в файле."""
    num = re.match(r"(\d{3})", tag)
    if not num:
        return []
    n = num.group(1)
    nc = tag[3:].upper() if len(tag) > 3 else ""
    patterns = []
    if nc:
        patterns = [f"{n}_{nc}", f"{n}{nc}", f"{n} {nc}"]
    else:
        patterns = [n]
    hits = []
    for c in columns:
        cn = c.replace(" ", "").replace("-", "_")
        for p in patterns:
            if cn == p or cn.startswith(p + "/") or cn == p:
                hits.append(c)
                break
    if not hits and nc:
        for c in columns:
            if c.strip().startswith(n) and nc in c.upper():
                hits.append(c)
    return hits


def load_matrix_preview(
    path: Path,
    *,
    channel_tags: list[str] | None = None,
    max_rows: int = 4000,
    max_proteins: int = 20,
) -> dict[str, Any]:
    cols, sep = _read_header(path)
    if not cols:
        return {"error": "Не удалось прочитать заголовок"}

    classified = classify_matrix_columns(cols)
    raw_cols = [c.name for c in classified if c.kind == "raw"]
    ratio_cols = [c.name for c in classified if c.kind == "ratio"]

    usecols = []
    protein_col = None
    for c in cols:
        if c in PROTEIN_ID_COLS or "Protein" in c or "Gene" in c:
            if protein_col is None:
                protein_col = c
            usecols.append(c)
    for c in raw_cols[:16]:
        if c not in usecols:
            usecols.append(c)

    enc = "latin-1"
    usecols_list = [c for c in usecols if c in cols]
    read_kw = dict(sep=sep, nrows=max_rows, encoding=enc, low_memory=False, on_bad_lines="skip")
    try:
        df = pd.read_csv(path, usecols=usecols_list or None, **read_kw)
    except Exception:
        try:
            df = pd.read_csv(path, **read_kw)
            if usecols_list:
                df = df[[c for c in usecols_list if c in df.columns]]
        except Exception as e:
            return {
                "error": str(e),
                "path": str(path),
                "raw_channel_columns": raw_cols,
                "ratio_columns": ratio_cols,
                "header_only": True,
            }

    if protein_col and protein_col in df.columns and raw_cols:
        id_col = protein_col
        num = df[raw_cols].apply(pd.to_numeric, errors="coerce")
        agg = df.assign(_id=df[id_col].astype(str)).groupby("_id", as_index=False)[raw_cols].median()
        agg = agg.head(max_proteins)
        preview = agg.to_dict(orient="records")
    else:
        preview = df.head(max_proteins).to_dict(orient="records")

    stats = {}
    for c in raw_cols[:12]:
        s = pd.to_numeric(df[c], errors="coerce")
        if s.notna().any():
            stats[c] = {
                "min": round(float(s.min()), 3),
                "max": round(float(s.max()), 3),
                "median": round(float(s.median()), 3),
            }

    return {
        "path": str(path),
        "separator": "tab" if sep == "\t" else "comma",
        "n_columns": len(cols),
        "raw_channel_columns": raw_cols,
        "ratio_columns": ratio_cols[:12],
        "protein_id_column": protein_col,
        "column_stats": stats,
        "protein_preview": preview,
    }


def infer_normalization_from_matrix(ratio_cols: list[str], raw_cols: list[str]) -> list[str]:
    notes = []
    if ratio_cols:
        notes.append(
            f"В файле есть {len(ratio_cols)} колонок-отношений (например «126/(126+127_N+…)») — "
            "значения уже поделены на сумму/refernce channel (reporter-ion ratio)."
        )
    if raw_cols and not ratio_cols:
        notes.append(
            "Только сырые интенсивности каналов — нормализация, вероятно, в отдельном шаге или в другом файле."
        )
    if any("126" in c for c in ratio_cols) or any(c.strip() == "126" for c in raw_cols):
        notes.append("Канал 126 часто используется как reference в TMT10-plex.")
    return notes


def build_tmt_view(
    row: pd.Series,
    project_dir: str | Path | None,
    *,
    quick: bool = False,
) -> dict[str, Any]:
    """Полная карточка TMT для проекта."""
    channels = parse_channels_from_row(row)
    ch_table = channels_summary_table(channels)

    norm_sheet = str(row.get("Normalization Strategy", "") or "").strip()
    quant_fmt = str(row.get("Quantification_Format", "") or "").strip()
    z_level = str(row.get("Z-Score Level", "") or "").strip()
    z_scope = str(row.get("Z-Score Scope", "") or "").strip()

    matrix_info: dict[str, Any] = {"found": False}
    path = None
    if project_dir:
        path = find_matrix_path(
            Path(project_dir),
            first_result_file(str(row.get("Result Files", ""))),
        )
    if path:
        if quick:
            cols, sep = _read_header(path)
            classified = classify_matrix_columns(cols)
            raw_cols = [c.name for c in classified if c.kind == "raw"]
            ratio_cols = [c.name for c in classified if c.kind == "ratio"]
            matrix_info = {
                "found": True,
                "path": str(path),
                "quick": True,
                "raw_channel_columns": raw_cols,
                "ratio_columns": ratio_cols,
                "normalization_hints": infer_normalization_from_matrix(ratio_cols, raw_cols),
            }
        else:
            matrix_info = load_matrix_preview(path, channel_tags=[c.tag for c in channels])
            matrix_info["found"] = True
        matrix_info["normalization_hints"] = infer_normalization_from_matrix(
            matrix_info.get("ratio_columns") or [],
            matrix_info.get("raw_channel_columns") or [],
        )
        # связать аннотации с колонками файла
        cols_all = (matrix_info.get("raw_channel_columns") or []) + (
            matrix_info.get("ratio_columns") or []
        )
        for ch in ch_table:
            ch["matrix_columns"] = _tag_to_col_names(ch["tag"], cols_all)

    sample_design = {
        "control_healthy": str(row.get("Control Healthy", "") or ""),
        "case_untreated": str(row.get("Case Cancer Untreated", "") or ""),
        "case_treated": str(row.get("Case Cancer Treated", "") or ""),
        "patients": str(row.get("Patients / donors", "") or ""),
        "samples_used": str(row.get("Samples Used N", "") or ""),
        "experimental_design": str(row.get("Experimental Design", "") or ""),
    }

    by_role = {
        "reference": [c for c in ch_table if c["role"] == ChannelRole.REFERENCE.value],
        "control": [c for c in ch_table if c["role"] == ChannelRole.CONTROL.value],
        "case": [c for c in ch_table if c["role"] == ChannelRole.CASE.value],
        "unknown": [c for c in ch_table if c["role"] == ChannelRole.UNKNOWN.value],
    }

    return {
        "channels": ch_table,
        "channels_by_role": by_role,
        "sample_design": sample_design,
        "normalization": {
            "strategy_sheet": norm_sheet or "(не указано)",
            "quantification_format": quant_fmt or "(не указано)",
            "z_score_level": z_level,
            "z_score_scope": z_scope,
            "matrix_hints": matrix_info.get("normalization_hints") or [],
            "interpretation": _interpret_normalization(norm_sheet, quant_fmt, matrix_info),
        },
        "matrix": matrix_info,
        "matrix_path": str(path) if path else None,
    }


def _interpret_normalization(norm: str, quant: str, matrix_info: dict) -> str:
    parts = []
    if norm and norm not in ("—", "-", "Not specified", "nan"):
        parts.append(f"По таблице: {norm}.")
    if quant and quant not in ("—", "-", "Not specified", "nan", "(не указано)"):
        parts.append(f"Формат: {quant}.")
    for h in matrix_info.get("normalization_hints") or []:
        parts.append(h)
    if not parts:
        return "Укажите Normalization Strategy в CSV и/или положите матрицу в папку проекта."
    return " ".join(parts)
