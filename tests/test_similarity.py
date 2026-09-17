import pandas as pd

from atlas_agent.revisor.similarity import annotate_candidates, catalog_token_index, find_similar, jaccard


def test_jaccard_overlap():
    assert jaccard({"colon", "cancer"}, {"colon", "tumor"}) == 1 / 3


def test_annotate_reuses_catalog_index(monkeypatch):
    calls: list[int] = []

    def _counting_index(df):
        calls.append(1)
        return catalog_token_index(df)

    monkeypatch.setattr("atlas_agent.revisor.similarity.catalog_token_index", _counting_index)

    df = pd.DataFrame(
        [
            {"Project ID": "PXD000001", "Title": "Colon cancer TMT proteomics", "Organ": "Colon"},
            {"Project ID": "PXD000002", "Title": "Lung tumor TMT study", "Organ": "Lung"},
        ]
    )
    candidates = [
        {"accession": "PXD999999", "title": "Colorectal carcinoma TMT quantitative proteomics"},
        {"accession": "PXD888888", "title": "Lung adenocarcinoma TMT proteomics"},
    ]
    annotate_candidates(candidates, df)
    assert calls == [1]


def test_find_similar_dedupes_duplicate_catalog_ids():
    df = pd.DataFrame(
        [
            {
                "Project ID": "PXD031107",
                "Title": "AML proteogenomics cohort A",
                "Organ": "Blood",
            },
            {
                "Project ID": "PXD031107",
                "Title": "AML proteogenomics cohort B",
                "Organ": "Blood",
            },
            {
                "Project ID": "PXD008378",
                "Title": "CD34 progenitor proteomics",
                "Organ": "Blood",
            },
        ]
    )
    sim = find_similar(
        {"accession": "PDC000604", "title": "Pediatric AML TMT proteomics"},
        df,
        threshold=0.0,
        top_k=5,
    )
    ids = [x["project_id"] for x in sim]
    assert ids.count("PXD031107") == 1


def test_find_similar_accepts_prebuilt_index():
    df = pd.DataFrame(
        [{"Project ID": "PXD000001", "Title": "Gastric cancer TMT atlas", "Organ": "Stomach"}]
    )
    index = catalog_token_index(df)
    sim = find_similar(
        {"accession": "PXD999999", "title": "Gastric cancer TMT proteomics patients"},
        df,
        index=index,
    )
    assert sim and sim[0]["project_id"] == "PXD000001"
