import pandas as pd

from atlas_agent.discovery.filters import classify_candidate, default_filter_config
from atlas_agent.revisor.similarity import (
    CLOSE_MATCH_THRESHOLD,
    annotate_candidates,
    jaccard,
)
from atlas_agent.sources.literature import publication_status_from_epmc
from atlas_agent.viz.discovery_table_shared import _type_cell, item_is_preprint


def _passing_item(**extra):
    item = {
        "title": "Human gastric cancer TMT 11-plex tumor tissue proteomics",
        "accession": "MSV000099999",
        "source": "massive",
        "human": True,
        "tmt_detected": True,
        "inferred_plex": 11,
        "description": (
            "Quantitative TMT 11-plex proteomics of tumor tissue from cancer patients "
            "and adjacent normal. Protein-level quantification."
        ),
    }
    item.update(extra)
    return item


def test_theme_overlap_below_close_match_is_not_has_close_match():
    df = pd.DataFrame(
        [{"Project ID": "PXD000001", "Title": "Colon cancer TMT proteomics patients tissue", "Organ": "Colon"}]
    )
    cand = [{"accession": "PXD999999", "title": "Lung cancer TMT proteomics patients tissue"}]
    out = annotate_candidates(cand, df)
    assert out[0]["similar_in_catalog"]
    assert float(out[0]["similar_in_catalog"][0]["score"]) < CLOSE_MATCH_THRESHOLD
    assert out[0]["has_close_match"] is False


def test_near_identical_title_is_close_match():
    df = pd.DataFrame(
        [
            {
                "Project ID": "PXD031107",
                "Title": "Pediatric AML proteogenomics TMT11 blood",
                "Organ": "Blood",
            }
        ]
    )
    cand = [{"accession": "MSV000088888", "title": "Pediatric AML proteogenomics TMT11 blood cohort"}]
    out = annotate_candidates(cand, df)
    assert out[0]["has_close_match"] is True
    assert out[0]["similar_in_catalog"][0]["project_id"] == "PXD031107"


def test_close_match_goes_to_manual_check_not_auto_exclude():
    out = classify_candidate(
        _passing_item(
            has_close_match=True,
            similar_in_catalog=[{"project_id": "PXD031107", "score": 0.85}],
        ),
        {"pmids": set(), "accessions": set()},
        cfg=default_filter_config(),
    )
    assert out["verdict"] == "requires_manual_check"
    assert any("similar_catalog_review" in r for r in out["filter_reasons"])


def test_without_close_match_stays_recommended():
    out = classify_candidate(
        _passing_item(has_close_match=False),
        {"pmids": set(), "accessions": set()},
        cfg=default_filter_config(),
    )
    assert out["verdict"] == "recommended"


def test_epmc_ppr_is_preprint():
    status = publication_status_from_epmc({"source": "PPR", "pubType": "preprint", "journalTitle": "bioRxiv"})
    assert status["is_preprint"] is True
    assert status["publication_status"] == "preprint"


def test_epmc_medline_is_journal():
    status = publication_status_from_epmc(
        {"source": "MED", "pubType": "research-article", "journalTitle": "Nature"}
    )
    assert status["is_preprint"] is False
    assert status["publication_status"] == "journal"


def test_biorxiv_journal_is_preprint():
    status = publication_status_from_epmc({"source": "PPR", "doi": "10.1101/2024.01.01.123456", "journalTitle": "bioRxiv"})
    assert status["is_preprint"] is True
    assert status["publication_status"] == "preprint"


def test_preprint_badge_in_type_cell():
    html = _type_cell("paper", {"is_preprint": True, "publication_status": "preprint"})
    assert "badge_preprint" in html
    assert item_is_preprint({"is_preprint": True})
    assert not item_is_preprint({"publication_status": "journal"})


def test_jaccard_close_threshold_constant():
    assert CLOSE_MATCH_THRESHOLD == 0.72
    assert jaccard({"a", "b", "c"}, {"a", "b", "c"}) == 1.0
