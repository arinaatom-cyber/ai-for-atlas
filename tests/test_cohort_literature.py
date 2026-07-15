"""Tests for cohort literature text mining."""
from atlas_agent.discovery.cohort_literature import (
    assess_patients,
    build_description_ru,
    detect_omics,
    extract_patient_count,
    mine_publication,
)


def test_extract_patient_count():
    text = "We analyzed a cohort of 312 patients with colorectal cancer using TMT proteomics."
    assert extract_patient_count(text) == 312


def test_extract_n_equals():
    text = "Phosphoproteomics in n = 156 participants with breast tumors."
    assert extract_patient_count(text) == 156


def test_detect_omics_multi():
    text = "Integrative multi-omics combining proteomics and transcriptomics in patients."
    omics = detect_omics(text)
    assert "proteomics" in omics
    assert "multi_omics" in omics or "transcriptomics" in omics


def test_assess_patients_yes():
    assert assess_patients("cohort of 200 patients with proteomics", 200) == "yes"


def test_mine_publication_description():
    pub = {
        "title": "Large-scale clinical proteomics",
        "abstract": "Proteomics and genomics in 420 patients. Multi-omics integration.",
        "journal": "Nat Med",
        "year": "2025",
        "pmid": "123",
    }
    out = mine_publication(pub)
    assert out["patient_n"] == 420
    assert out["has_patients"] == "yes"
    assert "протеомика" in out["description_ru"].lower() or "Омики" in out["description_ru"]
    assert build_description_ru(out)
