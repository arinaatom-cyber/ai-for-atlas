#!/usr/bin/env python3
"""CLI: опубликовать Discovery на docs/site/ (только новые проекты)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from atlas_agent.viz.publish_site import publish_discovery_site


def main() -> int:
    latest = ROOT / "data" / "discovery_history" / "latest.json"
    report = json.loads(latest.read_text(encoding="utf-8")) if latest.is_file() else {}
    site = publish_discovery_site(report, ROOT)
    print(f"Site: {site}")
    print(f"  discovery.html — {len(report.get('candidates') or report.get('new_projects') or [])} новых")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
