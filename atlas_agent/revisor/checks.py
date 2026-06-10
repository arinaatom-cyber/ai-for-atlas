"""Проверки целостности таблицы projects.csv и локальных файлов."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import pandas as pd

from atlas_agent.sources.projects_table import PID_RE, primary_project_id
from atlas_agent.workflow.completeness import UNIFIED_COLUMNS, _empty, row_completeness

PMID_RE = re.compile(r"^\d{5,9}$")


class Severity(str, Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class Finding:
    severity: Severity
    code: str
    message: str
    project_id: str = ""
    row_index: int | None = None
    column: str = ""
    auto_fixable: bool = False
    fix_hint: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "severity": self.severity.value,
            "code": self.code,
            "message": self.message,
            "project_id": self.project_id,
            "row_index": self.row_index,
            "column": self.column,
            "auto_fixable": self.auto_fixable,
            "fix_hint": self.fix_hint,
        }


@dataclass
class AuditResult:
    findings: list[Finding] = field(default_factory=list)
    stats: dict[str, Any] = field(default_factory=dict)

    def add(self, f: Finding) -> None:
        self.findings.append(f)

    def by_severity(self) -> dict[str, int]:
        out = {s.value: 0 for s in Severity}
        for f in self.findings:
            out[f.severity.value] += 1
        return out

    def to_dict(self) -> dict:
        return {
            "stats": self.stats,
            "counts": self.by_severity(),
            "findings": [f.to_dict() for f in self.findings],
        }


def _normalize_pmid_cell(val: Any) -> str:
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return ""
    s = str(val).strip()
    if s.endswith(".0") and s[:-2].isdigit():
        s = s[:-2]
    return re.sub(r"\D", "", s)


def audit_table_rows(df: pd.DataFrame) -> AuditResult:
    result = AuditResult()
    n = len(df)
    result.stats["total_rows"] = n

    if "Project ID" not in df.columns:
        result.add(
            Finding(
                Severity.ERROR,
                "missing_column",
                "Нет колонки Project ID",
            )
        )
        return result

    primary_ids: list[str] = []
    empty_rows = 0
    for idx, row in df.iterrows():
        raw_pid = row.get("Project ID")
        if _empty(raw_pid):
            empty_rows += 1
            result.add(
                Finding(
                    Severity.WARNING,
                    "empty_project_id",
                    "Строка без Project ID",
                    row_index=int(idx),
                    auto_fixable=False,
                )
            )
            continue

        pid = primary_project_id(str(raw_pid))
        primary_ids.append(pid)

        if str(raw_pid).strip() != str(raw_pid):
            result.add(
                Finding(
                    Severity.INFO,
                    "whitespace_project_id",
                    "Лишние пробелы в Project ID",
                    project_id=pid,
                    row_index=int(idx),
                    column="Project ID",
                    auto_fixable=True,
                    fix_hint="strip",
                )
            )

        if pid and not PID_RE.search(str(raw_pid)):
            result.add(
                Finding(
                    Severity.WARNING,
                    "unrecognized_accession",
                    f"ID не похож на PXD/PDC: {raw_pid}",
                    project_id=pid,
                    row_index=int(idx),
                )
            )

        comp = row_completeness(row)
        if comp["status"] == "todo":
            result.add(
                Finding(
                    Severity.ERROR,
                    "incomplete_unified",
                    f"Критически пустые Unified: {', '.join(comp['missing_unified'][:5])}",
                    project_id=pid,
                    row_index=int(idx),
                )
            )
        elif comp["status"] == "partial":
            miss = comp["missing_unified"]
            if miss:
                result.add(
                    Finding(
                        Severity.WARNING,
                        "partial_unified",
                        f"Не заполнено: {', '.join(miss)}",
                        project_id=pid,
                        row_index=int(idx),
                    )
                )

        if "TMT Label (Unified)" in row.index:
            is_tmt = "tmt" in str(row.get("TMT Label (Unified)", "")).lower()
            if is_tmt:
                if _empty(row.get("Normalization Strategy")):
                    result.add(
                        Finding(
                            Severity.ERROR,
                            "tmt_no_normalization",
                            "TMT без Normalization Strategy",
                            project_id=pid,
                            row_index=int(idx),
                            column="Normalization Strategy",
                        )
                    )
                if _empty(row.get("Result Files")):
                    result.add(
                        Finding(
                            Severity.ERROR,
                            "tmt_no_result_file",
                            "TMT без Result Files",
                            project_id=pid,
                            row_index=int(idx),
                            column="Result Files",
                        )
                    )

        if "PMID" in row.index and not _empty(row.get("PMID")):
            pmid = _normalize_pmid_cell(row.get("PMID"))
            if pmid and not PMID_RE.match(pmid):
                result.add(
                    Finding(
                        Severity.WARNING,
                        "invalid_pmid",
                        f"PMID некорректен: {row.get('PMID')}",
                        project_id=pid,
                        row_index=int(idx),
                        column="PMID",
                        auto_fixable=True,
                        fix_hint="normalize_pmid",
                    )
                )
            elif str(row.get("PMID", "")).strip() != pmid and pmid:
                result.add(
                    Finding(
                        Severity.INFO,
                        "pmid_format",
                        f"PMID лучше записать как {pmid}",
                        project_id=pid,
                        row_index=int(idx),
                        column="PMID",
                        auto_fixable=True,
                        fix_hint="normalize_pmid",
                    )
                )

    result.stats["empty_project_rows"] = empty_rows
    result.stats["rows_with_id"] = n - empty_rows

    from collections import Counter

    c = Counter(primary_ids)
    dup = {k: v for k, v in c.items() if k and v > 1}
    result.stats["unique_primary_ids"] = len(c)
    result.stats["duplicate_primary_ids"] = len(dup)
    for pid, count in sorted(dup.items(), key=lambda x: -x[1])[:30]:
        result.add(
            Finding(
                Severity.WARNING,
                "duplicate_primary_id",
                f"Проект {pid} встречается {count} раз (варианты строк)",
                project_id=pid,
            )
        )

    return result


def audit_local_paths(df: pd.DataFrame, tmt_root: str, limit: int = 0) -> list[Finding]:
    from pathlib import Path

    from atlas_agent.analysis.result_files import first_result_file

    findings: list[Finding] = []
    root = Path(tmt_root)
    if not tmt_root or not root.is_dir():
        findings.append(
            Finding(
                Severity.WARNING,
                "tmt_root_missing",
                f"Папка tmt-projects не найдена: {tmt_root}",
            )
        )
        return findings

    subset = df if not limit else df.head(limit)
    for idx, row in subset.iterrows():
        if _empty(row.get("Project ID")):
            continue
        pid = primary_project_id(str(row["Project ID"]))
        folder = root / pid
        if not folder.is_dir():
            findings.append(
                Finding(
                    Severity.WARNING,
                    "missing_project_folder",
                    f"Нет папки Projects/{pid}",
                    project_id=pid,
                    row_index=int(idx),
                )
            )
            continue
        rf = first_result_file(str(row.get("Result Files", "")))
        if rf:
            matches = [
                p.name
                for p in folder.iterdir()
                if p.is_file() and rf.lower() in p.name.lower()
            ]
            if not matches:
                ex = folder / "_extracted"
                if ex.is_dir():
                    matches = [
                        p.name
                        for p in ex.rglob("*")
                        if p.is_file() and rf.lower() in p.name.lower()
                    ]
            if not matches:
                findings.append(
                    Finding(
                        Severity.WARNING,
                        "result_file_not_on_disk",
                        f"В таблице '{rf}', на диске не найден",
                        project_id=pid,
                        row_index=int(idx),
                        column="Result Files",
                    )
                )
    return findings


def run_full_audit(
    df: pd.DataFrame,
    *,
    tmt_root: str = "",
    file_check_limit: int = 50,
) -> AuditResult:
    result = audit_table_rows(df)
    if tmt_root:
        for f in audit_local_paths(df, tmt_root, limit=file_check_limit or len(df)):
            result.add(f)
    result.stats["finding_counts"] = result.by_severity()
    return result
