"""Tests for canonical cell reading rules."""
from atlas_agent.catalog.cell_read import (
    audit_sample_columns,
    cell_state,
    parse_count,
    parse_number,
    strip_cell,
)


def test_empty_vs_zero():
    assert strip_cell(None) == ""
    assert strip_cell("nan") == ""
    assert strip_cell(0) == "0"
    assert cell_state("") == "empty"
    assert cell_state(0) == "zero"
    assert cell_state("0") == "zero"
    assert cell_state("12") == "value"
    assert parse_number("") is None
    assert parse_number(0) == 0.0
    assert parse_count("") == 0.0
    assert parse_count(0) == 0.0


def test_total_mismatch():
    row = {
        "Project ID": "PXD000001",
        "Total Samples": 100,
        "Case Cancer Untreated": 40,
        "Control Healthy": 40,
    }
    issues = audit_sample_columns(row)
    assert any(i["code"] == "total_mismatch" for i in issues)


def test_total_empty_with_parts():
    row = {
        "Project ID": "PXD000002",
        "Total Samples": "",
        "Case Cancer Untreated": 10,
    }
    issues = audit_sample_columns(row)
    assert any(i["code"] == "total_empty_parts" for i in issues)
