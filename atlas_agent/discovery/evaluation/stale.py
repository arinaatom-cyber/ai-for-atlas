from __future__ import annotations

from typing import Any

from atlas_agent.discovery.evaluation.schemas import ItemKind


def _kind_value(kind: ItemKind | str) -> str:
    return kind.value if isinstance(kind, ItemKind) else str(kind).lower()


def is_stale_project_evaluation(item: dict[str, Any], stored: dict[str, Any] | None = None) -> bool:
    ev = stored if stored is not None else item.get("evaluation")
    if not ev or not isinstance(ev, dict):
        return False
    da = item.get("data_availability") or {}
    status = str(da.get("status") or "")
    if not status:
        return False
    bullets = [str(b) for b in (ev.get("confidence_bullets") or [])]
    confidence = str(ev.get("confidence") or "")
    verdict = str(ev.get("final_verdict") or "")
    if bullets == ["Literature surveillance"]:
        return True
    if status == "quant_table" and confidence in ("C", "D") and verdict == "Watch":
        if not any("Protein" in b or "Quant" in b or "TMT" in b for b in bullets):
            return True
    if status == "quant_table" and verdict != "Candidate" and item.get("qc_status") == "candidate":
        return True
    return False


def should_recompute_evaluation(item: dict[str, Any], kind: ItemKind | str) -> bool:
    if not item.get("evaluation") or not item.get("confidence_tier"):
        return True
    if _kind_value(kind) == ItemKind.PROJECT.value:
        return is_stale_project_evaluation(item)
    return False
