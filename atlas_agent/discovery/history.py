"""История еженедельных сканов — без изменения projects.csv."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


def history_dir(base: Path) -> Path:
    d = base / "data" / "discovery_history"
    d.mkdir(parents=True, exist_ok=True)
    return d


def save_scan(payload: dict, base: Path) -> Path:
    d = history_dir(base)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = d / f"scan_{ts}.json"
    payload["saved_at"] = datetime.now(timezone.utc).isoformat()
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    latest = d / "latest.json"
    latest.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
    return path


def load_latest(base: Path) -> dict | None:
    p = history_dir(base) / "latest.json"
    if not p.is_file():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def list_scans(base: Path, limit: int = 20) -> list[dict]:
    d = history_dir(base)
    files = sorted(d.glob("scan_*.json"), reverse=True)[:limit]
    out = []
    for f in files:
        try:
            j = json.loads(f.read_text(encoding="utf-8"))
            out.append(
                {
                    "file": str(f),
                    "generated_at": j.get("generated_at"),
                    "new_projects": j.get("summary", {}).get("new_projects", 0),
                    "novel_count": j.get("summary", {}).get("new_projects", j.get("summary", {}).get("novel_total", 0)),
                }
            )
        except (json.JSONDecodeError, OSError):
            continue
    return out
