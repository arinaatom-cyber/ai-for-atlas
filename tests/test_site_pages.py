from pathlib import Path

from atlas_agent.viz.discovery_html import (
    generate_discovery_html,
    generate_guide_html,
    generate_methods_html,
)
from atlas_agent.viz.discovery_qc_html import generate_qc_html
from atlas_agent.viz.i18n_loader import load_i18n_dicts


def test_site_pages_split_guide_methods_qc(tmp_path: Path):
    report = {
        "generated_at": "2026-09-17T00:00:00Z",
        "summary": {"source_stats": {}},
        "candidates": [],
        "methods_manifest": {},
    }
    disc = generate_discovery_html(report, tmp_path / "discovery.html").read_text(encoding="utf-8")
    guide = generate_guide_html(tmp_path / "guide.html").read_text(encoding="utf-8")
    methods = generate_methods_html(report, tmp_path / "methods.html").read_text(encoding="utf-8")
    qc = generate_qc_html(report, tmp_path / "qc.html").read_text(encoding="utf-8")

    for html in (disc, guide, methods, qc):
        assert 'data-i18n="nav_guide"' in html
        assert 'data-i18n="nav_methods"' in html
        assert 'data-i18n="nav_qc"' in html
        assert "guide.html" in html
        assert "methods.html" in html
        assert "qc.html" in html

    assert 'id="guide"' not in disc
    assert 'id="technical"' not in disc
    assert "site-fold" not in disc
    assert 'data-i18n="guide_title"' in guide
    assert 'data-i18n="sec_methods"' in methods
    assert 'data-i18n="qc_title"' in qc
    assert 'class="active" data-i18n="nav_qc"' in qc


def test_nav_qc_label_is_quality_control_not_qc():
    load_i18n_dicts.cache_clear()
    ru, en = load_i18n_dicts()
    assert ru["nav_qc"] == "Контроль качества"
    assert en["nav_qc"] == "Quality control"
    assert ru["qc_title"] == "Контроль качества"
    assert "QC" not in ru["nav_qc"]
    assert ru["nav_guide"] == "Гайд"
    assert en["nav_guide"] == "Guide"
    assert ru["nav_methods"] == "Методы"
    assert en["nav_methods"] == "Methods"


def test_discovery_sort_uses_verdict_rank_and_keeps_stable_row_numbers(tmp_path: Path):
    html = generate_discovery_html(
        {"generated_at": "2026-09-22T00:00:00Z", "summary": {}, "candidates": []},
        tmp_path / "discovery.html",
    ).read_text(encoding="utf-8")
    assert "const VERDICT_RANK" in html
    assert "Candidate:0, Review:1, Watch:2, Exclude:3" in html
    assert "function missingYear" in html
    assert "if (num) num.textContent" not in html
    assert "rows.some(r => r.dataset.year === '—')" in html
