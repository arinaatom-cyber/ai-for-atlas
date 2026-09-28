from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from atlas_agent.discovery.fit_rules import project_verdict
from atlas_agent.viz.display_format import clean_taxonomy_value

CELL_LINE_SIGNALS = frozenset({"human_cancer_cell_line"})
TISSUE_SIGNALS = frozenset(
    {
        "human_tumor_tissue",
        "normal_adjacent",
        "human_tissue",
        "clinical_human",
        "pdc_clinical_tumor",
    }
)
_STUB_SITE = frozenset({"", "nan", "none", "—", "-", "not reported", "other", "unknown", "n/a"})


def _accession(item: dict[str, Any]) -> str:
    return str(item.get("accession") or item.get("project_accession") or "").strip().upper()


def _included_signals(item: dict[str, Any]) -> set[str]:
    sig = item.get("material_signals") or {}
    return {str(x).strip().lower() for x in (sig.get("included") or []) if str(x).strip()}


def _looks_like_cell_line(item: dict[str, Any]) -> bool:
    if _included_signals(item) & CELL_LINE_SIGNALS:
        return True
    blob = " ".join(
        str(item.get(k) or "")
        for k in ("title", "description", "abstract", "abstract_snippet", "experiment_type")
    ).lower()
    ai = item.get("abstract_ai") or {}
    blob += " " + str(ai.get("material") or "").lower()
    return "cell line" in blob or "cell-line" in blob


def _explicit_primary_site(item: dict[str, Any]) -> str:
    raw = item.get("primary_site")
    if raw is None or (isinstance(raw, float) and raw != raw):
        return ""
    cleaned = clean_taxonomy_value(raw)
    if cleaned and cleaned.strip().lower() not in _STUB_SITE:
        return cleaned
    text = str(raw or "").strip()
    if text.lower() in _STUB_SITE:
        return ""
    return text


def classify_accepted_material(item: dict[str, Any]) -> str:
    """Exclusive bucket for an accepted project: cell_line | primary_site | tissue."""
    if _looks_like_cell_line(item):
        return "cell_line"
    if _explicit_primary_site(item):
        return "primary_site"
    included = _included_signals(item)
    if included & TISSUE_SIGNALS:
        return "tissue"
    return "tissue"


def passed_candidates(report: dict[str, Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for it in report.get("candidates") or report.get("new_projects") or []:
        if project_verdict(it)[0] != "Candidate":
            continue
        key = _accession(it) or f"row:{len(out)}"
        if key in seen:
            continue
        seen.add(key)
        out.append(it)
    return out


def _count_unique(items: list[dict[str, Any]]) -> int:
    seen: set[str] = set()
    n_empty = 0
    for it in items:
        acc = _accession(it)
        if acc:
            seen.add(acc)
        else:
            n_empty += 1
    return len(seen) + n_empty


def _checked_from_arrays(report: dict[str, Any]) -> int:
    buckets: list[dict[str, Any]] = []
    seen: set[str] = set()
    n = 0
    for key in (
        "candidates",
        "new_projects",
        "repository_manual",
        "rejected_material",
        "filtered_out",
    ):
        for it in report.get(key) or []:
            acc = _accession(it)
            if acc:
                if acc in seen:
                    continue
                seen.add(acc)
            n += 1
            buckets.append(it)
    return n if n else _count_unique(buckets)


def _checked_from_summary(summary: dict[str, Any]) -> int:
    novel = int(summary.get("novel_total") or 0)
    if novel:
        return novel
    parts = (
        int(summary.get("candidates") or summary.get("new_projects") or 0)
        + int(summary.get("repository_manual") or 0)
        + int(summary.get("rejected_material") or 0)
        + int(summary.get("filtered_out") or 0)
        + int(summary.get("already_in_catalog") or 0)
    )
    return parts


def _history_unique_accessions(history: Path) -> int:
    seen: set[str] = set()
    files = sorted(history.glob("scan_*.json"))
    latest = history / "latest.json"
    if latest.is_file():
        files.append(latest)
    for path in files:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        for key in (
            "candidates",
            "new_projects",
            "repository_manual",
            "rejected_material",
            "filtered_out",
        ):
            for it in payload.get(key) or []:
                acc = _accession(it)
                if acc:
                    seen.add(acc)
        summary = payload.get("summary") or {}
        novel = int(summary.get("novel_total") or 0)
        if novel and not payload.get("filtered_out") and not payload.get("rejected_material"):
            # summary-only snapshot: keep the largest corpus size
            seen.add(f"__novel__{path.name}__{novel}")
    real = {x for x in seen if not x.startswith("__novel__")}
    if real:
        return len(real)
    novels = [int(x.rsplit("__", 1)[-1]) for x in seen if x.startswith("__novel__")]
    return max(novels) if novels else 0


def summarize_report(report: dict[str, Any], *, root: Path | None = None) -> dict[str, int]:
    """Counts shared by Discovery and QC. accepted = Candidate only."""
    summary = report.get("summary") or {}
    accepted_items = passed_candidates(report)
    buckets = {"cell_line": 0, "tissue": 0, "primary_site": 0}
    for it in accepted_items:
        buckets[classify_accepted_material(it)] += 1

    checked = _checked_from_summary(summary)
    if not checked:
        checked = _checked_from_arrays(report)
    if root is not None:
        hist = Path(root) / "data" / "discovery_history"
        hist_n = _history_unique_accessions(hist) if hist.is_dir() else 0
        if hist_n > checked:
            checked = hist_n

    return {
        "checked": checked,
        "accepted": len(accepted_items),
        "cell_line": buckets["cell_line"],
        "tissue": buckets["tissue"],
        "primary_site": buckets["primary_site"],
    }
