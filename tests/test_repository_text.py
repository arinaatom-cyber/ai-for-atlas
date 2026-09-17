"""PubMed / PRIDE / PDC excerpts for Abstract/Fit and material rescue."""

from atlas_agent.discovery.filters import classify_candidate, default_filter_config
from atlas_agent.discovery.repository_text import (
    attach_local_excerpt,
    attach_pubmed_abstract,
    enrich_items_for_display,
    rescue_unspecified_material,
)
from atlas_agent.viz.discovery_table_shared import _abstract_cell


def test_pride_description_becomes_excerpt_without_pubmed():
    item = {
        "accession": "PXD099001",
        "source": "pride_api",
        "description": "Quantitative TMT proteomics of tumor tissue from patients with lung cancer.",
        "sample_processing_protocol": "Proteins extracted from FFPE sections, TMT 10-plex labeling.",
    }
    attach_local_excerpt(item)
    assert "tumor tissue" in item["abstract_snippet"].lower()
    assert item["excerpt_source"] == "pride"
    html = _abstract_cell(item)
    assert "tumor tissue" in html.lower()
    assert "fit_llm" not in html
    assert "excerpt_src_" not in html


def test_pdc_excerpt_from_disease_and_site():
    item = {
        "accession": "PDC000999",
        "source": "pdc_api",
        "consortium": "PDC",
        "disease": "Lung adenocarcinoma",
        "primary_site": "Lung",
        "experiment_type": "TMT10",
        "description": "Lung adenocarcinoma · Proteome",
    }
    attach_local_excerpt(item)
    assert item["excerpt_source"] == "pdc"
    html = _abstract_cell(item)
    assert "Lung adenocarcinoma" in html
    assert "excerpt_src_" not in html


def test_pubmed_abstract_overrides_pride_card():
    item = {
        "accession": "PXD099002",
        "source": "pride_api",
        "pmid": "38765432",
        "description": "Short PRIDE blurb without tissue words.",
    }

    def fake_fetch(pmid: str) -> dict:
        return {
            "pmid": pmid,
            "found": True,
            "abstract": "We profiled tumor tissue from 40 cancer patients using TMT 11-plex proteomics.",
        }

    assert attach_pubmed_abstract(item, fetch_fn=fake_fetch, delay_s=0)
    assert item["excerpt_source"] == "pubmed"
    assert "tumor tissue" in item["abstract"]
    html = _abstract_cell(item)
    assert "tumor tissue" in html.lower()
    assert "excerpt_src_" not in html


def test_abstract_cell_is_summary_without_llm_badge():
    html = _abstract_cell(
        {
            "abstract_snippet": "Human TMT proteome of tumor tissue.",
            "atlas_fit": "yes",
            "excerpt_source": "pubmed",
        }
    )
    assert "tumor tissue" in html.lower()
    assert "fit_llm" not in html
    assert "LLM" not in html


def test_rescue_reads_pubmed_when_pride_material_missing():
    rejected = {
        "title": "Human cancer TMT 10-plex proteomics",
        "accession": "PXD088883",
        "source": "pride_api",
        "human": True,
        "tmt_detected": True,
        "inferred_plex": 10,
        "pmid": "39900001",
        "description": "Quantitative proteomics of patients",
        "verdict": "rejected",
        "qc_status": "rejected",
        "filter_reasons": ["Material not specified — no tissue/cell line in metadata or article"],
        "qc_reasons": ["Material not specified — no tissue/cell line in metadata or article"],
    }

    def fake_fetch(pmid: str) -> dict:
        return {
            "pmid": pmid,
            "found": True,
            "abstract": (
                "Quantitative TMT 10-plex proteomics of tumor tissue from cancer patients "
                "compared with healthy controls."
            ),
        }

    attach_pubmed_abstract(rejected, fetch_fn=fake_fetch, delay_s=0)
    buckets = {"rejected": [rejected], "recommended": []}
    stats = rescue_unspecified_material(
        buckets,
        {"pmids": set(), "accessions": set()},
        cfg=default_filter_config(),
        fetch_pubmed=False,
    )
    assert stats["rescued"] == 1
    assert buckets["rejected"] == []
    out = buckets["recommended"][0]
    assert out["verdict"] == "recommended"
    assert out.get("qc_status") == "candidate"


def test_enrich_display_uses_injected_pubmed():
    item = {
        "accession": "PXD099003",
        "source": "pride_api",
        "pmid": "31234567",
        "title": "Human TMT study",
        "description": "PRIDE project description without material words.",
    }

    def fake_fetch(pmid: str) -> dict:
        return {"pmid": pmid, "found": True, "abstract": "FFPE tumor tissue proteome of patients, TMT 16-plex."}

    attach_pubmed_abstract(item, fetch_fn=fake_fetch, delay_s=0)
    n = enrich_items_for_display([item], fetch_pubmed=False, use_llm=False)
    assert n == 1
    assert (item.get("abstract_ai") or {}).get("material") in (
        "tumor tissue",
        "human tissue",
        "cancer cell line",
    )
    assert item.get("atlas_fit") in ("yes", "maybe")


def test_fetch_abstract_requests_europe_pmc_core():
    from unittest.mock import patch

    from atlas_agent.sources.literature import fetch_abstract

    payload = {
        "resultList": {
            "result": [
                {
                    "title": "Human TMT tumor tissue proteome",
                    "abstractText": "Tumor tissue from patients was labeled with TMT 10-plex.",
                    "pubYear": "2025",
                    "journalTitle": "Mol Cell Proteomics",
                }
            ]
        }
    }

    class _Resp:
        status_code = 200

        def raise_for_status(self):
            return None

        def json(self):
            return payload

    with patch("atlas_agent.sources.literature.requests.get", return_value=_Resp()) as mocked:
        meta = fetch_abstract("38765432")
    assert meta["abstract"].startswith("Tumor tissue")
    kwargs = mocked.call_args.kwargs
    assert kwargs["params"]["resultType"] == "core"
    assert "EXT_ID:38765432" in kwargs["params"]["query"]
