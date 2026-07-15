from atlas_agent.config import load_config
from atlas_agent.discovery.abstract_reader import _regex_extract
from atlas_agent.discovery.catalog_profile import build_atlas_semantic_context
from atlas_agent.sources.projects_table import load_catalog


def test_semantic_context_from_catalog():
    cfg = load_config()
    df = load_catalog(cfg)
    ctx = build_atlas_semantic_context(df, max_examples=8)
    assert ctx["n_atlas"] == len(df)
    assert len(ctx["examples"]) >= 5
    assert "REFERENCE ATLAS" in ctx["prompt_block"]
    assert "NO PXD" in ctx["prompt_block"]


def test_regex_semantic_fit_without_pxd():
    ai = _regex_extract(
        "TMT proteomics of colorectal cancer patients",
        "We performed tandem mass tag labeling on tumor and adjacent normal tissue "
        "from 50 patients using quantitative proteomics. Data: PXD999999.",
        "",
    )
    assert ai["atlas_fit"] in ("yes", "maybe")
    assert ai["atlas_fit_score"] >= 0.5
    assert not ai["accessions"]["PXD"]
    assert not ai["accessions"]["PDC"]


def test_regex_rejects_tmt6():
    ai = _regex_extract(
        "TMT6 proteomics",
        "TMT6 labeling of patient plasma proteomics cohort.",
        "",
    )
    assert ai["atlas_fit"] == "no"
    assert ai["tmt"] == "TMT6"
