"""Парсинг сложных аннотаций TMT из текста таблицы и файлов."""
from __future__ import annotations

import re
from typing import Any

# Patient 1 → 126 / 127N
PATIENT_LINE_RE = re.compile(
    r"patient\s*(\d+|[A-Za-z0-9_-]+)\s*[:|\t]\s*([\dNC,\s;]+)",
    re.I,
)
# set_k_1 = X126 = Normal  |  126 = Control 1
CHANNEL_EQ_RE = re.compile(
    r"(?:set_[A-Za-z0-9_]+\s*=\s*)?(?:[Xx])?(\d{3})\s*([NC])?\s*=\s*(.+?)(?:\s{2,}|\t|$)",
    re.I,
)
# 127N (Control 2) — уже в tmt_channels
# X103B  103  Normal
TRIPLE_RE = re.compile(
    r"[Xx]?(\d{3})\s*([A-Z])?\s+(\d+)\s+(.+?)(?:\s{2,}|\t|$)",
)
PATIENT_IN_LABEL_RE = re.compile(
    r"patient\s*(\d+|[A-Za-z0-9_-]+)|"
    r"donor\s*(\d+|[A-Za-z0-9_-]+)|"
    r"pt\s*(\d+)|"
    r"P(\d{2,4})\b|"
    r"GSC-(\d+)",
    re.I,
)


def normalize_tag(num: str, nc: str = "") -> str:
    nc = (nc or "").upper()
    return f"{num}{nc}" if nc else num


def extract_patient_from_label(label: str) -> str | None:
    if not label:
        return None
    m = re.search(r"patient\s*(\d+|[A-Za-z0-9_-]+)", label, re.I)
    if m:
        return f"patient_{m.group(1)}"
    m = re.search(r"donor\s*(\d+|[A-Za-z0-9_-]+)", label, re.I)
    if m:
        return f"donor_{m.group(1)}"
    m = re.search(r"\bGSC-(\d+)\b", label, re.I)
    if m:
        return f"GSC-{m.group(1)}"
    m = re.search(r"\b[Pp](\d{2,4})\b", label)
    if m:
        return f"P{m.group(1)}"
    return None


def expand_channel_range(spec: str) -> list[str]:
    """126–130C → [126, 127N, 127C, 128N, 128C, 129N, 129C, 130N, 130C] (TMT10 order)."""
    spec = spec.strip().replace("–", "-").replace("—", "-")
    m = re.match(r"(\d{3})\s*-\s*(\d{3})([NC])?", spec, re.I)
    if not m:
        return []
    start, end, end_nc = int(m.group(1)), int(m.group(2)), (m.group(3) or "").upper()
    order = [126]
    for n in range(127, 132):
        order.extend([f"{n}N", f"{n}C"])
    tags = [str(x) if isinstance(x, int) else x for x in order]
    try:
        i0 = next(i for i, t in enumerate(tags) if t.startswith(str(start)))
        i1 = next(i for i, t in enumerate(tags) if t == f"{end}{end_nc}" or t == str(end))
        return tags[i0 : i1 + 1]
    except StopIteration:
        return []


def parse_freeform_channel_text(text: str, source: str = "freeform") -> list[dict[str, Any]]:
    """Из многострочного поля TMT Channels / Description."""
    if not text or str(text).strip().lower() in ("nan", ""):
        return []
    blob = str(text).replace("\r\n", "\n")
    out: list[dict[str, Any]] = []
    seen: set[str] = set()

    # Patient N <tab> 126 <tab> 127N
    for line in blob.split("\n"):
        line = line.strip()
        if not line:
            continue
        pm = re.match(r"patient\s*(\S+)\s+([\dNC\s\t,;]+)", line, re.I)
        if pm:
            pid = f"patient_{pm.group(1)}"
            for part in re.split(r"[\s\t,;]+", pm.group(2)):
                m = re.match(r"(\d{3})([NC])?", part, re.I)
                if m:
                    tag = normalize_tag(m.group(1), m.group(2) or "")
                    if tag not in seen:
                        seen.add(tag)
                        out.append(
                            {
                                "channel_tag": tag,
                                "label": line,
                                "patient_id": pid,
                                "condition": "",
                                "source": source,
                                "confidence": 0.85,
                            }
                        )
            continue

        # 126–130C = tumor/normal  |  131 = pooled reference
        rm = re.match(r"([Xx]?[\dNC–—\-]+)\s*=\s*(.+)", line)
        if rm:
            left, cond = rm.group(1).strip(), rm.group(2).strip()
            tags = expand_channel_range(left.replace("X", ""))
            if not tags and re.match(r"\d{3}", left):
                m0 = re.match(r"(\d{3})([NC])?", left.replace("X", ""), re.I)
                if m0:
                    tags = [normalize_tag(m0.group(1), m0.group(2) or "")]
            is_ref = "pool" in cond.lower() or "ref" in cond.lower()
            role_hint = "reference" if is_ref else ""
            for tag in tags:
                if tag in seen:
                    continue
                seen.add(tag)
                out.append(
                    {
                        "channel_tag": tag,
                        "label": cond,
                        "patient_id": "reference_pool" if is_ref else (extract_patient_from_label(cond) or ""),
                        "condition": cond,
                        "role": role_hint,
                        "source": source,
                        "confidence": 0.85 if is_ref else 0.78,
                    }
                )
            if tags:
                continue

        for m in CHANNEL_EQ_RE.finditer(line):
            tag = normalize_tag(m.group(1), m.group(2) or "")
            cond = m.group(3).strip()
            if tag in seen:
                continue
            seen.add(tag)
            out.append(
                {
                    "channel_tag": tag,
                    "label": cond,
                    "patient_id": extract_patient_from_label(cond) or "",
                    "condition": cond,
                    "source": source,
                    "confidence": 0.8,
                }
            )

        for m in TRIPLE_RE.finditer(line):
            tag = normalize_tag(m.group(1), m.group(2) or "")
            cond = m.group(4).strip()
            if tag in seen:
                continue
            seen.add(tag)
            out.append(
                {
                    "channel_tag": tag,
                    "label": line,
                    "patient_id": extract_patient_from_label(cond) or f"sample_{m.group(3)}",
                    "condition": cond,
                    "source": source,
                    "confidence": 0.75,
                }
            )

    return out


def parse_excel_mapping(path) -> list[dict[str, Any]]:
    import pandas as pd

    out: list[dict[str, Any]] = []
    try:
        xl = pd.ExcelFile(path)
    except Exception:
        return out

    for sheet in xl.sheet_names[:6]:
        try:
            df = pd.read_excel(path, sheet_name=sheet, nrows=500)
        except Exception:
            continue
        if df.empty:
            continue
        cols = {str(c).lower(): c for c in df.columns}
        tmt_col = next((cols[k] for k in cols if k in ("tmt", "channel", "reporter ion", "reporter")), None)
        if not tmt_col:
            continue
        label_col = next(
            (
                cols[k]
                for k in cols
                if any(x in k for x in ("sample", "cell", "patient", "condition", "role", "notes", "identifier"))
            ),
            None,
        )
        patient_col = next((cols[k] for k in cols if "patient" in k or "donor" in k), None)

        for _, row in df.iterrows():
            raw = row.get(tmt_col)
            if pd.isna(raw):
                continue
            s = str(raw).strip()
            m = re.match(r"(\d{3})([NC])?", s.replace("X", ""), re.I)
            if not m:
                continue
            tag = normalize_tag(m.group(1), m.group(2) or "")
            label = str(row.get(label_col, "") or "") if label_col else ""
            pid = ""
            if patient_col and not pd.isna(row.get(patient_col)):
                pid = f"patient_{row.get(patient_col)}"
            elif label:
                pid = extract_patient_from_label(label) or ""
            out.append(
                {
                    "channel_tag": tag,
                    "label": label,
                    "patient_id": pid,
                    "condition": label,
                    "source": f"excel:{path.name}/{sheet}",
                    "confidence": 0.9,
                }
            )
    return out
