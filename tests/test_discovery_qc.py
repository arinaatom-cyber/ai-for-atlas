import unittest

from atlas_agent.viz.discovery_qc import (
    abstract_matches_title,
    dedupe_literature,
    is_plausible_pmid,
    sanitize_item_publication,
)


class DiscoveryQcTests(unittest.TestCase):
    def test_pmid_must_be_eight_digits(self):
        self.assertTrue(is_plausible_pmid("41966223"))
        self.assertFalse(is_plausible_pmid("1861284"))
        self.assertFalse(is_plausible_pmid("609300501"))
        self.assertFalse(is_plausible_pmid("1320544"))
        self.assertFalse(is_plausible_pmid("0"))

    def test_glioblastoma_rejects_breastfeeding_abstract(self):
        title = "Serial Multi-omics Uncovers Anti-Glioblastoma Responses"
        abstract = (
            "The purpose of the study is to determine duration of satisfactory "
            "breast feeding in health breast-fed infants of mothers attending "
            "Maternal and Child Health Centres in the three towns of Khartoum Province."
        )
        self.assertFalse(abstract_matches_title(title, abstract))

    def test_matching_abstract_kept(self):
        title = "In-Depth Proteomic Analysis of Stage II Colorectal Cancer"
        abstract = "Colorectal cancer (CRC) remains a leading cause of cancer-related mortality."
        self.assertTrue(abstract_matches_title(title, abstract))

    def test_sanitize_clears_mismatched_pmid(self):
        item = {
            "title": "Serial Multi-omics Uncovers Anti-Glioblastoma Responses",
            "pmid": "31415926",
            "abstract": "Breast feeding in Khartoum Province maternal health centres.",
        }
        sanitize_item_publication(item)
        self.assertEqual(item.get("pmid"), "")

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
