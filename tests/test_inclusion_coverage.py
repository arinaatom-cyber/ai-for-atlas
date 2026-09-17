import pandas as pd

from atlas_agent.discovery.filters import (
    apply_filters,
    classify_candidate,
    default_filter_config,
    get_project_accession,
    is_confirmed_human,
    plex_allowed,
    select_new_projects,
)


def test_label_free_filtered():
    out = classify_candidate(
        {
            "title": "Label-free proteomics of human tumor tissue",
            "accession": "PXD088001",
            "source": "pride_api",
            "human": True,
            "tmt_detected": False,
            "description": "Label-free quantitative proteomics of tumor tissue from cancer patients.",
        },
        {"pmids": set(), "accessions": set()},
        cfg=default_filter_config(),
    )
    assert out["verdict"] == "filtered_out"


def test_review_without_project_id_filtered():
    out = classify_candidate(
        {
            "title": "A narrative review of tandem mass tag methods",
            "source": "europe_pmc",
            "human": True,
            "description": "This review and tutorial covers TMT 11-plex proteomics in cancer patients tumor tissue.",
        },
        {"pmids": set(), "accessions": set()},
        cfg=default_filter_config(),
    )
    assert out["verdict"] == "filtered_out"
    assert any("Review" in r for r in out["filter_reasons"])


def test_apply_filters_and_select_new_projects():
    df = pd.DataFrame([{"Project ID": "PXD000001", "PMID": "11111111", "Title": "Known"}])
    items = [
        {
            "title": "Human gastric cancer TMT 11-plex tumor tissue proteomics",
            "accession": "PXD088883",
            "source": "pride_api",
            "human": True,
            "tmt_detected": True,
            "inferred_plex": 11,
            "description": (
                "Quantitative TMT 11-plex proteomics of tumor tissue from cancer patients "
                "and adjacent normal. Protein-level quantification."
            ),
        },
        {
            "title": "Already catalogued",
            "accession": "PXD000001",
            "source": "pride_api",
            "human": True,
            "tmt_detected": True,
            "inferred_plex": 11,
            "description": "Tumor tissue from cancer patients TMT 11-plex protein groups.",
        },
    ]
    buckets = apply_filters(items, df, cfg=default_filter_config())
    assert buckets["already_in_catalog"]
    rec = buckets["recommended"]
    assert rec
    selected = select_new_projects(rec, {"PXD000001"})
    assert [x["project_accession"] for x in selected] == ["PXD088883"]
    selected_skip = select_new_projects(rec, {"PXD088883"})
    assert selected_skip == []


def test_get_project_accession_from_extracted_ids():
    assert get_project_accession({"accession": "not-an-id", "extracted_ids": {"PXD": ["PXD012345"]}}) == "PXD012345"
    assert get_project_accession({"pmid": "12345678"}) is None


def test_human_from_organisms_field():
    assert is_confirmed_human({"organisms": [{"name": "Homo sapiens"}]}, "TMT proteomics")
    assert not is_confirmed_human({"organisms": ["Mus musculus"]}, "TMT proteomics")


def test_plex_allowed_without_allow_list():
    cfg = {"min_tmt_channels": 7, "max_tmt_channels": 18, "reject_tmt_plexes": [2, 6], "allowed_tmt_plexes": []}
    assert plex_allowed(11, cfg) is True
    assert plex_allowed(6, cfg) is False
