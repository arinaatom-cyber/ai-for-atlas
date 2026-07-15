from atlas_agent.discovery.fit_rules import (
    apply_literature_exclusions,
    is_cohort_excluded,
    is_non_study_literature,
    sanitize_summary,
)


def test_sanitize_summary_drops_json_schema_artifact():
    assert sanitize_summary("This JSON schema describes human proteomics") == ""
    assert sanitize_summary("Human TMT cohort in gastric cancer") == "Human TMT cohort in gastric cancer"


def test_non_study_literature_review():
    assert is_non_study_literature("A narrative review of proteomics in cancer")
    assert not is_non_study_literature("Proteomic profiling of 120 patients with CRC")


def test_cohort_excludes_software():
    assert is_cohort_excluded("MultiOmicsXplorer: an integrator platform for multi-omics")


def test_apply_literature_exclusions_mouse():
    item = {
        "title": "Murine tumor proteomics with TMT11",
        "abstract": "We studied mice xenograft models.",
        "abstract_ai": {"atlas_fit": "yes", "atlas_fit_score": 0.7, "summary_en": "JSON schema test"},
    }
    out = apply_literature_exclusions(item)
    assert out["atlas_fit"] == "no"
    assert out["atlas_fit_score"] is None
    assert out["abstract_ai"]["summary_en"] == ""
