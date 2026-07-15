"""Tests for discovery data availability classification."""
from atlas_agent.discovery.data_availability import _classify_files, partition_phospho_only_candidates


def test_quant_protein_txt():
    r = _classify_files(["checksum.txt", "Protein.txt", "sample.raw"])
    assert r["status"] == "quant_table"
    assert r["omics_layer"] == "protein"
    assert "Protein.txt" in r["proteome_files"]


def test_phosphoproteome_table_not_quant_table():
    r = _classify_files(["Academia_Sinica_LUAD_ICPC_B_Phosphoproteome.qcmetrics.tsv"])
    assert r["status"] == "phospho_table"
    assert r["label"] == "phospho only"
    assert r["omics_layer"] == "phospho_only"
    assert r["phospho_files"]


def test_proteome_tmt_tsv():
    r = _classify_files(["CPTAC3_PNNL_HOPE_AYA_GBM_Proteome.tmt11.tsv"])
    assert r["status"] == "quant_table"
    assert r["omics_layer"] == "protein"
    assert "Proteome" in r["proteome_files"][0]


def test_mixed_proteome_and_phospho():
    r = _classify_files(
        [
            "CPTAC3_Proteome.tmt11.tsv",
            "CPTAC3_Phosphoproteome.peptides.tsv",
        ]
    )
    assert r["status"] == "quant_table"
    assert r["omics_layer"] == "mixed"
    assert r["proteome_files"]
    assert r["phospho_files"]


def test_partition_phospho_only_candidates():
    items = [
        {
            "accession": "PDC000564",
            "data_availability": {"omics_layer": "phospho_only", "status": "phospho_table"},
        },
        {
            "accession": "PXD077831",
            "data_availability": {"omics_layer": "protein", "status": "quant_table"},
        },
    ]
    kept, moved = partition_phospho_only_candidates(items)
    assert len(kept) == 1
    assert kept[0]["accession"] == "PXD077831"
    assert len(moved) == 1
    assert moved[0]["verdict"] == "filtered_out"


def test_psm_only():
    r = _classify_files(["peptide_identifications.mzid", "run.raw"])
    assert r["status"] in ("processed_psm", "raw_only")


def test_no_quant():
    r = _classify_files(["checksum.txt", "crap.fasta"])
    assert r["status"] in ("no_files", "raw_only")
