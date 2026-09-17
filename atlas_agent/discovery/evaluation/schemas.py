"""Domain models for discovery evaluation — no raw dicts at boundaries."""
from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field, field_validator


class ExclusionReason(str, Enum):
    PHOSHO_ONLY = "phospho_only"
    METHODOLOGY = "methodology_review"
    SINGLE_CELL = "single_cell"
    NON_HUMAN = "non_human"
    LLM_REJECTED = "llm_rejected"
    PEPTIDE_ONLY = "peptide_only"
    TMT6_OR_LOW_PLEX = "tmt6_or_low_plex"
    NO_PROTEIN_TABLE = "no_protein_table"
    REVIEW_SOFTWARE = "review_software"
    OFF_ATLAS_DISEASE = "off_atlas_disease"
    BIOFLUID = "biofluid"


class ModelTrustLevel(str, Enum):
    HIGH = "high"  # GPT-4o, Claude, cloud APIs
    MEDIUM = "medium"  # Local Ollama qwen2.5:3b+
    LOW = "low"  # GPT4All qwen2-1.5b
    RULES = "rules"  # regex / deterministic fallback


class FinalVerdict(str, Enum):
    CANDIDATE = "Candidate"
    WATCH = "Watch"
    EXCLUDE = "Exclude"


class ConfidenceTier(str, Enum):
    A = "A"
    B = "B"
    C = "C"
    D = "D"


class ItemKind(str, Enum):
    PROJECT = "project"
    LITERATURE = "literature"
    COHORT = "cohort"


class LLMVerdict(BaseModel):
    fit: bool = Field(..., description="Strict boolean, no 'maybe'")
    material: str | None = Field(None, max_length=100)
    reasoning: str = Field(..., max_length=150)

    @classmethod
    def from_legacy_fit(cls, fit: str, *, material: str | None = None, reasoning: str = "") -> LLMVerdict:
        f = str(fit or "").lower()
        return cls(
            fit=f == "yes",
            material=(material or "")[:100] or None,
            reasoning=(reasoning or f"legacy atlas_fit={fit}")[:150],
        )


class EvaluationEvidence(BaseModel):
    source: str = Field(..., description='e.g. "regex_engine", "llm_high", "llm_low"')
    score: float | None = None
    is_actionable: bool = Field(True, description="False if score is below threshold or irrelevant")
    reason: ExclusionReason | None = None
    detail: str | None = Field(None, max_length=200)

    @field_validator("score")
    @classmethod
    def clamp_score(cls, v: float | None) -> float | None:
        if v is None:
            return None
        return max(0.0, min(1.0, float(v)))


class ProjectEvaluation(BaseModel):
    final_verdict: str = Field(..., description="Candidate | Watch | Exclude")
    confidence: str = Field(..., description="A | B | C | D")
    evidence_chain: list[EvaluationEvidence] = Field(default_factory=list)
    requires_manual_review: bool = False
    confidence_css: str = ""
    confidence_bullets: list[str] = Field(default_factory=list)
    display_fit_label: str = ""

    @property
    def verdict_enum(self) -> FinalVerdict:
        return FinalVerdict(self.final_verdict)

    @property
    def tier_enum(self) -> ConfidenceTier:
        return ConfidenceTier(self.confidence)

    def actionable_evidence(self) -> list[EvaluationEvidence]:
        return [e for e in self.evidence_chain if e.is_actionable]

    def exclusion_reasons(self) -> list[ExclusionReason]:
        return [e.reason for e in self.evidence_chain if e.reason is not None]
