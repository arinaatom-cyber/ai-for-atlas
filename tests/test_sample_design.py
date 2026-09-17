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


def test_unknown_sample_design_is_filtered_not_manual():
    item = {
        "title": "Human TMT 10-plex proteomics of tissue samples",
        "accession": "PXD088881",
        "source": "pride_api",
        "human": True,
        "tmt_detected": True,
        "inferred_plex": 10,
        "description": "Quantitative TMT 10-plex proteomics of human tissue from donors",
    }
    out = classify_candidate(item, {"pmids": set(), "accessions": set()}, cfg=default_filter_config())
    assert out["verdict"] == "filtered_out"
    assert any("Sample design unclear" in r for r in out["filter_reasons"])


def test_mixed_tissue_organoid_stays_manual_when_filters_pass():
    item = {
        "title": "Human cancer TMT 10-plex of tumor tissue and organoids",
        "accession": "PXD088882",
        "source": "pride_api",
        "human": True,
        "tmt_detected": True,
        "inferred_plex": 10,
        "description": (
            "Quantitative TMT 10-plex proteomics of tumor tissue from cancer patients "
            "and matched organoids. Case-control comparison with healthy controls."
        ),
    }
    out = classify_candidate(item, {"pmids": set(), "accessions": set()}, cfg=default_filter_config())
    assert out["verdict"] == "requires_manual_check"
    assert any("Mixed" in r or "organoid" in r.lower() for r in out["filter_reasons"])


def test_co_ip_interactome_filtered():
    item = {
        "title": "Co-immunoprecipitation enrichment mass spectrometry of EGFR interactome",
        "accession": "PXD083797",
        "source": "pride_api",
        "human": True,
        "tmt_detected": True,
        "inferred_plex": 10,
        "description": "IP-MS of EGFR interactome from tumor tissue of cancer patients, TMT 10-plex",
    }
    out = classify_candidate(item, {"pmids": set(), "accessions": set()}, cfg=default_filter_config())
    assert out["verdict"] == "filtered_out"
    assert any("interactome" in r.lower() or "co-ip" in r.lower() for r in out["filter_reasons"])
