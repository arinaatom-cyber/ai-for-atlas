#!/usr/bin/env python3
"""
Discovery Agent — поиск похожих проектов и статей (PRIDE, PDC, CCLE, GTEx, CPTAC).

ВАЖНО: data/projects.csv только ЧИТАЕТСЯ. Удаление и авто-изменение ЗАПРЕЩЕНЫ.

  python run_discovery.py policy     # правила
  python run_discovery.py scan       # полный поиск + отчёт
  python run_discovery.py latest     # последний отчёт
  python run_discovery.py history    # история еженедельных сканов
  python run_discovery.py profile    # профиль вашего атласа

Еженедельно (Task Scheduler / cron):
  python run_discovery.py scan
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from atlas_agent.config import load_config
from atlas_agent.discovery.agent import run_discovery_scan
from atlas_agent.discovery.catalog_profile import build_catalog_profile
from atlas_agent.discovery.history import list_scans, load_latest
from atlas_agent.discovery.policy import policy_summary
from atlas_agent.discovery.agent import load_catalog_readonly

ROOT = Path(__file__).parent


def cmd_policy(_args: argparse.Namespace) -> int:
    print(json.dumps(policy_summary(), ensure_ascii=False, indent=2))
    print("\nprojects.csv: READ ONLY — never deleted by this agent.")
    return 0


def cmd_scan(args: argparse.Namespace) -> int:
    cfg = load_config(args.config)
    csv_path = (cfg.get("sheet") or {}).get("projects_csv")
    df = load_catalog_readonly(csv_path)
    print(f"Каталог: {len(df)} строк (только чтение, без изменений)")
    report = run_discovery_scan(df, cfg, root=ROOT)
    s = report.get("summary") or {}
    print(f"QC candidate: {s.get('candidates', s.get('new_projects', 0))}")
    print(f"  manual check: {s.get('manual_check', 0)} · rejected material: {s.get('rejected_material', 0)}")
    stats = s.get("source_stats") or {}
    if stats:
        print(f"  PRIDE v3: {stats.get('pride_v3_search', 0)} · PDC: {stats.get('pdc_uiStudySummary', 0)} · resolved: {stats.get('literature_resolved', 0)}")
    if s.get("articles_skipped"):
        print(f"  (статей без номера проекта пропущено: {s.get('articles_skipped')})")
    if s.get("already_in_catalog"):
        print(f"  Уже в каталоге: {s.get('already_in_catalog')}")
    print(f"Отчёт: {report.get('report_md')}")
    if report.get("report_html"):
        print(f"Сайт:  {report.get('report_html')}")
    if report.get("report_qc_html"):
        print(f"QC:    {report.get('report_qc_html')}")
    print(f"История: {report.get('history_file')}")
    return 0


def cmd_latest(_args: argparse.Namespace) -> int:
    data = load_latest(ROOT)
    if not data:
        print("Нет сканов. Запустите: python run_discovery.py scan")
        return 1
    s = data.get("summary") or {}
    print(f"Дата: {data.get('generated_at')}")
    print(f"Новых проектов: {s.get('new_projects', 0)}")
    if s.get("articles_skipped"):
        print(f"  (статей без номера проекта пропущено: {s.get('articles_skipped')})")
    for p in (data.get("new_projects") or data.get("recommended") or [])[:10]:
        acc = p.get("project_accession") or p.get("accession") or "?"
        print(f"  {acc} — {(p.get('title') or '')[:60]}")
    return 0


def cmd_history(args: argparse.Namespace) -> int:
    for h in list_scans(ROOT, limit=args.limit):
        print(f"{h.get('generated_at', '?')[:19]}  new={h.get('new_projects', h.get('novel_count', '?'))}  {h.get('file')}")
    return 0


def cmd_profile(args: argparse.Namespace) -> int:
    cfg = load_config(args.config)
    df = load_catalog_readonly((cfg.get("sheet") or {}).get("projects_csv"))
    prof = build_catalog_profile(df)
    print(json.dumps(prof, ensure_ascii=False, indent=2))
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description="Discovery Agent (read-only catalog)")
    p.add_argument("--config", help="config.yaml")
    sub = p.add_subparsers(dest="command", required=True)

    sub.add_parser("policy").set_defaults(func=cmd_policy)
    sub.add_parser("scan").set_defaults(func=cmd_scan)
    sub.add_parser("latest").set_defaults(func=cmd_latest)
    pr = sub.add_parser("profile", help="Профиль атласа для поиска")
    pr.set_defaults(func=cmd_profile)

    hi = sub.add_parser("history")
    hi.add_argument("--limit", type=int, default=15)
    hi.set_defaults(func=cmd_history)

    args = p.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
