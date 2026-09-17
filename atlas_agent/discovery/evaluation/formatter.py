"""UI formatting — renders only actionable evidence from ProjectEvaluation."""
from __future__ import annotations

import html
import logging
from typing import Literal

from atlas_agent.discovery.evaluation.schemas import EvaluationEvidence, ProjectEvaluation
from atlas_agent.viz.display_format import format_bullet_text, sentence_cap

logger = logging.getLogger(__name__)


class AnalysisFormatter:
    """Decoupled presentation layer for discovery table / QC cells."""

    def __init__(self, *, max_summary_len: int = 280, max_bullet_len: int = 200) -> None:
        self._max_summary = max_summary_len
        self._max_bullet = max_bullet_len

    @staticmethod
    def _esc(text: str) -> str:
        return html.escape(text, quote=True)

    def format_evidence_line(self, evidence: EvaluationEvidence) -> str:
        parts: list[str] = [evidence.source]
        if evidence.reason is not None:
            parts.append(evidence.reason.value)
        if evidence.score is not None:
            parts.append(f"score={evidence.score:.2f}")
        if evidence.detail:
            parts.append(evidence.detail)
        return self._esc(" · ".join(parts)[: self._max_bullet])

    def format_actionable_evidence(self, evaluation: ProjectEvaluation) -> list[str]:
        lines = [self.format_evidence_line(e) for e in evaluation.actionable_evidence()]
        logger.debug("Formatted %s actionable evidence lines", len(lines))
        return lines

    def _summary_blocks(self, summary: str, summary_ru: str = "") -> str:
        en = sentence_cap(summary.strip()[: self._max_summary])
        ru = sentence_cap(summary_ru.strip()[: self._max_summary])
        if not en and not ru:
            return ""
        parts: list[str] = []
        if en:
            parts.append(
                f'<p class="cell-summary lang-block lang-en">{self._esc(en)}</p>'
            )
        if ru and ru != en:
            parts.append(
                f'<p class="cell-summary lang-block lang-ru">{self._esc(ru)}</p>'
            )
        elif ru and not en:
            parts.append(
                f'<p class="cell-summary lang-block lang-en lang-ru">{self._esc(ru)}</p>'
            )
        return "".join(parts)

    def to_html(
        self,
        evaluation: ProjectEvaluation,
        *,
        summary: str = "",
        summary_ru: str = "",
    ) -> str:
        blocks: list[str] = []
        summary_html = self._summary_blocks(summary, summary_ru)
        if summary_html:
            blocks.append(summary_html)
        actionable = evaluation.actionable_evidence()
        seen: set[str] = set()
        if actionable:
            lines = [self.format_evidence_line(e) for e in actionable]
            seen = {line.lower() for line in lines}
            items = "".join(f"<li>{line}</li>" for line in lines)
            blocks.append(f'<ul class="cell-bullets evidence-bullets">{items}</ul>')
        bullets = evaluation.confidence_bullets
        if bullets:
            unique = []
            for b in bullets[:8]:
                key = b.strip().lower()
                if not key or key in seen:
                    continue
                seen.add(key)
                unique.append(format_bullet_text(b))
            if unique:
                note_items = "".join(f"<li>{self._esc(b[: self._max_bullet])}</li>" for b in unique)
                blocks.append(f'<ul class="cell-bullets">{note_items}</ul>')
        if evaluation.display_fit_label:
            blocks.append(f'<span class="badge badge-muted">{self._esc(evaluation.display_fit_label)}</span>')
        return "".join(blocks) if blocks else '<span class="cell-empty">—</span>'

    @staticmethod
    def legacy_html() -> str:
        """Safe placeholder when stored evaluation cannot be parsed."""
        return '<span class="badge badge-muted" data-i18n="legacy_rescan"></span>'

    def to_markdown(self, evaluation: ProjectEvaluation, *, summary: str = "") -> str:
        lines: list[str] = []
        if summary.strip():
            lines.append(summary.strip()[: self._max_summary])
        for ev in evaluation.actionable_evidence():
            lines.append(f"- {self.format_evidence_line(ev)}")
        for b in evaluation.confidence_bullets[:8]:
            lines.append(f"- {b}")
        if evaluation.display_fit_label:
            lines.append(f"**{evaluation.display_fit_label}**")
        return "\n".join(lines) if lines else "—"

    def fit_badge_html(
        self,
        evaluation: ProjectEvaluation,
        *,
        fit: str = "",
    ) -> str:
        label = evaluation.display_fit_label or (f"LLM {fit}" if fit else "")
        if not label:
            return ""
        return f'<span class="badge badge-muted">{self._esc(label)}</span>'
