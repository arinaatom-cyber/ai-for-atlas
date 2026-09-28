from __future__ import annotations

import re
import tempfile
import unittest
from pathlib import Path

from atlas_agent.viz.discovery_html import generate_discovery_html, generate_guide_html
from atlas_agent.viz.discovery_qc_html import generate_qc_html
from atlas_agent.viz.discovery_stats import classify_accepted_material, summarize_report
from atlas_agent.viz.i18n_loader import load_i18n_dicts


def _candidate(**kwargs):
    item = {
        "accession": "PXD000001",
        "title": "Human tumor tissue TMT proteomics",
        "confidence_tier": "A",
        "evaluation": {
            "final_verdict": "Candidate",
            "confidence": "A",
            "evidence_chain": [],
            "requires_manual_review": False,
        },
        "data_availability": {"status": "quant_table", "label": "Protein table"},
        "material_signals": {"included": ["human_tissue"]},
    }
    item.update(kwargs)
    return item


class DiscoveryStatsTests(unittest.TestCase):
    def test_classify_cell_line_tissue_primary_site(self):
        self.assertEqual(
            classify_accepted_material(
                _candidate(
                    title="MCF7 cancer cell line TMT",
                    material_signals={"included": ["human_cancer_cell_line"]},
                )
            ),
            "cell_line",
        )
        self.assertEqual(
            classify_accepted_material(
                _candidate(
                    primary_site="Ovary",
                    material_signals={"included": ["pdc_clinical_tumor"]},
                )
            ),
            "primary_site",
        )
        self.assertEqual(
            classify_accepted_material(
                _candidate(material_signals={"included": ["human_tumor_tissue"]})
            ),
            "tissue",
        )

    def test_summarize_checked_accepted_and_material_split(self):
        report = {
            "summary": {
                "novel_total": 40,
                "candidates": 3,
                "rejected_material": 10,
                "filtered_out": 20,
            },
            "candidates": [
                _candidate(
                    accession="PXD111",
                    title="A549 cell line panel",
                    material_signals={"included": ["human_cancer_cell_line"]},
                ),
                _candidate(
                    accession="PXD222",
                    title="Colon tumor tissue",
                    material_signals={"included": ["human_tumor_tissue"]},
                ),
                _candidate(
                    accession="PDC0001",
                    title="PDC ovarian",
                    primary_site="Ovary",
                    material_signals={"included": ["pdc_clinical_tumor"]},
                ),
                _candidate(
                    accession="PXD333",
                    title="Watch only",
                    evaluation={
                        "final_verdict": "Exclude",
                        "confidence": "C",
                        "evidence_chain": [],
                        "requires_manual_review": False,
                    },
                ),
            ],
            "rejected_material": [{"accession": "PXD999"}],
            "filtered_out": [{"accession": "PXD888"}],
        }
        stats = summarize_report(report)
        self.assertEqual(stats["checked"], 40)
        self.assertEqual(stats["accepted"], 3)
        self.assertEqual(stats["cell_line"], 1)
        self.assertEqual(stats["tissue"], 1)
        self.assertEqual(stats["primary_site"], 1)
        self.assertEqual(
            stats["cell_line"] + stats["tissue"] + stats["primary_site"],
            stats["accepted"],
        )

    def test_discovery_and_qc_share_kpi_numbers(self):
        report = {
            "generated_at": "2026-09-28T00:00:00Z",
            "summary": {"novel_total": 17, "candidates": 2},
            "candidates": [
                _candidate(
                    accession="PXD067886",
                    material_signals={"included": ["human_cancer_cell_line"]},
                ),
                _candidate(
                    accession="PDC000606",
                    primary_site="Gallbladder",
                    material_signals={"included": ["pdc_clinical_tumor"]},
                ),
            ],
        }
        with tempfile.TemporaryDirectory() as raw:
            tmp = Path(raw)
            disc = generate_discovery_html(report, tmp / "discovery.html").read_text(
                encoding="utf-8"
            )
            qc = generate_qc_html(report, tmp / "qc.html").read_text(encoding="utf-8")
        for key in (
            "kpi_checked",
            "kpi_accepted",
            "kpi_cell_line",
            "kpi_tissue",
            "kpi_primary_site",
        ):
            self.assertIn(f'data-i18n="{key}"', disc)
            self.assertIn(f'data-i18n="{key}"', qc)

        def kpis(html: str) -> list[str]:
            return re.findall(r'class="kpi-value">([^<]+)</span>', html)

        self.assertEqual(kpis(disc), kpis(qc))
        self.assertEqual(len(kpis(disc)), 5)
        for html in (disc, qc):
            self.assertNotIn("kpi_pride_manual", html)
            self.assertIn("cadence_monday", html)
            self.assertIn("cadence_local_llm", html)
        self.assertNotIn("table_scroll_hint", disc)
        self.assertNotIn("qc_regex_only", qc)
        self.assertNotIn("qc_pmid_review", qc)
        self.assertIn("PXD067886", qc)

    def test_guide_uses_two_column_rows_and_cadence(self):
        with tempfile.TemporaryDirectory() as raw:
            html = generate_guide_html(Path(raw) / "guide.html").read_text(encoding="utf-8")
        self.assertIn("guide-row", html)
        self.assertIn("guide_cadence_title", html)
        self.assertIn("page-content-wide", html)

    def test_i18n_has_new_kpi_keys(self):
        load_i18n_dicts.cache_clear()
        ru, en = load_i18n_dicts()
        self.assertEqual(ru["kpi_checked"], "Проверено")
        self.assertEqual(ru["kpi_accepted"], "Принято")
        self.assertEqual(ru["kpi_cell_line"], "Клеточная линия")
        self.assertEqual(ru["cadence_monday"], "Каждый понедельник")
        self.assertEqual(en["kpi_primary_site"], "Primary site")
        self.assertNotIn("ткань+3D", ru["qc_lead"])
        self.assertNotIn("mixed tissue+3D", en["qc_lead"].lower())


if __name__ == "__main__":
    unittest.main()
