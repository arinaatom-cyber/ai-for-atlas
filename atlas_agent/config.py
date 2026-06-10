from __future__ import annotations

import os
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def load_config(path: str | Path | None = None) -> dict:
    cfg_path = Path(path) if path else ROOT / "config.yaml"
    if not cfg_path.is_file():
        cfg_path = ROOT / "config.example.yaml"
    with open(cfg_path, encoding="utf-8") as f:
        cfg = yaml.safe_load(f) or {}

    def resolve(p: str | None) -> str | None:
        if not p:
            return None
        pp = Path(p)
        if not pp.is_absolute():
            pp = (ROOT / pp).resolve()
        return str(pp)

    sheet = cfg.get("sheet") or {}
    paths = cfg.get("paths") or {}
    for key in ("projects_csv",):
        if sheet.get(key):
            sheet[key] = resolve(sheet[key])
    for key in ("tmt_projects_dir", "atlas_data_dir", "reports_dir"):
        if paths.get(key):
            paths[key] = resolve(paths[key])
    cfg["sheet"] = sheet
    cfg["paths"] = paths
    return cfg
