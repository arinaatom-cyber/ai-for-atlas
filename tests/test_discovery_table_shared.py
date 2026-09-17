"""Tests for discovery table Analysis column rendering."""
from __future__ import annotations

from atlas_agent.discovery.evaluation.schemas import ItemKind
from atlas_agent.viz.discovery_qc_html import _rows
from atlas_agent.viz.discovery_table_shared import (
    _coerce_evaluation,
    _id_cell,
    _project_links,
    _render_analysis_cell,
    _similar_cell,
    _source_link_cell,
    _title_cell,
    source_label,
)


def test_render_analysis_legacy_when_evidence_chain_missing():
    item = {
        "evaluation": {
            "final_verdict": "Watch",
            "confidence": "C",
            "confidence_css": "tier-c",
            "confidence_bullets": ["old scan"],
        },
        "title": "Legacy paper",
    }
    html = _render_analysis_cell(item, kind=ItemKind.LITERATURE, pubs_by_pmid={})
    assert 'data-i18n="legacy_rescan"' in html
    assert "cell-analysis" in html


def test_render_analysis_uses_formatter_for_typed_evaluation():
    item = {
        "evaluation": {
            "final_verdict": "Watch",
            "confidence": "C",
            "confidence_css": "tier-c",
            "confidence_bullets": ["LLM maybe — literature watch"],
            "evidence_chain": [
                {
                    "source": "llm_low",
                    "score": 0.2,
                    "is_actionable": False,
                    "detail": "below threshold",
                }
            ],
            "display_fit_label": "LLM maybe",
        },
        "abstract_ai": {"summary_en": "Human TMT cohort study."},
    }
    html = _render_analysis_cell(item, kind=ItemKind.LITERATURE, pubs_by_pmid={})
    assert "cell-analysis" in html
    assert "Human TMT cohort study" in html
    assert "LLM maybe — literature watch" in html
    assert "Legacy format" not in html


def test_coerce_evaluation_rejects_string_payload():
    assert _coerce_evaluation({"evaluation": "old string"}, kind=ItemKind.PROJECT) is None


def test_source_label_massive_iprox():
    assert source_label({"accession": "MSV000080000"}) == "MassIVE"
    assert source_label({"accession": "IPX0001234000"}) == "iProX"
    assert source_label({"accession": "PXD012345"}) == "PRIDE"


def test_id_cell_repo_link_without_pmid_duplicate():
    html = _id_cell(
        acc="PXD012345",
        repo="https://www.ebi.ac.uk/pride/archive/projects/PXD012345",
        pmid="38765432",
    )
    assert "PXD012345" in html
    assert "PMID" not in html
    assert "pride/archive/projects/PXD012345" in html
    assert ">PRIDE</" in html
    assert 'class="cell-mono id-acc"' in html
    assert 'class="cell-mono id-acc"><b>PXD012345</b></a>' not in html


def test_id_cell_pdc_blue_repo_link_once():
    html = _id_cell(
        acc="PDC000604",
        repo="https://proteomic.datacommons.cancer.gov/pdc/study/PDC000604",
        pmid="",
    )
    assert html.count(">PDC</") == 1
    assert "PDC000604" in html
    assert "pdc/study/PDC000604" in html


def test_title_cell_repo_over_pubmed_for_project():
    html = _title_cell(
        "Human TMT colon proteome",
        "https://pubmed.ncbi.nlm.nih.gov/38765432/",
        "https://www.ebi.ac.uk/pride/archive/projects/PXD012345",
        description="Paired tumor and adjacent colon tissue.",
        acc="PXD012345",
    )
    assert "cell-desc" in html
    assert "Paired tumor and adjacent colon tissue." in html
    assert "Human TMT colon proteome" in html
    assert "pride/archive/projects/PXD012345" in html
    assert "pubmed.ncbi.nlm.nih.gov" not in html


def test_title_cell_pubmed_link_for_paper():
    html = _title_cell(
        "Human TMT colon proteome",
        "https://pubmed.ncbi.nlm.nih.gov/38765432/",
        "",
        description="Paired tumor and adjacent colon tissue.",
    )
    assert "pubmed.ncbi.nlm.nih.gov/38765432" in html


def test_title_cell_repo_link_for_project():
    html = _title_cell(
        "CPTAC pediatric AML",
        "",
        "https://proteomic.datacommons.cancer.gov/pdc/study/PDC000604",
        acc="PDC000604",
    )
    assert "CPTAC pediatric AML" in html
    assert "pdc/study/PDC000604" in html
    assert 'class="cell-title"' in html
    assert "PMID" not in html


def test_source_link_cell_skips_repo_duplicate():
    html = _source_link_cell({"accession": "PDC000604"}, acc="PDC000604")
    assert "PDC" not in html
    assert "cell-empty" in html


def test_project_links_skips_repo_when_in_id_column():
    html = _project_links(
        "MSV000080000",
        "https://massive.ucsd.edu/ProteoSAFe/dataset.jsp?accession=MSV000080000",
        "38765432",
    )
    assert "MassIVE" not in html
    assert "accession=MSV000080000" not in html
    assert "PMID 38765432" in html
    assert 'data-i18n="link_epmc"' in html


def test_similar_cell_dedupes_catalog_hits():
    html = _similar_cell(
        {
            "similar_in_catalog": [
                {"project_id": "PXD031107", "score": 0.19},
                {"project_id": "PXD031107", "score": 0.19},
            ]
        }
    )
    assert html.count('class="link-row"') == 1


def test_similar_cell_shows_catalog_match():
    html = _similar_cell(
        {"similar_in_catalog": [{"project_id": "PXD012173", "score": 0.82}]}
    )
    assert "PXD012173" in html
    assert "82%" in html
    assert "pride" in html.lower()


def test_qc_rows_include_pmid_description_repo():
    html = _rows(
        [
            {
                "accession": "PXD012345",
                "title": "Human TMT colon proteome",
                "pmid": "38765432",
                "description": "Paired tumor and adjacent colon tissue.",
                "repository_url": "https://www.ebi.ac.uk/pride/archive/projects/PXD012345",
                "tmt_label": "TMT11",
            }
        ]
    )
    assert "cell-desc" in html
    assert "Paired tumor and adjacent colon tissue." in html
    assert "pride/archive/projects/PXD012345" in html
    assert "Human TMT colon proteome" in html
