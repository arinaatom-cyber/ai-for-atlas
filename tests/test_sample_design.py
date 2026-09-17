"""Sample design inference — disease controls vs healthy-only."""

from atlas_agent.discovery.filters import _infer_sample_design, classify_candidate, default_filter_config


def test_pvr_rrd_is_case_control_not_healthy_only():
    blob = (
        "A case-control study of proliferative vitreoretinopathy comparing patients "
        "who later developed PVR with matched RRD controls"
    )
    assert _infer_sample_design(blob) == "case_control"


def test_matched_controls_without_healthy_keyword():
    blob = "TMT proteomics comparing metastatic tumors with matched controls without metastasis"
    assert _infer_sample_design(blob) == "case_control"


def test_healthy_controls_still_detected():
    blob = "TMT proteomics of tumor tissue and healthy control subjects from donors"
    assert _infer_sample_design(blob) == "case_control"


def test_healthy_only_when_no_cancer_terms():
    blob = "Proteomics of healthy volunteers and normal tissue donors"
    assert _infer_sample_design(blob) == "healthy_only"


def test_co_ip_interactome_filtered():
    item = {
        "title": "Co-immunoprecipitation enrichment mass spectrometry of EGFR interactome",
        "accession": "PXD083797",
        "source": "pride_api",
        "human": True,
        "tmt_detected": True,
        "inferred_plex": 10,
    }
    out = classify_candidate(item, {"pmids": set(), "accessions": set()}, cfg=default_filter_config())
    assert out["verdict"] == "filtered_out"
    assert any("interactome" in r.lower() or "co-ip" in r.lower() for r in out["filter_reasons"])
