#!/usr/bin/env python3
"""End-to-end проверка AI-оценки всех находок Discovery (evaluation pipeline)."""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

REPORT_PATH = ROOT / "reports" / "ai_findings_verify.md"

_BUCKETS: tuple[tuple[str, str], ...] = (
    ("candidates", "project"),
    ("new_projects", "project"),
    ("manual_check", "literature"),
    ("literature_semantic", "literature"),
    ("cohort_literature", "cohort"),
    ("rejected_material", "literature"),
)


def ok(msg: str) -> None:
    print(f"  OK  {msg}")


def warn(msg: str) -> None:
    print(f"  WARN {msg}")


def fail(msg: str) -> None:
    print(f"  FAIL {msg}")
    raise SystemExit(1)


def _item_id(item: dict) -> str:
    return str(
        item.get("accession")
        or item.get("project_accession")
        or item.get("pmid")
        or item.get("title", "")[:40]
        or "?"
    )


def load_report(*, reevaluate: bool = False) -> dict:
    from atlas_agent.config import load_config
    from atlas_agent.discovery.evaluation.report import evaluate_discovery_report_from_config

    latest = ROOT / "data" / "discovery_history" / "latest.json"
    if not latest.is_file():
        fail("missing data/discovery_history/latest.json — run: python run_discovery.py scan")

    report = json.loads(latest.read_text(encoding="utf-8"))
    cfg = load_config()

    missing = sum(
        1
        for key, _ in _BUCKETS
        for item in (report.get(key) or [])
        if not item.get("evaluation")
    )
    if reevaluate or missing:
        print(f"  … running EvaluationPipeline ({missing} items without evaluation)")
        evaluate_discovery_report_from_config(report, cfg)
        latest.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        ok(f"evaluation attached; saved {latest.name}")
    return report


def audit_evaluations(report: dict) -> dict:
    from atlas_agent.discovery.evaluation.schemas import ItemKind

    kind_map = {
        "project": ItemKind.PROJECT,
        "literature": ItemKind.LITERATURE,
        "cohort": ItemKind.COHORT,
    }

    stats: dict = {
        "total": 0,
        "with_evaluation": 0,
        "missing": [],
        "tiers": Counter(),
        "verdicts": Counter(),
        "review_flags": 0,
        "buckets": {},
    }

    seen_ids: set[tuple[str, str]] = set()
    for key, kind_name in _BUCKETS:
        items = report.get(key) or []
        bucket = {"n": len(items), "evaluated": 0, "missing": []}
        for item in items:
            iid = _item_id(item)
            dedupe = (key, iid)
            if dedupe in seen_ids:
                continue
            seen_ids.add(dedupe)
            stats["total"] += 1
            ev = item.get("evaluation")
            if not ev:
                stats["missing"].append(f"{key}:{iid}")
                bucket["missing"].append(iid)
                continue
            stats["with_evaluation"] += 1
            bucket["evaluated"] += 1
            stats["tiers"][str(ev.get("confidence") or "?")] += 1
            stats["verdicts"][str(ev.get("final_verdict") or "?")] += 1
            if item.get("requires_manual_review") or ev.get("requires_manual_review"):
                stats["review_flags"] += 1
            # schema sanity
            if not ev.get("confidence_bullets"):
                warn(f"{key}:{iid} — evaluation without confidence_bullets")
            _ = kind_map.get(kind_name)  # reserved for future strict kind checks
        stats["buckets"][key] = bucket
    return stats


def check_candidates(report: dict) -> None:
    cands = report.get("candidates") or report.get("new_projects") or []
    if not cands:
        warn("no project candidates in latest scan")
        return
    for c in cands:
        acc = str(c.get("accession") or c.get("project_accession") or "").upper()
        if not acc.startswith(("PXD", "PDC", "MSV", "IPX")):
            warn(f"candidate without repo ID: {_item_id(c)}")
        ev = c.get("evaluation") or {}
        if ev.get("final_verdict") == "exclude":
            warn(f"candidate marked exclude by AI: {acc} — {ev.get('confidence_bullets', [''])[0]}")
    ok(f"{len(cands)} candidates audited")


def write_report_md(report: dict, stats: dict) -> None:
    lines = [
        "# AI findings verification",
        "",
        f"Scan: `{report.get('generated_at', '')}`",
        "",
        "## Coverage",
        f"- Items checked: **{stats['total']}**",
        f"- With `evaluation`: **{stats['with_evaluation']}**",
        f"- Missing evaluation: **{len(stats['missing'])}**",
        f"- Manual review flags: **{stats['review_flags']}**",
        "",
        "## Confidence tiers",
    ]
    for tier, n in sorted(stats["tiers"].items()):
        lines.append(f"- `{tier}`: {n}")
    lines.extend(["", "## Final verdicts"])
    for v, n in sorted(stats["verdicts"].items()):
        lines.append(f"- `{v}`: {n}")
    lines.extend(["", "## Buckets"])
    for key, b in stats["buckets"].items():
        lines.append(f"- `{key}`: {b['evaluated']}/{b['n']} evaluated")
        if b["missing"]:
            lines.append(f"  - missing: {', '.join(b['missing'][:8])}")
    lines.extend(
        [
            "",
            "## Candidates (top)",
            "",
        ]
    )
    for c in (report.get("candidates") or [])[:10]:
        ev = c.get("evaluation") or {}
        lines.append(
            f"- `{c.get('accession')}` tier **{ev.get('confidence', '?')}** "
            f"verdict `{ev.get('final_verdict', '?')}` — "
            f"{(ev.get('confidence_bullets') or [''])[0]}"
        )
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    import argparse

    ap = argparse.ArgumentParser(description="Verify AI evaluation on all discovery findings")
    ap.add_argument("--reevaluate", action="store_true", help="Re-run EvaluationPipeline and save latest.json")
    args = ap.parse_args()

    print("=== AI findings verification ===\n")
    report = load_report(reevaluate=args.reevaluate)
    stats = audit_evaluations(report)

    print("\n1. Evaluation coverage")
    if stats["missing"]:
        fail(f"{len(stats['missing'])} items without evaluation: {stats['missing'][:5]}")
    ok(f"{stats['with_evaluation']}/{stats['total']} items have evaluation")
    ok(f"tiers: {dict(stats['tiers'])}")
    ok(f"verdicts: {dict(stats['verdicts'])}")

    print("\n2. Project candidates")
    check_candidates(report)

    print("\n3. Quality metrics")
    qm = (report.get("summary") or {}).get("quality_metrics") or report.get("quality_metrics")
    if qm:
        ok(f"benchmark_literature: {qm.get('benchmark_literature')}")
        ok(f"benchmark_projects: {qm.get('benchmark_projects')}")
    else:
        warn("quality_metrics missing — run: python scripts/enrich_and_publish_site.py")

    write_report_md(report, stats)
    print(f"\nReport: {REPORT_PATH}")
    print("\n=== AI verification passed ===")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
