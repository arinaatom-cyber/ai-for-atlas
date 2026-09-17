from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.classify_projects import classify_all
from src.deleted_check import load_deleted_database
from src.duplicate_check import load_database
from src.parse_sources import normalize_record
from src.report import generate_report
from src.save_outputs import save_outputs
from src.search_sources import run_all_searches
from src.utils import load_config


def run_pipeline(cfg: dict | None = None) -> dict[str, Any]:
    cfg = cfg or load_config()
    raw, errors, warnings = run_all_searches(cfg)

    seen: set[str] = set()
    normalized: list[dict] = []
    for r in raw:
        rec = normalize_record(r)
        key = rec.get("project_id") or rec.get("pmid") or rec.get("doi") or rec.get("title", "")[:80]
        if key in seen:
            continue
        seen.add(key)
        normalized.append(rec)

    db = load_database()
    deleted_db = load_deleted_database()
    classified = classify_all(normalized, database=db, deleted_database=deleted_db)

    saved = save_outputs(classified, cfg)
    sources = [k for k, v in (cfg.get("sources") or {}).items() if v]
    report_path, log_path = generate_report(
        classified,
        errors=errors,
        warnings=warnings,
        sources_run=sources,
        cfg=cfg,
    )

    counts = {}
    for r in classified:
        c = r.get("classification", "unknown")
        counts[c] = counts.get(c, 0) + 1

    return {
        "records": classified,
        "counts": counts,
        "total": len(classified),
        "saved": {k: str(v) for k, v in saved.items()},
        "report": str(report_path),
        "log": str(log_path),
        "errors": errors,
        "warnings": warnings,
    }
