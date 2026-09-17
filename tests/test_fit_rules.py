from atlas_agent.discovery.filters import classify_candidate, default_filter_config
from atlas_agent.discovery.fit_rules import (
    apply_literature_exclusions,
    is_cohort_excluded,
    is_non_study_literature,
    sanitize_summary,
)


def test_sanitize_summary_drops_json_schema_artifact():
    assert sanitize_summary("This JSON schema describes human proteomics") == ""
    assert sanitize_summary("Human TMT cohort in gastric cancer") == "Human TMT cohort in gastric cancer"


def test_non_study_literature_review():
    assert is_non_study_literature("A narrative review of proteomics in cancer")
    assert not is_non_study_literature("Proteomic profiling of 120 patients with CRC")


def test_cohort_excludes_software():
    assert is_cohort_excluded("MultiOmicsXplorer: an integrator platform for multi-omics")


def test_apply_literature_exclusions_mouse():
    item = {
        "title": "Murine tumor proteomics with TMT11",
        "abstract": "We studied mice xenograft models.",
        "abstract_ai": {"atlas_fit": "yes", "atlas_fit_score": 0.7, "summary_en": "JSON schema test"},
    }
    out = apply_literature_exclusions(item)
    assert out["atlas_fit"] == "no"
    assert out["atlas_fit_score"] is None
    assert out["abstract_ai"]["summary_en"] == ""


def test_human_reagent_does_not_rescue_murine_paper():
    title = (
        "A Multicenter Confirmatory Randomized-Controlled Study of rhNRGβ1 "
        "Protein Replacement Therapy in a Murine Model"
    )
    abstract = (
        "216 mice received recombinant human Neuregulin-1. Phosphoproteomics "
        "of sciatic nerve after crush injury."
    )
    assert is_non_study_literature(title, abstract)
    assert is_cohort_excluded(title, abstract)


def test_cohort_excludes_software_tool_to_browse():
    assert is_cohort_excluded(
        "MultiOmicsXplorer, a tool to browse, access and analyse multi-omics data.",
        "We present a browser for proteomics and phosphoproteomics.",
    )


def test_off_atlas_kidney_injury_excluded():
    assert is_non_study_literature(
        "ER stress contributes to cardiac biomarker-induced kidney injury",
        "Plasma biomarkers in heart failure patients, TMT proteomics.",
    )


def test_off_atlas_glaucoma_and_vitreous_excluded():
    assert is_non_study_literature(
        "Isobaric quantitative proteomics in glaucomatous trabecular meshwork cells",
        "Primary trabecular meshwork cell cultures from glaucoma donors.",
    )
    item = {
        "title": "The baseline vitreous proteome in rhegmatogenous retinal detachment",
        "abstract": "Human vitreous biopsies, case-control PVR, TMT 10-plex.",
        "abstract_ai": {"atlas_fit": "maybe"},
    }
    out = apply_literature_exclusions(item)
    assert out["atlas_fit"] == "no"


def test_cancer_cohort_not_excluded_as_off_atlas():
    assert not is_non_study_literature(
        "TMT proteomics of 120 patients with colorectal cancer",
        "Paired tumor and adjacent normal tissue, TMT 11-plex protein groups.",
    )


def test_classify_rejects_vitreous_and_broad():
    empty = {"pmids": set(), "accessions": set()}
    cfg = default_filter_config()
    vitreous = classify_candidate(
        {
            "accession": "PXD077831",
            "title": "The baseline vitreous proteome in rhegmatogenous retinal detachment",
            "description": "Human vitreous TMT 10-plex case-control PVR",
            "human": True,
            "inferred_plex": 10,
            "tmt_detected": True,
            "source": "pride_search_v3",
        },
        empty,
        cfg=cfg,
    )
    assert vitreous["verdict"] == "filtered_out"
    assert any("Off-atlas" in r for r in vitreous["filter_reasons"])

    broad = classify_candidate(
        {
            "accession": "PDC000430",
            "title": "Broad — Broad Institute",
            "program": "Broad Institute",
            "description": "TMT 11-plex proteome",
            "human": True,
            "inferred_plex": 11,
            "tmt_detected": True,
            "source": "pdc_api",
            "consortium": "PDC",
        },
        empty,
        cfg=cfg,
    )
    assert broad["verdict"] == "filtered_out"


def test_plex_policy_accepts_gt6_rejects_six_and_below():
    from atlas_agent.discovery.filters import plex_allowed

    cfg = default_filter_config()
    assert not plex_allowed(2, cfg)
    assert not plex_allowed(6, cfg)
    assert plex_allowed(7, cfg)
    assert plex_allowed(9, cfg)
    assert plex_allowed(10, cfg)
    assert plex_allowed(18, cfg)
    assert not plex_allowed(19, cfg)
    assert not plex_allowed(None, cfg, blob="TMT6 plasma proteomics")
    assert plex_allowed(None, cfg, blob="TMTpro18 tumor tissue")

    empty = {"pmids": set(), "accessions": set()}

    def _item(plex: int) -> dict:
        return classify_candidate(
            {
                "accession": f"PXD9{plex:05d}",
                "title": "Human colorectal cancer tumor tissue TMT proteomics",
                "description": "Homo sapiens patients, tumor tissue, protein groups, TMT labeling.",
                "human": True,
                "inferred_plex": plex,
                "tmt_detected": True,
                "source": "pride_search_v3",
            },
            empty,
            cfg=cfg,
        )

    assert _item(6)["verdict"] == "filtered_out"
    assert _item(7)["verdict"] != "filtered_out"
    assert _item(18)["verdict"] != "filtered_out"


def test_human_only_rejects_mouse_and_mixed():
    from atlas_agent.discovery.filters import is_confirmed_human

    empty = {"pmids": set(), "accessions": set()}
    cfg = default_filter_config()
    mouse = classify_candidate(
        {
            "accession": "PXD900001",
            "title": "Murine liver TMT11 proteomics",
            "description": "Mus musculus tissue TMT 11-plex protein groups.",
            "human": False,
            "inferred_plex": 11,
            "tmt_detected": True,
            "source": "pride_search_v3",
        },
        empty,
        cfg=cfg,
    )
    assert mouse["verdict"] == "filtered_out"

    mixed = classify_candidate(
        {
            "accession": "PXD900002",
            "title": "Human and mouse comparative TMT proteomics",
            "description": "Homo sapiens patients and mouse xenograft tumor tissue, TMT 11-plex.",
            "human": True,
            "inferred_plex": 11,
            "tmt_detected": True,
            "source": "pride_search_v3",
        },
        empty,
        cfg=cfg,
    )
    assert mixed["verdict"] == "filtered_out"
    assert is_confirmed_human(mixed, mixed["title"] + " " + mixed["description"]) is False

    hela = classify_candidate(
        {
            "accession": "PXD900003",
            "title": "TMT11 proteomics of MCF7 and A549 cancer cell lines",
            "description": "Protein groups, tumor cell line panel.",
            "inferred_plex": 11,
            "tmt_detected": True,
            "source": "pride_search_v3",
        },
        empty,
        cfg=cfg,
    )
    assert hela["verdict"] != "filtered_out" or "Human only" not in " ".join(hela.get("filter_reasons") or [])
