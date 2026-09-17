"""Лист removed for general — исключение из Discovery."""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from atlas_agent.config import load_config
from atlas_agent.discovery.agent import _apply_removed_from_workbook, _known_accessions, load_catalog_readonly
from atlas_agent.sources.proteomics_workbook import (
    find_deleted_sheet_name,
    item_in_known_set,
    known_rejected_from_workbook,
    rejection_reasons_from_workbook,
    workbook_path_from_cfg,
)

ROOT = Path(__file__).resolve().parents[1]
XLSX = ROOT / "project of Proteomics.xlsx"


class _FakeXL:
    def __init__(self, names: list[str]):
        self.sheet_names = names


def test_find_deleted_sheet_removed_for_general():
    xl = _FakeXL(["TMT ATLAS", "removed for general", "CPTAC"])
    assert find_deleted_sheet_name(xl) == "removed for general"


def test_item_in_known_set_matches_accession_and_pmid():
    known = {"PXD001938", "30860844"}
    assert item_in_known_set({"accession": "PXD001938"}, known)
    assert item_in_known_set({"pmid": "30860844"}, known)
    assert not item_in_known_set({"accession": "PXD999999"}, known)


def test_apply_removed_moves_to_rejected_bucket():
    buckets = {
        "recommended": [
            {"accession": "PXD002622", "title": "Lung ADC pilot"},
            {"accession": "PXD999999", "title": "New study"},
        ]
    }
    cfg = {"sheet": {"proteomics_workbook": str(XLSX)}}
    if not XLSX.is_file():
        return
    moved = _apply_removed_from_workbook(buckets, cfg, root=ROOT)
    assert moved >= 1
    assert all(x.get("accession") != "PXD002622" for x in buckets["recommended"])
    rejected = buckets.get("rejected", [])
    assert any(x.get("accession") == "PXD002622" for x in rejected)
    hit = next(x for x in rejected if x.get("accession") == "PXD002622")
    assert hit.get("recommendation") == "rejected_previously_removed"
    assert hit.get("filter_reasons")


def test_known_accessions_includes_removed_ids():
    if not XLSX.is_file():
        return
    cfg = load_config()
    df = load_catalog_readonly(cfg)
    known = _known_accessions(df, cfg)
    rejected = known_rejected_from_workbook(XLSX)
    assert rejected
    assert rejected.issubset(known)
    assert "PXD002622" in known or "26539827" in known


def test_rejection_reasons_loaded_from_workbook():
    if not XLSX.is_file():
        return
    reasons = rejection_reasons_from_workbook(XLSX)
    assert reasons
    sample = reasons.get("PXD002622") or reasons.get("26539827")
    assert sample


def test_workbook_path_from_cfg():
    cfg = {"sheet": {"proteomics_workbook": "./project of Proteomics.xlsx"}}
    if not XLSX.is_file():
        return
    path = workbook_path_from_cfg(cfg, root=ROOT)
    assert path == XLSX
