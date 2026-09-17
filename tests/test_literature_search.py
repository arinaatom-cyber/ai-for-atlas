"""Tests for professional literature search pipeline."""
from __future__ import annotations

from atlas_agent.discovery.abstract_reader import (
    _consensus_with_regex,
    _is_garbage_llm,
    _regex_extract,
)
from atlas_agent.discovery.evaluation.sanitize import sanitize_summary
from atlas_agent.discovery.filters import _infer_sample_design
from atlas_agent.discovery.literature_search import (
    atlas_literature_queries,
    prefilter_publication,
    publication_has_repository_id,
    score_publication_relevance,
)
from atlas_agent.sources.dataset_resolve import literature_semantic_candidates


def test_atlas_queries_exclude_methods():
    qs = atlas_literature_queries(2024, 2026)
    assert len(qs) >= 3
    assert all("NOT (" in q for q in qs[:3])
    assert all("TMT" in q or "tandem mass tag" in q for q in qs)


def test_prefilter_drops_integrator_title():
    pub = {
        "title": "Analysis of isobaric quantitative proteomic data using TMT-Integrator",
        "abstract": "We present a computational platform for TMT data.",
        "data_availability": "",
    }
    ok, reason = prefilter_publication(pub)
    assert ok is False
    assert "exclusion" in reason


def test_score_higher_for_patient_tmt():
    weak = {
        "title": "MoSAIC workflow for PTM analysis",
        "abstract": "Software toolbox for proteomics.",
    }
    strong = {
        "title": "TMT proteomics of colorectal cancer tumor and adjacent normal",
        "abstract": "Human patients, TMT 11-plex, protein-level quantification, PXD099999.",
        "data_availability": "ProteomeXchange PXD099999",
    }
    assert score_publication_relevance(strong) > score_publication_relevance(weak)


def test_publication_has_repository_id():
    pub = {"title": "Study", "abstract": "Data at PXD012345", "data_availability": ""}
    assert publication_has_repository_id(pub) is True


def test_garbage_llm_detected():
    assert _is_garbage_llm(
        {
            "atlas_fit": "yes",
            "summary_ru": "This JSON schema describes human TMT proteomics like the atlas.",
            "semantic_evidence": [],
        }
    )


def test_low_trust_llm_cannot_promote_to_yes_alone():
    regex = _regex_extract(
        "TMT proteomics in patients",
        "Human cohort TMT 10-plex tumor tissue protein quantification.",
        "",
    )
    llm = {
        "atlas_fit": "yes",
        "atlas_fit_score": 0.9,
        "summary_ru": "Подходит.",
        "semantic_evidence": ["TMT proteomics"],
    }
    merged = _consensus_with_regex(regex, llm, engine="gpt4all:qwen2-1_5b-instruct-q4_0.gguf")
    assert merged["atlas_fit"] in ("no", "maybe")


def test_sanitize_strips_boilerplate():
    assert sanitize_summary("This paper describes human TMT/isobaric quantitative proteomics") == ""


def test_case_control_design_inference():
    blob = (
        "case-control study comparing PVR patients with matched RRD controls "
        "human vitreous TMT 10-plex"
    )
    assert _infer_sample_design(blob) == "case_control"


def test_literature_semantic_skips_method_papers():
    pubs = [
        {
            "pmid": "41771895",
            "title": "Analysis of isobaric quantitative proteomic data using TMT-Integrator",
            "abstract": "Computational platform FragPipe TMT-Integrator.",
            "abstract_ai": {"atlas_fit": "yes", "atlas_fit_score": 0.8},
            "abstract_reader": "gpt4all:test",
        }
    ]
    out = literature_semantic_candidates(pubs, known_accessions=set())
    assert out == []


def test_regex_extract_tmt16_not_tmt6():
    out = _regex_extract(
        "TMT16 proteomics of lung cancer",
        "Human patients TMT 16-plex protein-level tumor tissue.",
        "",
    )
    assert out["tmt"] == "TMT16"
    assert out["atlas_fit"] != "no" or "TMT6" not in str(out.get("semantic_evidence"))


def test_regex_extract_mixed_organism_rejected():
    out = _regex_extract(
        "Human and murine comparative TMT proteomics of colorectal cancer",
        "Patients and mouse xenograft tumor tissue, TMT 11-plex protein-level.",
        "",
    )
    assert out["organism"] == "mixed"
    assert out["atlas_fit"] == "no"
    assert out["human_suitable"] is False


def test_regex_extract_tmt7_allowed():
    out = _regex_extract(
        "TMT7 proteomics of colorectal cancer",
        "Human patients TMT 7-plex protein-level tumor tissue.",
        "",
    )
    assert out["tmt"] == "TMT7"
    assert out["atlas_fit"] in ("yes", "maybe")


def test_regex_extract_plasma_only_rejected():
    out = _regex_extract(
        "Plasma proteomics of colorectal cancer",
        "Human patients TMT 11-plex protein-level quantification of plasma.",
        "",
    )
    assert out["material"] == "plasma"
    assert out["atlas_fit"] == "no"
    assert out["material_suitable"] is False


def test_regex_extract_tmtpro18():
    out = _regex_extract(
        "TMTpro18 proteomics of gastric cancer",
        "Human patients TMTpro 18-plex protein-level quantification of tumor tissue.",
        "",
    )
    assert out["tmt"] == "TMTpro18"
    assert out["atlas_fit"] in ("yes", "maybe")


def test_regex_extract_rejects_glaucoma():
    out = _regex_extract(
        "Isobaric quantitative proteomics of glaucomatous trabecular meshwork cells",
        "Primary cell cultures, TMT 16-plex extracellular matrix.",
        "",
    )
    assert out["atlas_fit"] == "no"


def test_prefilter_drops_murine_with_human_reagent():
    pub = {
        "title": "Confirmatory study of rhNRGβ1 in a Murine Model of nerve injury",
        "abstract": "216 mice received recombinant human Neuregulin-1.",
        "data_availability": "",
    }
    ok, reason = prefilter_publication(pub)
    assert ok is False
    assert "exclusion" in reason


def test_literature_semantic_keeps_strong_cohort():
    pubs = [
        {
            "pmid": "41966223",
            "title": "Proteomic Analysis of Paired FFPE Tissue in Stage II Colorectal Cancer",
            "abstract": (
                "Human patients TMT 11-plex protein quantification tumor tissue "
                "clinical cohort proteome"
            ),
            "abstract_ai": {
                "atlas_fit": "maybe",
                "atlas_fit_score": 0.65,
                "regex_fit": "maybe",
                "summary_ru": "Возможно подходит: human clinical proteomics.",
            },
            "abstract_reader": "gpt4all:test",
            "literature_relevance": 0.7,
        }
    ]
    out = literature_semantic_candidates(pubs, known_accessions=set(), min_score=0.55)
    assert len(out) == 1
    assert out[0]["pmid"] == "41966223"
