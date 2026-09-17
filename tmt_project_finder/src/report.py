from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.utils import load_config, resolve_path

CLASSIFICATIONS = (
    "high_priority_check",
    "medium_priority_check",
    "manual_check",
    "reject",
    "duplicate",
    "rejected_previously_removed",
)


def _count_by_class(records: list[dict]) -> dict[str, int]:
    counts = {c: 0 for c in CLASSIFICATIONS}
    for r in records:
        cls = r.get("classification", "")
        if cls in counts:
            counts[cls] += 1
    return counts


def generate_report(
    records: list[dict],
    *,
    errors: list[str] | None = None,
    warnings: list[str] | None = None,
    sources_run: list[str] | None = None,
    cfg: dict | None = None,
) -> tuple[Path, Path]:
    cfg = cfg or load_config()
    outputs = cfg.get("outputs") or {}
    report_path = resolve_path(outputs.get("report", "outputs/report.md"))
    log_path = resolve_path(outputs.get("log", "outputs/search_log.json"))
    report_path.parent.mkdir(parents=True, exist_ok=True)

    counts = _count_by_class(records)
    errors = errors or []
    warnings = warnings or []
    generated = datetime.now(timezone.utc).isoformat()

    lines = [
        "# TMT Project Finder — Report",
        "",
        f"Generated: {generated}",
        "",
        "## Summary",
        "",
        f"- Total found: **{len(records)}**",
        f"- High priority: **{counts['high_priority_check']}**",
        f"- Medium priority: **{counts['medium_priority_check']}**",
        f"- Manual check: **{counts['manual_check']}**",
        f"- Rejected: **{counts['reject']}**",
        f"- Duplicates: **{counts['duplicate']}**",
        f"- Previously removed: **{counts['rejected_previously_removed']}**",
        "",
        "## Errors",
        "",
    ]
    if errors:
        lines.extend(f"- {e}" for e in errors)
    else:
        lines.append("- None")

    lines.extend(["", "## Warnings", ""])
    if warnings:
        lines.extend(f"- {w}" for w in warnings)
    else:
        lines.append("- None")

    lines.extend(["", "## Sources", ""])
    if sources_run:
        lines.extend(f"- {s}" for s in sources_run)
    else:
        lines.append("- (not recorded)")

    lines.extend([
        "",
        "## Policy",
        "",
        "- `project of Proteomics.xlsx` is read-only",
        "- Result files / protein matrices are not downloaded",
        "",
    ])

    report_path.write_text("\n".join(lines), encoding="utf-8")

    log = {
        "generated_at": generated,
        "total_found": len(records),
        "counts": {
            "high_priority": counts["high_priority_check"],
            "medium_priority": counts["medium_priority_check"],
            "manual_check": counts["manual_check"],
            "rejected": counts["reject"],
            "duplicates": counts["duplicate"],
            "previously_removed": counts["rejected_previously_removed"],
        },
        "errors": errors,
        "warnings": warnings,
        "sources_run": sources_run or [],
    }
    log_path.write_text(json.dumps(log, ensure_ascii=False, indent=2), encoding="utf-8")

    return report_path, log_path
