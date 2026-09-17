from atlas_agent.discovery.filters import classify_candidate, default_filter_config
from atlas_agent.discovery.id_extract import extract_ids_from_text, extract_loose_pmids


def test_date_is_not_strict_pmid():
    blob = "Dataset submitted 20260917 without PubMed identifier"
    assert "PMID" not in extract_ids_from_text(blob)
    assert "20260917" in extract_loose_pmids(blob)


def test_pmid_prefix_is_strict():
    blob = "See PMID: 38765432 and PubMed 12345678"
    ids = extract_ids_from_text(blob)
    assert ids["PMID"] == ["12345678", "38765432"]


def test_loose_pmid_does_not_auto_exclude():
    catalog = {"pmids": {"20260917"}, "accessions": set()}
    item = {
        "accession": "PXD900317",
        "title": "Human colorectal tumor tissue TMT 11-plex proteomics submitted 20260917",
        "description": "Homo sapiens patients, tumor tissue, protein groups, TMT labeling.",
        "human": True,
        "inferred_plex": 11,
        "tmt_detected": True,
        "source": "pride_search_v3",
    }
    out = classify_candidate(item, catalog, cfg=default_filter_config())
    assert out["verdict"] != "already_in_catalog"
    assert "20260917" in (out.get("possible_pmid_match") or [])
    assert out["verdict"] == "requires_manual_check"


def test_strict_pmid_still_already_in_catalog():
    catalog = {"pmids": {"38765432"}, "accessions": set()}
    item = {
        "accession": "PXD900318",
        "title": "Human tumor tissue TMT 11-plex PMID: 38765432",
        "description": "Homo sapiens patients, tumor tissue, protein groups.",
        "human": True,
        "inferred_plex": 11,
        "tmt_detected": True,
        "source": "pride_search_v3",
        "pmid": "38765432",
    }
    out = classify_candidate(item, catalog, cfg=default_filter_config())
    assert out["verdict"] == "already_in_catalog"
