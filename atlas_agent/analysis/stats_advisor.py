from __future__ import annotations

import pandas as pd

from atlas_agent.analysis.stats_plan import build_stats_plan


def recommend_stats(row: pd.Series) -> dict:
    """Рекомендация пайплайна статистики по строке таблицы."""
    plan = build_stats_plan(row)
    steps = [
        f"Design: {plan['design_type']} | test: {plan['test']} | level: {plan['patient_level']}",
    ]
    if plan["blocking_factors"]:
        steps.append(f"Blocking factors: {', '.join(plan['blocking_factors'])}")
    steps.append(f"Multiple testing: {plan['multiple_testing']}")
    for w in plan.get("warnings", []):
        steps.append(w)

    notes = []
    if plan.get("normalization_sheet"):
        notes.append(f"Нормализация в таблице: {plan['normalization_sheet'][:120]}")
    else:
        notes.append("Нормализация в таблице не указана — извлечь из статьи/PRIDE.")

    return {
        "project_id": plan["project_id"],
        "recommended_steps": steps,
        "notes": notes,
        "stats_plan": plan,
    }
