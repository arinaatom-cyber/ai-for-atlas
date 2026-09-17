"""Site sanitize must not downgrade repository project evaluations."""
from atlas_agent.discovery.evaluation import attach_evaluation
from atlas_agent.discovery.evaluation.schemas import ItemKind
from atlas_agent.viz.site_sanitize import sanitize_discovery_item


def test_sanitize_preserves_project_evaluation():
    item = {
        "accession": "PXD077831",
        "project_accession": "PXD077831",
        "title": "Human TMT vitreous proteomics",
        "data_availability": {"status": "quant_table", "omics_layer": "protein"},
        "sample_design": "healthy_only",
        "human": True,
        "qc_status": "candidate",
        "inferred_plex": 10,
    }
    attach_evaluation(item, kind=ItemKind.PROJECT)
    assert item["confidence_tier"] == "A"
    assert item["evaluation"]["final_verdict"] == "Candidate"

    sanitize_discovery_item(item)
    assert item["confidence_tier"] == "A"
    assert item["evaluation"]["final_verdict"] == "Candidate"
    assert "Literature surveillance" not in (item.get("confidence_evidence") or [])
