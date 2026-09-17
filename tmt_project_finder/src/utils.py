"""Shared helpers: config, dictionaries, text blob."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parent.parent


def resolve_path(path: str | Path, *, base: Path | None = None) -> Path:
    p = Path(path)
    if not p.is_absolute():
        p = (base or ROOT) / p
    return p


def load_config(path: Path | None = None) -> dict[str, Any]:
    p = path or ROOT / "config.yaml"
    with open(p, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def load_dictionaries(path: Path | None = None) -> dict[str, Any]:
    p = path or ROOT / "dictionaries.yaml"
    with open(p, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def record_blob(record: dict[str, Any]) -> str:
    parts = [
        record.get("title"),
        record.get("description"),
        record.get("organism"),
        record.get("method"),
        record.get("sample_type"),
        record.get("publication"),
        record.get("evidence_text"),
        record.get("keywords"),
    ]
    return " ".join(str(p or "") for p in parts).lower()


def ensure_manual_fields(record: dict[str, Any]) -> dict[str, Any]:
    out = dict(record)
    for col in ("Quantification_Format", "TMT_Channels", "Result_Files"):
        if not out.get(col):
            out[col] = "manual review required"
    return out
