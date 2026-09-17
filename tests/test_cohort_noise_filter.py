"""Cohort literature — oncology-only and noise exclusions."""

from atlas_agent.discovery.cohort_literature import is_oncology_cohort
from atlas_agent.discovery.fit_rules import is_cohort_excluded


def test_diabetes_cohort_excluded():
    title = "Proteomic profiling of type 1 diabetes patients"
    assert is_cohort_excluded(title, "clinical cohort proteomics")
    assert not is_oncology_cohort(title)


def test_sepsis_cohort_excluded():
    title = "Quantitative proteomics in sepsis and septic shock"
    assert is_cohort_excluded(title, "intensive care cohort")
    assert not is_oncology_cohort(title)


def test_colorectal_cancer_cohort_kept():
    title = "Proteomics of metastatic colorectal cancer patients"
    abstract = "TMT quantitative proteomics in tumor tissue"
    assert not is_cohort_excluded(title, abstract)
    assert is_oncology_cohort(title, abstract)


def test_diabetic_kidney_excluded():
    title = "Kidney proteomics in diabetic kidney disease"
    assert is_cohort_excluded(title, "proteomics cohort")
    assert not is_oncology_cohort(title)
