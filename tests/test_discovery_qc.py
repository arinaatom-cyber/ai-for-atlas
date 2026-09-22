import unittest

from atlas_agent.viz.discovery_qc import (
    abstract_matches_title,
    content_tokens,
    dedupe_literature,
    is_plausible_pmid,
    sanitize_item_publication,
)


class PmidRangeTests(unittest.TestCase):
    def test_current_eight_digit_pmids_pass(self):
        self.assertTrue(is_plausible_pmid("41966223"))
        self.assertTrue(is_plausible_pmid("40493991"))

    def test_seven_digit_historical_ids_are_in_range(self):
        self.assertTrue(is_plausible_pmid("1861284"))
        self.assertTrue(is_plausible_pmid("1320544"))

    def test_nine_digit_out_of_range_rejected(self):
        self.assertFalse(is_plausible_pmid("609300501"))
        self.assertFalse(is_plausible_pmid("0"))
        self.assertFalse(is_plausible_pmid("123"))


class AbstractOverlapTests(unittest.TestCase):
    def test_unrelated_domains_are_mismatch(self):
        cases = [
            (
                "Serial Multi-omics Uncovers Anti-Glioblastoma Responses",
                "Duration of satisfactory breast feeding in Khartoum Province.",
            ),
            (
                "Global proteomic effects of PARP inhibitors in ovarian cancer",
                "Secretome of cancer-associated fibroblasts in pancreatic stroma.",
            ),
            (
                "CD70 as a cellular therapy target in high risk multiple myeloma",
                "Farnesyl transferase inhibition in lung cancer pull-down.",
            ),
            (
                "PXD012345 Human colon TMT proteome",
                "Quantitative proteomics of lymphatic vesicles in melanoma.",
            ),
        ]
        for title, abstract in cases:
            with self.subTest(title=title[:32]):
                self.assertFalse(abstract_matches_title(title, abstract))

    def test_synonyms_still_match_without_prefix(self):
        self.assertTrue(
            abstract_matches_title(
                "Proteomics of glioma U251 cells",
                "Glioblastoma multiforme (GBM) is an intracranial malignant tumor.",
            )
        )
        self.assertTrue(
            abstract_matches_title(
                "Stage II colorectal cancer FFPE tissue",
                "CRC remains a leading cause of cancer-related mortality.",
            )
        )

    def test_single_weak_token_is_not_a_match(self):
        self.assertFalse(
            abstract_matches_title(
                "Clinical treatment effects of TMT labelling weeks",
                "Clinical treatment effects of breastfeeding counselling after 12 weeks.",
            )
        )

    def test_organ_stem_is_not_a_prefix_match(self):
        self.assertFalse(
            abstract_matches_title(
                "TMT proteome of hepatocellular carcinoma",
                "Primary human hepatocyte cultures after isolation.",
            )
        )
        self.assertFalse(
            abstract_matches_title(
                "Pancreatic ductal adenocarcinoma TMT",
                "Chronic pancreatitis cohort serum proteins.",
            )
        )

    def test_lowercase_mm_is_not_myeloma(self):
        self.assertNotIn("myeloma", content_tokens("the tumor was 12 mm in diameter"))
        self.assertIn("myeloma", content_tokens("CD70 CAR-T in MM cell lines"))

    def test_matching_abstract_kept(self):
        title = "In-Depth Proteomic Analysis of Stage II Colorectal Cancer"
        abstract = "Colorectal cancer (CRC) remains a leading cause of cancer-related mortality."
        self.assertTrue(abstract_matches_title(title, abstract))


class SanitizeJoinTests(unittest.TestCase):
    def test_project_keeps_accession_when_pmid_abstract_mismatch(self):
        item = {
            "accession": "PXD063512",
            "title": "Serial Multi-omics Uncovers Anti-Glioblastoma Responses",
            "pmid": "31415926",
            "abstract": "Breast feeding in Khartoum Province maternal health centres.",
            "description": "Recurrent glioblastoma (rGBM) is incurable. Serial multi-omic assays.",
        }
        sanitize_item_publication(item)
        self.assertEqual(item.get("pmid"), "")
        self.assertEqual(item.get("publication_qc"), "abstract_mismatch")
        self.assertEqual(item.get("accession"), "PXD063512")
        self.assertIn("glioblastoma", item["description"].lower())

    def test_out_of_range_pmid_cleared_not_dropped_on_project(self):
        item = {"accession": "PXD000001", "title": "Ovarian TMT", "pmid": "609300501"}
        sanitize_item_publication(item)
        self.assertEqual(item["pmid"], "")
        self.assertEqual(item["publication_qc"], "pmid_out_of_range")
        self.assertEqual(item["accession"], "PXD000001")

    def test_dedupe_drops_fake_pmid_duplicate(self):
        rows = [
            {"title": "Apatinib glioma U251", "pmid": "40493991"},
            {"title": "Apatinib glioma U251", "pmid": "609300501"},
        ]
        out = dedupe_literature(rows)
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["pmid"], "40493991")


if __name__ == "__main__":
    unittest.main()
