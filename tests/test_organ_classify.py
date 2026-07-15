"""Tests for catalog organ classification (mirrors app.js)."""
from __future__ import annotations

from atlas_agent.catalog.organ_classify import classify_all_organs, map_project


def test_multiple_organs_22_types():
    row = {
        "Project ID": "MSV000085836",
        "Organ": "Multiple organs (22 types)",
        "Sample Type": "Cell Lines",
        "Tumor Type": "Cancer",
        "Title": "CLLE",
    }
    m = map_project(row)
    assert m["organs"] == ["Multiple_Organs"]


def test_multiple_organs_plain():
    row = {
        "Project ID": "PXD006895",
        "Organ": "Multiple organs",
        "Sample Type": "Cell Lines",
        "Tumor Type": "Cancer",
        "Title": "SubCellBarCode",
    }
    m = map_project(row)
    assert m["organs"] == ["Multiple_Organs"]


def test_lung_metastasis_trim():
    row = {
        "Project ID": "PXD012845",
        "Organ": "Lung; liver; kidney",
        "Sample Type": "Tissue",
        "Tumor Type": "Metastatic lung adenocarcinoma",
        "Title": "Autopsy LUAD",
    }
    m = map_project(row)
    assert "Lung" in m["organs"]
    assert "Liver" not in m["organs"]


def test_gtex_normal_tissue():
    organs = classify_all_organs(
        "Adrenal Gland; Liver; Lung; Brain Cortex; Colon Sigmoid"
    )
    assert "Liver" in organs
    assert "Lung" in organs
    assert "Adrenal_Gland" in organs
