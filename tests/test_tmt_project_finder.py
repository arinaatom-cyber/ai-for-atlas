"""Unit tests for tmt_project_finder classification (no network)."""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

FINDER = Path(__file__).resolve().parents[1] / "tmt_project_finder"
if str(FINDER) not in sys.path:
    sys.path.insert(0, str(FINDER))

from src.classify_projects import classify_project
from src.extract_metadata import extract_organism, extract_tmt
from src.utils import load_dictionaries, resolve_path


def test_resolve_path_relative_to_finder_root():
    p = resolve_path("outputs/report.md")
    assert p.is_absolute()
    assert p.name == "report.md"
    assert "tmt_project_finder" in str(p)


def test_extract_tmt_allows_tmt7_tmt9_tmt12_and_tmt18():
    tmt7 = extract_tmt({"title": "Human gastric cancer TMT7 proteomics", "description": ""})
    assert tmt7["status"] == "confirmed"
    assert any("7" in x for x in tmt7["allowed_hits"])

    tmt9 = extract_tmt({"title": "Clinical TMT9 cohort", "description": "patients"})
    assert tmt9["status"] == "confirmed"
    assert any("9" in x for x in tmt9["allowed_hits"])

    tmt12 = extract_tmt({"title": "Human gastric cancer TMT12 proteomics", "description": ""})
    assert tmt12["status"] == "confirmed"
    assert any("12" in x for x in tmt12["allowed_hits"])

    tmt18 = extract_tmt({"title": "TMTpro18 clinical cohort", "description": "patients"})
    assert tmt18["status"] == "confirmed"
    assert any("18" in x for x in tmt18["allowed_hits"])


def test_extract_organism_rejects_mixed_human_mouse():
    org = extract_organism(
        {
            "title": "Human and mouse TMT study",
            "description": "Homo sapiens patients and Mus musculus xenograft.",
        }
    )
    assert org["status"] == "rejected"
    tmt = extract_tmt({"title": "TMT6 yeast study", "description": "label-free comparison"})
    assert tmt["status"] == "rejected"


def test_classify_high_priority_human_tmt10_tissue():
    rec = classify_project(
        {
            "project_id": "PXD999999",
            "title": "Human colorectal cancer TMT10 tumor tissue proteomics",
            "description": "Homo sapiens patients with tumor tissue.",
            "organism": "Homo sapiens",
            "method": "TMT10",
            "sample_type": "tumor tissue",
        },
        database=pd.DataFrame(),
        deleted_database=pd.DataFrame(),
    )
    assert rec["classification"] == "high_priority_check"


def test_classify_duplicate_on_project_id():
    db = pd.DataFrame([{"Project ID": "PXD000001", "PMID": "", "DOI": "", "Title": "Known", "URL": ""}])
    rec = classify_project(
        {
            "project_id": "PXD000001",
            "title": "Anything",
            "description": "Already catalogued project.",
        },
        database=db,
        deleted_database=pd.DataFrame(),
    )
    assert rec["classification"] == "duplicate"


def test_classify_previously_removed():
    deleted = pd.DataFrame(
        [{"Project ID": "PXD000002", "PMID": "", "DOI": "", "Title": "Removed", "URL": ""}]
    )
    rec = classify_project(
        {
            "project_id": "PXD000002",
            "title": "Old candidate",
            "description": "Previously removed from general.",
        },
        database=pd.DataFrame(),
        deleted_database=deleted,
    )
    assert rec["classification"] == "rejected_previously_removed"


def test_dictionaries_allow_tmt18():
    d = load_dictionaries()
    assert "TMT18" in (d.get("allowed_tmt") or [])
    assert "TMT18" not in (d.get("rejected_tmt") or [])
    assert "TMT12" in (d.get("allowed_tmt") or [])
    assert "TMT7" in (d.get("allowed_tmt") or [])
    assert "TMT7" not in (d.get("rejected_tmt") or [])
    assert "TMT6" in (d.get("rejected_tmt") or [])
