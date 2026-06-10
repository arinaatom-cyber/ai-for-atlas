#!/usr/bin/env python3
"""sessionStart: inject Discovery scan status into agent context."""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LATEST = ROOT / "data" / "discovery_history" / "latest.json"
HTML = ROOT / "reports" / "discovery_index.html"


def main() -> int:
    try:
        json.load(sys.stdin)
    except json.JSONDecodeError:
        pass

    lines = ["## Atlas Discovery status"]

    if not LATEST.is_file():
        lines.append("- No scan yet. Run: `python run_discovery.py scan`")
    else:
        try:
            data = json.loads(LATEST.read_text(encoding="utf-8"))
            gen = data.get("generated_at", "")
            s = data.get("summary") or {}
            n = s.get("new_projects", len(data.get("new_projects") or []))
            stats = s.get("source_stats") or {}
            age_days = None
            if gen:
                dt = datetime.fromisoformat(gen.replace("Z", "+00:00"))
                age_days = (datetime.now(timezone.utc) - dt).days
            lines.append(f"- Last scan: {gen[:19]} UTC · **{n}** new projects")
            if stats:
                lines.append(
                    f"- Sources: PRIDE {stats.get('pride_v3_search', 0)} · "
                    f"PDC {stats.get('pdc_uiStudySummary', 0)} · "
                    f"papers {stats.get('literature_resolved', 0)}"
                )
            if HTML.is_file():
                lines.append(f"- Website: `reports/discovery_index.html`")
            if age_days is not None and age_days >= 7:
                lines.append(
                    f"- Scan is **{age_days} days** old — consider `python run_discovery.py scan`"
                )
        except (json.JSONDecodeError, OSError, ValueError):
            lines.append("- Could not read latest.json")

    out = {"additional_context": "\n".join(lines)}
    sys.stdout.write(json.dumps(out, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
