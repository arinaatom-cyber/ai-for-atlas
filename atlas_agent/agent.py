from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from atlas_agent.analysis.dependencies import (
    column_coverage,
    dependency_rules,
    normalization_landscape,
)
from atlas_agent.analysis.result_files import audit_local_files
from atlas_agent.analysis.stats_advisor import recommend_stats
from atlas_agent.config import load_config
from atlas_agent.sources.literature import fetch_abstract, text_mentions_normalization
from atlas_agent.sources.pride import fetch_project, search_human_tmt_projects
from atlas_agent.llm_client import analyze_report, ask_about_project, is_llm_available, resolve_engine
from atlas_agent.sources.projects_table import load_projects_table, primary_project_id


class AtlasAgent:
    """ИИ-агент: таблица → правила Python → интерпретация Claude → отчёт."""

    def __init__(self, config_path: str | None = None):
        self.cfg = load_config(config_path)
        sheet_cfg = self.cfg.get("sheet") or {}
        self.df = load_projects_table(sheet_cfg.get("projects_csv"))
        paths = self.cfg.get("paths") or {}
        self.tmt_root = paths.get("tmt_projects_dir") or ""
        self.reports_dir = Path(paths.get("reports_dir") or Path(__file__).parents[1] / "reports")
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        llm_cfg = self.cfg.get("llm") or self.cfg.get("claude") or {}
        self.llm_provider = llm_cfg.get("provider") or "auto"
        self.llm_model = llm_cfg.get("model")
        self.llm_base_url = llm_cfg.get("base_url")
        self.gpt4all_model = llm_cfg.get("gpt4all_model")
        self.llm_max_tokens = int(llm_cfg.get("max_tokens") or 2048)
        self.ai_enabled = bool(llm_cfg.get("enabled", True))
        # совместимость
        self.claude_model = self.llm_model
        self.claude_enabled = self.ai_enabled

    def run_full(
        self,
        validate_limit: int = 25,
        file_audit_limit: int = 20,
        pride_scan: bool = True,
        use_claude: bool = True,
    ) -> dict:
        df = self.df
        known_pids = {primary_project_id(str(x)) for x in df["Project ID"] if pd.notna(x)}

        report = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "summary": {
                "total_projects": int(len(df)),
                "databases": df["Database"].value_counts().to_dict() if "Database" in df.columns else {},
                "tmt_projects": int(
                    df["TMT Label (Unified)"].astype(str).str.contains("TMT", case=False, na=False).sum()
                )
                if "TMT Label (Unified)" in df.columns
                else 0,
            },
            "column_coverage": column_coverage(df),
            "dependency_rules": dependency_rules(df),
            "normalization_landscape": normalization_landscape(df),
            "normalization_validation": self._validate_normalization(df, limit=validate_limit),
            "local_file_audit": audit_local_files(df, self.tmt_root, limit=file_audit_limit)
            if self.tmt_root
            else [],
            "stats_recommendations_sample": [
                recommend_stats(df.iloc[i]) for i in range(min(10, len(df)))
            ],
            "github": self.cfg.get("github") or {},
        }

        if pride_scan:
            report["new_pride_candidates"] = self._scan_new_pride(known_pids)

        if self.cfg.get("github"):
            try:
                from atlas_agent.sources.github_analyzer import build_github_integration_report

                report["github_integration"] = build_github_integration_report(self.cfg, df)
            except Exception as e:
                report["github_integration"] = {"error": str(e), "policy": {"mode": "read_only"}}

        if use_claude and self.ai_enabled:
            report["ai_analysis"] = analyze_report(
                report,
                provider=self.llm_provider,
                model=self.llm_model,
                base_url=self.llm_base_url,
                gpt4all_model=self.gpt4all_model,
                max_tokens=self.llm_max_tokens,
                df=self.df,
                use_ai=True,
            )
        else:
            report["ai_analysis"] = {
                "available": False,
                "error": "ИИ отключён (--no-ai)",
            }
        report["claude_analysis"] = report["ai_analysis"]  # совместимость

        return report

    def ask(self, project_id: str, question: str | None = None) -> str:
        pid = primary_project_id(project_id)
        mask = self.df["Project ID"].astype(str).apply(
            lambda x: primary_project_id(x) == pid
        )
        rows = self.df[mask]
        if rows.empty:
            return f"Проект {pid} не найден в data/projects.csv"
        row = rows.iloc[0].to_dict()
        for k, v in row.items():
            if pd.isna(v):
                row[k] = ""
        return ask_about_project(
            row,
            provider=self.llm_provider,
            model=self.llm_model,
            base_url=self.llm_base_url,
            gpt4all_model=self.gpt4all_model,
            question=question,
            max_tokens=min(self.llm_max_tokens, 2048),
        )

    def _validate_normalization(self, df: pd.DataFrame, limit: int) -> list[dict]:
        out = []
        cols_need = ["Project ID", "Normalization Strategy", "PMID"]
        if not all(c in df.columns for c in cols_need):
            return out

        tmt = df[df["TMT Label (Unified)"].astype(str).str.contains("TMT", case=False, na=False)]
        for _, row in tmt.head(limit).iterrows():
            pid = primary_project_id(str(row["Project ID"]))
            norm = str(row.get("Normalization Strategy", "") or "").strip()
            pmid = str(row.get("PMID", "") or "").strip().split(".")[0]

            lit = fetch_abstract(pmid) if pmid else {"found": False, "abstract": "", "title": ""}
            pride = fetch_project(pid) if pid.startswith("PXD") else None
            pride_text = ""
            if pride:
                pride_text = " ".join(
                    str(pride.get(k, "") or "")
                    for k in ("title", "projectDescription", "sampleProcessingProtocol", "dataProcessingProtocol")
                )

            combined = f"{lit.get('title', '')} {lit.get('abstract', '')} {pride_text}"
            check = text_mentions_normalization(combined, norm)

            out.append(
                {
                    "project_id": pid,
                    "normalization_table": norm,
                    "pmid": pmid,
                    "literature_found": lit.get("found", False),
                    "pride_found": pride is not None,
                    "validation": check,
                    "title": lit.get("title") or (pride or {}).get("title", ""),
                }
            )
        return out

    def _scan_new_pride(self, known_pids: set[str]) -> list[dict]:
        scan = self.cfg.get("scan") or {}
        keywords = scan.get("pride_keywords") or ["TMT"]
        max_res = int(scan.get("pride_max_results") or 40)
        year_from = int(scan.get("pride_year_from") or 2020)
        try:
            projects = search_human_tmt_projects(
                keywords, page_size=max_res, year_from=year_from
            )
        except Exception as e:
            return [{"error": str(e)}]

        novel = []
        for p in projects:
            acc = (p.get("accession") or p.get("projectAccession") or "").upper()
            if not acc or acc in known_pids:
                continue
            novel.append(
                {
                    "accession": acc,
                    "title": p.get("title", ""),
                    "submission_date": p.get("submissionDate", ""),
                    "organisms": p.get("organisms", []),
                    "instruments": p.get("instruments", [])[:3] if isinstance(p.get("instruments"), list) else [],
                    "suggested_action": "Добавить строку в data/projects.csv + Result Files в tmt-projects/Projects",
                }
            )
        return novel[:20]

    def save_report(self, report: dict, basename: str = "atlas_agent_report") -> tuple[Path, Path]:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        json_path = self.reports_dir / f"{basename}_{ts}.json"
        md_path = self.reports_dir / f"{basename}_{ts}.md"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        md_path.write_text(self._to_markdown(report), encoding="utf-8")
        return json_path, md_path

    def _to_markdown(self, report: dict) -> str:
        lines = [
            "# Atlas Agent — отчёт",
            "",
            f"Сгенерировано: {report.get('generated_at', '')}",
            "",
            "## Сводка",
            "",
        ]
        s = report.get("summary") or {}
        lines.append(f"- Проектов в таблице: **{s.get('total_projects', 0)}**")
        lines.append(f"- TMT-проектов: **{s.get('tmt_projects', 0)}**")
        lines.append("")

        ca = report.get("ai_analysis") or report.get("claude_analysis") or {}
        engine = ca.get("engine") or ca.get("model") or "ai"
        if ca.get("executive_summary"):
            lines.append(f"## Исполнительное резюме ({engine})")
            lines.append("")
            lines.append(ca["executive_summary"])
            lines.append("")
        if ca.get("normalization_review"):
            lines.append(f"## Анализ нормализации ({engine})")
            lines.append("")
            lines.append(ca["normalization_review"])
            lines.append("")
        if ca.get("action_items"):
            lines.append(f"## Приоритетные действия ({engine})")
            lines.append("")
            for i, item in enumerate(ca["action_items"], 1):
                lines.append(f"{i}. {item}")
            lines.append("")
        if ca.get("projects_needing_manual_review"):
            lines.append("## Ручная проверка проектов")
            lines.append("")
            for p in ca["projects_needing_manual_review"]:
                lines.append(f"- {p}")
            lines.append("")
        elif ca.get("error") and not ca.get("available"):
            lines.append("## Claude")
            lines.append("")
            lines.append(f"_{ca['error']}_")
            lines.append("")

        lines.append("## Зависимости и заполненность колонок")
        lines.append("")
        for group, info in (report.get("column_coverage") or {}).items():
            lines.append(f"### {group}")
            for col, st in (info.get("columns") or {}).items():
                lines.append(f"- `{col}`: {st.get('pct')}% заполнено")
            lines.append("")

        lines.append("## Правила целостности")
        lines.append("")
        for r in report.get("dependency_rules") or []:
            lines.append(
                f"- {r['rule']}: нарушений **{r['violations']}** / {r['scope']}"
            )
        lines.append("")

        lines.append("## Ландшафт нормализации (топ)")
        lines.append("")
        for k, v in list((report.get("normalization_landscape") or {}).items())[:15]:
            lines.append(f"- {k}: {v}")
        lines.append("")

        lines.append("## Проверка нормализации (таблица vs статья/PRIDE)")
        lines.append("")
        for v in report.get("normalization_validation") or []:
            status = (v.get("validation") or {}).get("status", "?")
            lines.append(f"### {v.get('project_id')} — {status}")
            lines.append(f"- Таблица: {v.get('normalization_table', '')[:200]}")
            lines.append(f"- PMID: {v.get('pmid')} | литература: {v.get('literature_found')} | PRIDE: {v.get('pride_found')}")
            note = (v.get("validation") or {}).get("note", "")
            if note:
                lines.append(f"- {note}")
            hits = (v.get("validation") or {}).get("hits") or []
            if hits:
                lines.append(f"- Совпадения: {', '.join(hits[:8])}")
            lines.append("")

        gh = report.get("github_integration") or {}
        cmp = gh.get("comparison") or {}
        if cmp.get("only_on_github"):
            lines.append("## GitHub — PXD нет в таблице")
            lines.append("")
            for p in (cmp.get("only_on_github") or [])[:15]:
                lines.append(f"- {p}")
            lines.append("")

        novel = report.get("new_pride_candidates") or []
        if novel and not novel[0].get("error"):
            lines.append("## Новые похожие проекты в PRIDE (нет в вашей таблице)")
            lines.append("")
            for n in novel:
                lines.append(f"- **{n.get('accession')}** — {n.get('title', '')[:120]}")
                lines.append(f"  - Дата: {n.get('submission_date', '')}")
            lines.append("")

        lines.append("## Примеры рекомендаций по статистике")
        lines.append("")
        for rec in report.get("stats_recommendations_sample") or []:
            lines.append(f"### {rec.get('project_id', '')}")
            for step in rec.get("recommended_steps") or []:
                lines.append(f"- {step}")
            lines.append("")

        gh = report.get("github") or {}
        if gh:
            lines.append("## GitHub")
            lines.append("")
            lines.append(f"- Атлас: {gh.get('atlas_repo', '')}")
            lines.append(f"- Данные: {gh.get('data_repo', '')}")
            lines.append("")

        return "\n".join(lines)
