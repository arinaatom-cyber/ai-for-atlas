"""Tests for architect-grade evaluation components."""
from __future__ import annotations

import pandas as pd

from atlas_agent.discovery.evaluation import (
    DISPLAY_SCORE_MIN,
    AnalysisFormatter,
    EvaluationPipeline,
    EvaluationService,
    ExclusionEngine,
    ExclusionReason,
    ItemKind,
    LLMEvaluatorRegistry,
    LocalEvaluator,
    SimilarityScorer,
    attach_evaluation,
    build_pipeline,
    evaluate_item,
    reset_default_pipeline,
    verdict_badge,
)
from atlas_agent.discovery.evaluation.atlas_index import TokenAtlasIndex
from atlas_agent.discovery.evaluation.config_loader import load_exclusion_config
from atlas_agent.discovery.evaluation.heuristics import scan_literature_text
from atlas_agent.discovery.evaluation.llm_router import trust_level_for_engine
from atlas_agent.discovery.evaluation.schemas import ModelTrustLevel
from atlas_agent.discovery.fit_rules import apply_literature_exclusions


def _pipeline() -> EvaluationPipeline:
    reset_default_pipeline()
    return build_pipeline(
        atlas_index=TokenAtlasIndex(index=[]),
        similarity_threshold=0.35,
    )


def test_trust_from_providers_yml_not_filename():
    reg = LLMEvaluatorRegistry()
    assert reg.trust_for_engine("claude") == ModelTrustLevel.HIGH
    assert reg.trust_for_engine("ollama:qwen2.5:3b") == ModelTrustLevel.MEDIUM
    assert reg.trust_for_engine("gpt4all:any-model-file.gguf") == ModelTrustLevel.LOW
    assert trust_level_for_engine("gpt4all:qwen2-1_5b-instruct-q4_0.gguf") == ModelTrustLevel.LOW


def test_exclusion_engine_from_yaml_config():
    engine = ExclusionEngine.from_config(load_exclusion_config())
    assert engine.rules_count() >= 5
    ev = engine.check(
        "Phosphoproteomics of gastric cancer",
        "TiO2 enrichment phosphorylation profiling.",
    )
    assert ev is not None
    assert ev.reason == ExclusionReason.PHOSHO_ONLY
    assert ev.source == "exclusion_engine"


def test_exclusion_engine_check_returns_first_hit():
    engine = ExclusionEngine.from_config(load_exclusion_config())
    hit = engine.check("Murine xenograft study", "No patients in xenograft models.")
    assert hit is not None
    assert hit.reason == ExclusionReason.NON_HUMAN


def test_phospho_scan_legacy_facade():
    chain = scan_literature_text(
        "Phosphoproteomics of gastric cancer",
        "We profiled phosphorylation sites using TiO2 enrichment.",
    )
    assert chain[0].reason == ExclusionReason.PHOSHO_ONLY


def test_similarity_scorer_actionable_threshold():
    index = TokenAtlasIndex(
        index=[
            {
                "project_id": "PXD000001",
                "tokens": {"gastric", "cancer", "tumor", "proteomics"},
                "title": "Gastric cancer proteomics",
            }
        ]
    )
    scorer = SimilarityScorer(index, threshold=0.35)
    low = scorer.evaluate("unrelated yeast bacterial study")
    assert low.is_actionable is False
    high = scorer.evaluate("gastric cancer tumor proteomics cohort")
    assert high.score is not None


def test_local_evaluator_low_trust_override():
    ev = LocalEvaluator().evaluate(
        {
            "abstract_ai": {"atlas_fit": "yes", "atlas_fit_score": 0.8, "reader": "gpt4all:model"},
            "abstract_reader": "gpt4all:model",
        }
    )
    assert ev.requires_manual_review is True
    assert ev.confidence_downgrade == 1
    assert any(e.source == "llm_low_override" for e in ev.evidence)


def test_pipeline_excludes_before_llm():
    pipe = _pipeline()
    result = pipe.run(
        {
            "title": "Phosphoproteomics landscape",
            "abstract": "Phosphorylation profiling only.",
            "abstract_ai": {"atlas_fit": "yes", "atlas_fit_score": 0.9},
        },
        kind=ItemKind.LITERATURE,
    )
    assert result.final_verdict == "Exclude"
    assert result.evidence_chain[0].source == "exclusion_engine"


def test_pipeline_low_trust_downgrades_and_manual_review():
    pipe = _pipeline()
    result = pipe.run(
        {
            "title": "Human TMT proteomics in colorectal cancer",
            "abstract": "Patients with tumor tissue.",
            "abstract_ai": {
                "atlas_fit": "yes",
                "atlas_fit_score": 0.7,
                "reader": "gpt4all:local",
            },
            "abstract_reader": "gpt4all:local",
        },
        kind=ItemKind.LITERATURE,
    )
    assert result.requires_manual_review is True
    assert any(e.source == "llm_low_override" for e in result.evidence_chain)


def test_apply_literature_exclusions_structured_evaluation():
    svc = EvaluationService(_pipeline())
    out = svc.apply_literature_exclusions(
        {
            "title": "Phosphoproteomics landscape",
            "abstract": "Phosphorylation profiling with TiO2 enrichment only.",
            "abstract_ai": {"atlas_fit": "maybe", "atlas_fit_score": 0.6},
        }
    )
    assert out["abstract_ai"]["atlas_fit"] == "no"
    assert out["evaluation"]["final_verdict"] == "Exclude"


def test_analysis_formatter_only_actionable():
    pipe = _pipeline()
    evaluation = pipe.run(
        {
            "title": "Human proteomics",
            "abstract": "Clinical cohort.",
            "abstract_ai": {
                "atlas_fit": "maybe",
                "atlas_fit_score": 0.2,
                "reader": "gpt4all:local",
            },
            "abstract_reader": "gpt4all:local",
        },
        kind=ItemKind.LITERATURE,
    )
    fmt = AnalysisFormatter()
    html = fmt.to_html(evaluation)
    assert "llm_low_override" not in html or "0.20" not in html
    actionable = evaluation.actionable_evidence()
    rendered = fmt.format_actionable_evidence(evaluation)
    assert len(rendered) == len(actionable)
    assert all("score=0.20" not in line for line in rendered if not any(
        e.is_actionable and e.score == 0.2 for e in evaluation.evidence_chain
    ))


def test_project_quant_table_tier_a():
    pipe = _pipeline()
    ev = evaluate_item(
        {
            "data_availability": {"status": "quant_table", "omics_layer": "protein"},
            "sample_design": "cancer_only",
            "human": True,
            "qc_status": "candidate",
            "inferred_plex": "TMT11",
        },
        kind=ItemKind.PROJECT,
        pipeline=pipe,
    )
    assert ev.confidence == "A"
    assert ev.final_verdict == "Candidate"


def test_attach_evaluation_writes_legacy_fields():
    pipe = _pipeline()
    item = {"data_availability": {"status": "no_files"}, "filter_reasons": ["raw only"]}
    attach_evaluation(item, kind=ItemKind.PROJECT, pipeline=pipe)
    assert item["confidence_tier"] == "D"
    assert "evaluation" in item


def test_verdict_badge_separate_from_tier():
    pipe = _pipeline()
    ev = evaluate_item(
        {
            "data_availability": {"status": "quant_table", "omics_layer": "protein"},
            "sample_design": "cancer_only",
            "human": True,
            "qc_status": "candidate",
        },
        kind=ItemKind.PROJECT,
        pipeline=pipe,
    )
    label, css, _ = verdict_badge(ev)
    assert label == "Candidate"
    assert css == "badge-ok"


def test_low_llm_score_not_actionable():
    pipe = _pipeline()
    ev = pipe.run(
        {
            "title": "Human TMT proteomics",
            "abstract": "Patients with cancer.",
            "abstract_ai": {
                "atlas_fit": "maybe",
                "atlas_fit_score": 0.2,
                "reader": "gpt4all:qwen2-1_5b-instruct-q4_0.gguf",
            },
            "abstract_reader": "gpt4all:qwen2-1_5b-instruct-q4_0.gguf",
        },
        kind=ItemKind.LITERATURE,
    )
    llm_ev = [e for e in ev.evidence_chain if e.source == "llm_low"]
    assert llm_ev
    assert llm_ev[0].score == 0.2
    assert llm_ev[0].is_actionable is False
    assert 0.2 < DISPLAY_SCORE_MIN


def test_pipeline_accepts_paper_kind_alias():
    pipe = _pipeline()
    ev = pipe.run(
        {"title": "Human gastric TMT proteomics", "abstract": "Patients with cancer.", "abstract_ai": {"atlas_fit": "maybe"}},
        kind="paper",
    )
    assert ev.confidence in ("A", "B", "C", "D")


def test_evaluate_discovery_report_attaches_structured_evaluation():
    from atlas_agent.discovery.evaluation.report import evaluate_discovery_report

    report = {
        "new_projects": [
            {
                "title": "Human TMT proteomics cohort",
                "abstract": "Tumor samples from patients.",
                "data_availability": {"status": "quant_table", "omics_layer": "protein"},
                "sample_design": "tumor_normal",
                "human": True,
                "qc_status": "candidate",
                "inferred_plex": "TMT10",
            }
        ],
        "manual_check": [
            {"title": "Review article on proteomics", "abstract": "We summarize methods without new data."},
        ],
    }
    evaluate_discovery_report(report, catalog_df=pd.DataFrame())
    assert report["new_projects"][0]["evaluation"]["final_verdict"]
    assert report["new_projects"][0]["confidence_tier"]
    assert report["manual_check"][0]["evaluation"]["final_verdict"] == "Exclude"


def test_evaluate_discovery_report_covers_repository_manual_and_rejected():
    from atlas_agent.discovery.evaluation.report import evaluate_discovery_report

    report = {
        "repository_manual": [
            {
                "accession": "PXD077831",
                "title": "Human TMT proteomics mixed organoid tissue",
                "abstract": "Patients and organoids.",
                "data_availability": {"status": "maybe_table"},
            }
        ],
        "rejected_material": [
            {
                "accession": "PXD000003",
                "title": "Phosphoproteomics landscape",
                "abstract": "Phosphorylation profiling with TiO2 enrichment only.",
            }
        ],
    }
    evaluate_discovery_report(report, catalog_df=pd.DataFrame())
    assert report["repository_manual"][0]["evaluation"]["final_verdict"]
    assert report["rejected_material"][0]["evaluation"]["final_verdict"] == "Exclude"


def test_stale_literature_eval_recomputed_for_project():
    from atlas_agent.discovery.evaluation.stale import should_recompute_evaluation

    item = {
        "confidence_tier": "C",
        "evaluation": {
            "final_verdict": "Watch",
            "confidence": "C",
            "confidence_bullets": ["Literature surveillance"],
        },
        "data_availability": {"status": "quant_table", "omics_layer": "protein"},
        "sample_design": "cancer_only",
        "human": True,
        "qc_status": "candidate",
    }
    assert should_recompute_evaluation(item, ItemKind.PROJECT) is True
    ev = evaluate_item(item, kind=ItemKind.PROJECT, pipeline=_pipeline())
    assert ev.confidence == "A"
    assert ev.final_verdict == "Candidate"
