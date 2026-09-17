#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from atlas_agent.config import load_config
from atlas_agent.discovery.data_availability import annotate_data_availability, summarize_availability
from atlas_agent.discovery.history import save_scan
from atlas_agent.viz.publish_site import publish_discovery_site


def main() -> int:
    cfg = load_config()
    latest = ROOT / "data" / "discovery_history" / "latest.json"
    if not latest.is_file():
        print("No latest.json — run: python run_discovery.py scan")
        return 1

    report = json.loads(latest.read_text(encoding="utf-8"))
    tmt_root = (cfg.get("paths") or {}).get("tmt_projects_dir") or ""

    for key in ("candidates", "manual_check", "rejected_material"):
        items = report.get(key) or []
        if items:
            print(f"Checking {key}: {len(items)} ...")
            annotate_data_availability(items, tmt_root=tmt_root, fetch_remote=True, delay_s=0.12)

    summary = summarize_availability(
        (report.get("candidates") or report.get("new_projects") or [])
        + (report.get("manual_check") or [])
    )
    report.setdefault("summary", {})["data_availability"] = summary
    if report.get("new_projects") and report.get("candidates"):
        by_acc = {
            (it.get("accession") or it.get("project_accession") or "").upper(): it
            for it in report["candidates"]
        }
        for it in report["new_projects"]:
            acc = (it.get("accession") or it.get("project_accession") or "").upper()
            if acc in by_acc and by_acc[acc].get("data_availability"):
                it["data_availability"] = by_acc[acc]["data_availability"]

    out_md = ROOT / "reports" / "data_availability_audit.md"
    out_md.parent.mkdir(parents=True, exist_ok=True)
    lines = ["# Data availability audit", "", "## Summary", ""]
    for st, n in sorted(summary.items(), key=lambda x: -x[1]):
        lines.append(f"- **{st}:** {n}")
    lines.extend(["", "## Candidates", ""])
    for it in (report.get("candidates") or [])[:50]:
        da = it.get("data_availability") or {}
        acc = it.get("accession") or "?"
        lines.append(
            f"- **{acc}** [{da.get('status', '?')}] "
            f"{', '.join((da.get('quant_files') or da.get('sample_files') or [])[:2])}"
        )
    out_md.write_text("\n".join(lines) + "\n", encoding="utf-8")

    save_scan(report, ROOT)
    publish_discovery_site(report, ROOT)
    print(f"Summary: {summary}")
    print(f"Report: {out_md}")
    print(f"Site: {ROOT / 'docs' / 'site' / 'discovery.html'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
