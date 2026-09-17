from atlas_agent.discovery.organism_terms import is_human_text, is_non_human_text
from atlas_agent.viz.export_flat_candidates import FLAT_COLUMNS, iter_flat_candidates


def test_extended_non_human_terms():
    for term in (
        "rabbit liver TMT",
        "hamster CHO cells",
        "ovine muscle proteome",
        "guinea pig plasma",
        "Drosophila proteomics",
        "C. elegans TMT",
        "equine serum",
        "feline lymphoma cats",
    ):
        assert is_non_human_text(term), term
    assert is_human_text("Homo sapiens patient tumor tissue")
    assert not is_non_human_text("human colorectal tumor tissue TMT 11-plex")


def test_flat_export_has_organ_disease_finding():
    item = {
        "accession": "PXD000111",
        "source": "pride_search_v3",
        "title": "Human glioblastoma tumor tissue TMT 11-plex proteomics",
        "description": "Patients with glioblastoma, surgical tumor tissue, protein groups.",
        "abstract_ai": {"summary_en": "TMT proteome of glioblastoma tissue from patients."},
        "inferred_plex": 11,
        "tmt_detected": True,
        "human": True,
        "verdict": "recommended",
        "qc_status": "candidate",
        "pmid": "38765432",
        "url": "https://www.ebi.ac.uk/pride/archive/projects/PXD000111",
    }
    rows = iter_flat_candidates([item])
    assert list(rows[0].keys()) == FLAT_COLUMNS
    assert rows[0]["organ"]
    assert rows[0]["disease"]
    assert "glioblastoma" in rows[0]["finding"].lower() or "glioblastoma" in rows[0]["title"].lower()
    assert "11" in rows[0]["tmt_label"]
