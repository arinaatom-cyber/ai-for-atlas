from __future__ import annotations

from typing import Any

from atlas_agent.workflow.completeness import audit_table
from atlas_agent.sources.projects_table import load_projects_table
import pandas as pd


def generate_local_analysis(report: dict, df: pd.DataFrame | None = None) -> dict[str, Any]:
    """Локальный «ИИ»-слой без API: резюме и action items по правилам."""
    if df is None:
        df = pd.DataFrame()

    audit = audit_table(df) if len(df) else pd.DataFrame()
    n_complete = int((audit["status"] == "complete").sum()) if len(audit) else 0
    n_partial = int((audit["status"] == "partial").sum()) if len(audit) else 0
    n_todo = int((audit["status"] == "todo").sum()) if len(audit) else 0
    n_rows = len(audit) if len(audit) else report.get("summary", {}).get("total_projects", 0)

    validations = report.get("normalization_validation") or []
    supported = sum(1 for v in validations if (v.get("validation") or {}).get("status") == "supported")
    not_found = sum(1 for v in validations if (v.get("validation") or {}).get("status") == "not_found")

    deps = report.get("dependency_rules") or []
    dep_lines = [f"{d['rule']}: {d['violations']} нарушений из {d['scope']}" for d in deps]

    summary = (
        f"В таблице {n_rows} строк. По unified-полям: готово {n_complete}, частично {n_partial}, "
        f"нужно дочитать {n_todo}. "
        f"Проверено нормализаций (выборка): {len(validations)}; совпало со статьёй/PRIDE: {supported}, "
        f"не найдено явных формулировок: {not_found}."
    )

    actions: list[str] = []
    if n_todo > 0:
        actions.append(f"Дочитать {n_todo} проектов со статусом todo (см. data/workflow_audit.csv)")
    if n_partial > 0:
        actions.append(f"Дописать Quantification_Format / Normalization Strategy у {n_partial} partial-проектов")
    for d in deps:
        if d.get("violations", 0) > 0:
            actions.append(f"Исправить: {d['rule']} ({d['violations']} шт.)")
    if len(audit):
        todo_df = audit[(audit["status"] == "todo") & audit["project_id"].astype(str).str.match(r"^PXD|^PDC|^MSV", na=False)]
        todo_pids = todo_df["project_id"].head(5).tolist()
    else:
        todo_pids = []
    if todo_pids:
        actions.append("Приоритет PXD: " + ", ".join(todo_pids))

    norm_review = "Топ нормализаций в каталоге: " + ", ".join(
        list((report.get("normalization_landscape") or {}).keys())[:5]
    )
    if not_found:
        norm_review += f". В {not_found} проектах из выборки формулировка из таблицы не найдена в abstract — проверить Methods вручную."

    return {
        "available": True,
        "engine": "local_rules",
        "model": "local_analyst",
        "executive_summary": summary,
        "normalization_review": norm_review,
        "action_items": actions[:10],
        "projects_needing_manual_review": todo_pids,
        "dependency_notes": dep_lines,
    }
