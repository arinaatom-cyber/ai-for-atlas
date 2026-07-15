"""Tests for discovery data availability classification."""
from atlas_agent.discovery.data_availability import _classify_files


def test_quant_protein_txt():
    r = _classify_files(["checksum.txt", "Protein.txt", "sample.raw"])
    assert r["status"] == "quant_table"
    assert "Protein.txt" in r["quant_files"]


def test_psm_only():
    r = _classify_files(["peptide_identifications.mzid", "run.raw"])
    assert r["status"] in ("processed_psm", "raw_only")


def test_no_quant():
    r = _classify_files(["checksum.txt", "crap.fasta"])
    assert r["status"] in ("no_files", "raw_only")
