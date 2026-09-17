from pathlib import Path

import pandas as pd

from atlas_agent.discovery.filters import build_catalog_index, classify_candidate, default_filter_config
from atlas_agent.sources.catalog_sync import (
    catalog_sync_lines,
    compare_frames,
    compare_summary,
    safe_compare_from_config,
)
from atlas_agent.sources.projects_table import all_repo_ids, catalog_path, normalize_doi, primary_project_id


def test_all_repo_ids_keeps_ipx_and_pxd():
    ids = all_repo_ids("IPX0002532001 (PXD022714)")
    assert ids == {"IPX0002532001", "PXD022714"}
    assert primary_project_id("IPX0002532001 (PXD022714)") == "PXD022714"


def test_catalog_path_prefers_csv(tmp_path: Path):
    csv = tmp_path / "projects.csv"
    xlsx = tmp_path / "book.xlsx"
    csv.write_text("Project ID\nPXD000001\n", encoding="utf-8")
    xlsx.write_bytes(b"PK\x03\x04")
    sc = {
        "projects_csv": str(csv),
        "projects_file": str(xlsx),
        "proteomics_workbook": str(xlsx),
        "catalog_runtime": "csv",
    }
    assert Path(catalog_path(sc)).name == "projects.csv"


def test_catalog_path_falls_back_to_xlsx(tmp_path: Path):
    xlsx = tmp_path / "book.xlsx"
    xlsx.write_bytes(b"PK\x03\x04")
    sc = {
        "projects_csv": str(tmp_path / "missing.csv"),
        "proteomics_workbook": str(xlsx),
    }
    assert Path(catalog_path(sc)).name == "book.xlsx"


def test_compare_frames_reports_id_drift():
    left = pd.DataFrame([{"Project ID": "PXD000001", "Title": "A", "PMID": ""}])
    right = pd.DataFrame([{"Project ID": "PXD000002", "Title": "A", "PMID": ""}])
    result = compare_frames(left, right)
    assert result["in_sync"] is False
    assert "PXD000001" in result["only_left"]
    assert "PXD000002" in result["only_right"]


def test_compare_frames_ignores_newline_only_title_diff():
    left = pd.DataFrame([{"Project ID": "PXD000001", "Title": "Endometrial\r\n Carcinoma", "PMID": ""}])
    right = pd.DataFrame([{"Project ID": "PXD000001", "Title": "Endometrial\n Carcinoma", "PMID": ""}])
    result = compare_frames(left, right)
    assert result["in_sync"] is True


def test_catalog_index_indexes_both_accessions_and_doi():
    df = pd.DataFrame(
        [
            {
                "Project ID": "IPX0002532001 (PXD022714)",
                "PMID": "12345678",
                "DOI": "https://doi.org/10.1234/atlas",
                "Title": "Gastric cancer TMT",
                "URL": "",
            }
        ]
    )
    idx = build_catalog_index(df)
    assert "IPX0002532001" in idx["accessions"]
    assert "PXD022714" in idx["accessions"]
    assert "12345678" in idx["pmids"]
    assert "10.1234/atlas" in idx["dois"]


def test_cross_repo_ipx_is_already_in_catalog():
    idx = build_catalog_index(
        pd.DataFrame([{"Project ID": "IPX0002532001 (PXD022714)", "PMID": "", "Title": ""}])
    )
    out = classify_candidate(
        {"accession": "IPX0002532001", "title": "Same iProX deposit"},
        idx,
        cfg=default_filter_config(),
    )
    assert out["verdict"] == "already_in_catalog"


def test_same_doi_is_already_in_catalog():
    idx = build_catalog_index(
        pd.DataFrame([{"Project ID": "PXD000001", "PMID": "", "DOI": "10.9999/foo", "Title": ""}])
    )
    out = classify_candidate(
        {"accession": "MSV000099999", "doi": "doi:10.9999/foo", "title": "MassIVE mirror"},
        idx,
        cfg=default_filter_config(),
    )
    assert out["verdict"] == "already_in_catalog"
    assert any("DOI:" in r for r in out["filter_reasons"])


def test_normalize_doi_strips_resolver():
    assert normalize_doi("https://doi.org/10.1/ABC") == "10.1/abc"


def test_catalog_sync_lines_warn_on_id_drift():
    left = pd.DataFrame([{"Project ID": "PXD000001", "Title": "A", "PMID": ""}])
    right = pd.DataFrame([{"Project ID": "PXD000002", "Title": "A", "PMID": ""}])
    lines = catalog_sync_lines(compare_frames(left, right))
    text = "\n".join(lines)
    assert "WARNING: runtime CSV and Proteomics workbook differ." in text
    assert "PXD000001" in text
    assert "sync_tmt_projects_csv.py --apply" in text


def test_catalog_sync_lines_ok_when_in_sync():
    df = pd.DataFrame([{"Project ID": "PXD000001", "Title": "A", "PMID": ""}])
    lines = catalog_sync_lines(compare_frames(df, df.copy()))
    assert lines == ["CSV and workbook: in sync (1 rows)."]


def test_catalog_sync_lines_xlsx_missing_is_note_not_warning():
    lines = catalog_sync_lines(
        {
            "in_sync": True,
            "warning": "xlsx_missing",
            "note": "Runtime catalog is CSV; workbook absent — nothing to compare.",
        }
    )
    assert lines
    assert not any(line.startswith("WARNING") for line in lines)


def test_safe_compare_from_config_survives_bad_loader(monkeypatch):
    def boom(_cfg):
        raise RuntimeError("openpyxl exploded")

    monkeypatch.setattr(
        "atlas_agent.sources.catalog_sync.compare_from_config",
        boom,
    )
    out = safe_compare_from_config({})
    assert out["in_sync"] is False
    assert out["error"] == "RuntimeError"
    lines = catalog_sync_lines(out)
    assert lines[0].startswith("WARNING: catalog compare failed")


def test_compare_summary_counts_diffs():
    left = pd.DataFrame([{"Project ID": "PXD000001", "Title": "A", "PMID": ""}])
    right = pd.DataFrame([{"Project ID": "PXD000002", "Title": "A", "PMID": ""}])
    slim = compare_summary(compare_frames(left, right))
    assert slim["in_sync"] is False
    assert slim["only_csv"] == ["PXD000001"]
    assert slim["only_workbook"] == ["PXD000002"]
    assert slim["cell_diff_count"] == 0


def test_cmd_scan_prints_catalog_drift(monkeypatch, capsys):
    import argparse

    import run_discovery

    monkeypatch.setattr(
        run_discovery,
        "load_config",
        lambda _=None: {"sheet": {"projects_csv": "data/projects.csv", "projects_sheet": "TMT ATLAS"}},
    )
    monkeypatch.setattr(
        run_discovery,
        "load_catalog_readonly",
        lambda cfg: pd.DataFrame([{"Project ID": "PXD000001"}]),
    )
    monkeypatch.setattr(
        "atlas_agent.sources.projects_table.catalog_path",
        lambda sc: "data/projects.csv",
    )
    monkeypatch.setattr(
        "atlas_agent.sources.catalog_sync.safe_compare_from_config",
        lambda cfg: compare_frames(
            pd.DataFrame([{"Project ID": "PXD000001", "Title": "A", "PMID": ""}]),
            pd.DataFrame([{"Project ID": "PXD000002", "Title": "A", "PMID": ""}]),
        ),
    )
    monkeypatch.setattr(
        run_discovery,
        "run_discovery_scan",
        lambda df, cfg, root=None: {"summary": {}, "report_md": "x"},
    )
    rc = run_discovery.cmd_scan(argparse.Namespace(config=None))
    assert rc == 0
    out = capsys.readouterr().out
    assert "WARNING: runtime CSV and Proteomics workbook differ." in out
