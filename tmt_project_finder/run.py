#!/usr/bin/env python3
"""CLI: python run.py"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.pipeline import run_pipeline


def main() -> int:
    result = run_pipeline()
    print(f"Found {result['total']} records")
    counts = result.get("counts") or {}
    for key in (
        "high_priority_check",
        "medium_priority_check",
        "manual_check",
        "reject",
        "duplicate",
        "rejected_previously_removed",
    ):
        print(f"  {key}: {counts.get(key, 0)}")
    if result.get("errors"):
        print("Errors:")
        for err in result["errors"]:
            print(f"  - {err}")
    if result.get("report"):
        print(f"Report: {result['report']}")
    print(json.dumps({"saved": result.get("saved")}, ensure_ascii=False, indent=2))
    return 0 if not result.get("errors") else 1


if __name__ == "__main__":
    raise SystemExit(main())
