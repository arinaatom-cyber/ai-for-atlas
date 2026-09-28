from __future__ import annotations

import logging
from typing import Any

from atlas_agent.discovery.evaluation.exclusion_engine import ExclusionEngine
from atlas_agent.discovery.evaluation.llm_evaluator import LLMEvaluatorRegistry
from atlas_agent.discovery.evaluation.schemas import (
    ConfidenceTier,
    EvaluationEvidence,
    ExclusionReason,
    FinalVerdict,
    ItemKind,
    ProjectEvaluation,
)
from atlas_agent.discovery.evaluation.similarity_scorer import SimilarityScorer
from atlas_agent.discovery.evaluation.thresholds import COHORT_LARGE_N, COHORT_TMT_N

logger = logging.getLogger(__name__)

_TIER_ORDER = [ConfidenceTier.A, ConfidenceTier.B, ConfidenceTier.C, ConfidenceTier.D]

_KIND_ALIASES: dict[str, ItemKind] = {
    "paper": ItemKind.LITERATURE,
    "literature": ItemKind.LITERATURE,
}


def _normalize_kind(kind: ItemKind | str) -> ItemKind:
    if isinstance(kind, ItemKind):
        return kind
    key = str(kind).lower()
    if key in _KIND_ALIASES:
        return _KIND_ALIASES[key]
    return ItemKind(key)


def _downgrade_tier(tier: ConfidenceTier, steps: int = 1) -> ConfidenceTier:
    idx = _TIER_ORDER.index(tier)
    return _TIER_ORDER[min(idx + steps, len(_TIER_ORDER) - 1)]


def _legacy_fit(item: dict[str, Any]) -> str:
    ai = item.get("abstract_ai") or {}
    return str(item.get("atlas_fit") or ai.get("atlas_fit") or "").lower()


def _reader(item: dict[str, Any]) -> str:
    ai = item.get("abstract_ai") or {}
    return str(item.get("abstract_reader") or ai.get("reader") or "")


def _semantic_evidence(item: dict[str, Any]) -> list[str]:
    ai = item.get("abstract_ai") or {}
    return [str(x) for x in (ai.get("semantic_evidence") or [])[:3]]


class EvaluationPipeline:

    def __init__(
        self,
        exclusion_engine: ExclusionEngine,
        similarity_scorer: SimilarityScorer | None,
        llm_registry: LLMEvaluatorRegistry,
    ) -> None:
        self._exclusion = exclusion_engine
        self._similarity = similarity_scorer
        self._llm_registry = llm_registry

    @property
    def exclusion_engine(self) -> ExclusionEngine:
        return self._exclusion

    def run(
        self,
        item: dict[str, Any],
        *,
        kind: ItemKind | str = ItemKind.LITERATURE,
        has_accession: bool = False,
    ) -> ProjectEvaluation:
        k = _normalize_kind(kind)
        if k == ItemKind.PROJECT:
            return self._run_project(item)
        if k == ItemKind.COHORT:
            return self._run_cohort(item)
        return self._run_literature(item, has_accession=has_accession)

    def _run_literature(self, item: dict[str, Any], *, has_accession: bool) -> ProjectEvaluation:
        title = str(item.get("title") or "")
        abstract = str(item.get("abstract") or "")
        chain: list[EvaluationEvidence] = []

        exclusion = self._exclusion.check(title, abstract)
        if exclusion is not None:
            chain.append(exclusion)
            logger.info("Literature excluded: %s", exclusion.reason)
            return self._finalize(
                FinalVerdict.EXCLUDE,
                ConfidenceTier.D,
                chain,
                requires_manual_review=False,
                bullets=[exclusion.detail or "Atlas exclusion"],
                display_fit="",
            )

        if self._similarity is not None:
            sim_ev = self._similarity.evaluate(f"{title} {abstract}".strip())
            chain.append(sim_ev)

        reader = _reader(item)
        llm_evaluator = self._llm_registry.for_engine(reader)
        llm_result = llm_evaluator.evaluate(item)
        chain.extend(llm_result.evidence)

        fit = _legacy_fit(item)
        resolved = item.get("accessions_resolved") or (item.get("abstract_ai") or {}).get("accessions") or {}
        has_repo = has_accession and any(resolved.get(k) for k in ("PXD", "PDC", "MSV", "IPX"))

        requires_manual = llm_result.requires_manual_review
        tier = ConfidenceTier.C
        verdict = FinalVerdict.WATCH
        bullets: list[str] = []

        if fit == "no" or any(e.reason == ExclusionReason.LLM_REJECTED for e in chain):
            tier = ConfidenceTier.D
            verdict = FinalVerdict.EXCLUDE
            bullets.append("LLM / rules rejection")
        elif has_repo:
            tier = ConfidenceTier.A
            verdict = FinalVerdict.WATCH
            bullets.extend(["Repository ID from data availability", *_semantic_evidence(item)])
        elif fit == "yes":
            bullets.extend(["LLM yes — no verified PXD/PDC", *_semantic_evidence(item)])
            if reader:
                bullets.append(f"reader: {reader}")
        elif fit == "maybe":
            bullets.extend(["LLM maybe — literature watch", *_semantic_evidence(item)])
            requires_manual = True
        else:
            bullets.append("Literature surveillance")
            if reader:
                bullets.append(f"reader: {reader}")

        if llm_result.confidence_downgrade:
            tier = _downgrade_tier(tier, llm_result.confidence_downgrade)

        close_sim = next((e for e in chain if e.source == "similarity_scorer" and e.is_actionable), None)
        if close_sim and self._similarity and close_sim.is_actionable:
            bullets.append(f"Similar to catalog ({close_sim.detail})")

        display = f"LLM {fit}" if fit else ""
        return self._finalize(
            verdict,
            tier,
            chain,
            requires_manual_review=requires_manual,
            bullets=bullets,
            display_fit=display,
        )

    def _run_project(self, item: dict[str, Any]) -> ProjectEvaluation:
        title = str(item.get("title") or "")
        abstract = str(item.get("abstract") or "")
        chain: list[EvaluationEvidence] = []

        exclusion = self._exclusion.check(title, abstract)
        if exclusion is not None:
            chain.append(exclusion)
            return self._finalize(
                FinalVerdict.EXCLUDE,
                ConfidenceTier.D,
                chain,
                requires_manual_review=False,
                bullets=[exclusion.detail or "Text exclusion"],
                display_fit="",
            )

        if self._similarity is not None and title:
            chain.append(self._similarity.evaluate(f"{title} {abstract}".strip()))

        da = item.get("data_availability") or {}
        layer = da.get("omics_layer") or ""
        status = da.get("status") or ""
        design = item.get("sample_design") or "unknown"
        plex = item.get("inferred_plex") or item.get("tmt_label") or ""
        human = item.get("human") is not False
        qc = item.get("qc_status") or ""
        reasons = list(item.get("filter_reasons") or [])[:4]

        if status in ("phospho_table", "no_files", "raw_only") or layer == "phospho":
            chain.append(
                EvaluationEvidence(
                    source="file_gate",
                    reason=ExclusionReason.NO_PROTEIN_TABLE,
                    detail=status or layer,
                )
            )
            return self._finalize(
                FinalVerdict.EXCLUDE,
                ConfidenceTier.D,
                chain,
                requires_manual_review=False,
                bullets=["No protein-level table", reasons[0] if reasons else ""],
                display_fit="",
            )

        if layer == "mixed":
            chain.append(EvaluationEvidence(source="file_gate", detail="mixed protein+phospho files"))
            return self._finalize(
                FinalVerdict.WATCH,
                ConfidenceTier.B,
                chain,
                requires_manual_review=True,
                bullets=["Mixed protein+phospho files — manual matrix check", f"design: {design}"],
                display_fit="",
            )

        if status == "quant_table" and human and qc == "candidate" and design != "unknown":
            return self._finalize(
                FinalVerdict.CANDIDATE,
                ConfidenceTier.A,
                chain,
                requires_manual_review=False,
                bullets=[
                    "Protein quant table confirmed",
                    f"TMT {plex}" if plex else "TMT detected",
                    f"design: {design}",
                ],
                display_fit="",
            )

        if status in ("quant_table", "local_mirror", "maybe_table"):
            verdict = FinalVerdict.CANDIDATE if status == "quant_table" else FinalVerdict.WATCH
            return self._finalize(
                verdict,
                ConfidenceTier.B,
                chain,
                requires_manual_review=verdict == FinalVerdict.WATCH,
                bullets=["Quant files present", f"design: {design}", reasons[0] if reasons else "verify sample labels"],
                display_fit="",
            )

        return self._finalize(
            FinalVerdict.WATCH,
            ConfidenceTier.C,
            chain,
            requires_manual_review=True,
            bullets=["Needs manual review", reasons[0] if reasons else ""],
            display_fit="",
        )

    def _run_cohort(self, item: dict[str, Any]) -> ProjectEvaluation:
        title = str(item.get("title") or "")
        abstract = str(item.get("abstract") or "")
        exclusion = self._exclusion.check_cohort(title, abstract)
        chain: list[EvaluationEvidence] = []
        if exclusion is not None:
            chain.append(exclusion)
            return self._finalize(
                FinalVerdict.EXCLUDE,
                ConfidenceTier.D,
                chain,
                requires_manual_review=False,
                bullets=[exclusion.detail or "Review / software / narrative"],
                display_fit="",
            )

        n = int(item.get("patient_n") or 0)
        if item.get("tmt_detected") and n >= COHORT_TMT_N:
            tier = ConfidenceTier.B
            bullets = [f"N≈{n}", "TMT mention", "Cohort watch — not a new repo ID"]
        elif n >= COHORT_LARGE_N:
            tier = ConfidenceTier.C
            bullets = [f"Large cohort N≈{n}", "No TMT confirmation"]
        else:
            tier = ConfidenceTier.C
            bullets = ["Cohort literature watch"]
            if item.get("tmt_detected"):
                bullets.insert(0, "Large cohort + TMT mention")

        return self._finalize(
            FinalVerdict.WATCH,
            tier,
            chain,
            requires_manual_review=True,
            bullets=bullets,
            display_fit="",
        )

    @staticmethod
    def _finalize(
        verdict: FinalVerdict,
        tier: ConfidenceTier,
        chain: list[EvaluationEvidence],
        *,
        requires_manual_review: bool,
        bullets: list[str],
        display_fit: str,
    ) -> ProjectEvaluation:
        return ProjectEvaluation(
            final_verdict=verdict.value,
            confidence=tier.value,
            evidence_chain=chain,
            requires_manual_review=requires_manual_review,
            confidence_css=f"tier-{tier.value.lower()}",
            confidence_bullets=[b for b in bullets if b],
            display_fit_label=display_fit,
        )
