#!/usr/bin/env python3
"""
Ревизор платформы Atlas — проверка таблицы, авто-правки, поиск новых публикаций.

  python run_revisor.py audit          # полный аудит → reports/revisor_*.json
  python run_revisor.py fix            # показать что исправится (dry-run)
  python run_revisor.py fix --apply    # применить + бэкап CSV
  python run_revisor.py scan           # PRIDE JSON + статьи 2026
  python run_revisor.py add            # добавить новые PXD (dry-run)
  python run_revisor.py add --apply    # записать в projects.csv
  python run_revisor.py viz            # HTML dashboard
  python run_revisor.py all            # audit + scan + fix dry-run
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from atlas_agent.config import load_config
from atlas_agent.revisor import fix_and_save, run_full_audit, scan_new_content
from atlas_agent.revisor.catalog_update import append_candidates
from atlas_agent.sources.projects_table import catalog_path, is_excel_catalog, load_catalog
from atlas_agent.viz.dashboard import generate_dashboard


def _csv_path(cfg: dict) -> str:
    sc = cfg.get("sheet") or {}
    return catalog_path(sc) or "./project of Proteomics.xlsx"


def _reports_dir(cfg: dict) -> Path:
    p = Path((cfg.get("paths") or {}).get("reports_dir") or "./reports")
    p.mkdir(parents=True, exist_ok=True)
    return p


def cmd_audit(args: argparse.Namespace) -> int:
    cfg = load_config(args.config)
    df = load_catalog(cfg)
    tmt_root = (cfg.get("paths") or {}).get("tmt_projects_dir", "")
    audit = run_full_audit(df, tmt_root=tmt_root, file_check_limit=args.file_limit)
    payload = audit.to_dict()
    payload["generated_at"] = datetime.now(timezone.utc).isoformat()

    out = _reports_dir(cfg) / f"revisor_audit_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    counts = audit.by_severity()
    print(f"Строк в таблице: {audit.stats.get('total_rows', len(df))}")
    print(f"Уникальных PXD: {audit.stats.get('unique_primary_ids', '?')}")
    print(f"Дубликаты PXD: {audit.stats.get('duplicate_primary_ids', 0)}")
    print(f"Ошибки: {counts.get('error', 0)} | предупреждения: {counts.get('warning', 0)} | info: {counts.get('info', 0)}")
    print(f"Отчёт: {out}")
    if args.verbose:
        for f in audit.findings[: args.show]:
            print(f"  [{f.severity.value}] {f.project_id or '-'}: {f.message[:90]}")
    return 0


def cmd_fix(args: argparse.Namespace) -> int:
    cfg = load_config(args.config)
    if is_excel_catalog(cfg.get("sheet") or {}):
        print("Каталог — Excel (TMT ATLAS). Авто-правки только для CSV; Excel не изменяется.")
        return 0
    csv_path = _csv_path(cfg)
    result = fix_and_save(csv_path, dry_run=not args.apply)
    mode = "ПРИМЕНЕНО" if result.get("saved") else "dry-run"
    print(f"Режим: {mode}")
    print(f"Правок: {result.get('changes', 0)}")
    if result.get("backup"):
        print(f"Бэкап: {result['backup']}")
    for line in (result.get("log") or [])[:30]:
        print(f"  {line}")
    if len(result.get("log") or []) > 30:
        print(f"  ... ещё {len(result['log']) - 30}")
    if not args.apply and result.get("changes"):
        print("\nЧтобы записать: python run_revisor.py fix --apply")
    return 0


def cmd_scan(args: argparse.Namespace) -> int:
    cfg = load_config(args.config)
    df = load_catalog(cfg)
    scan_cfg = cfg.get("scan") or {}
    year = int(scan_cfg.get("scan_year") or 2026)
    data = scan_new_content(
        df,
        pride_max=int(scan_cfg.get("pride_max_results") or 50),
        pub_max=int(scan_cfg.get("publications_max") or 40),
        year_from=year,
        year_to=int(scan_cfg.get("scan_year_to") or year),
        pride_keywords=scan_cfg.get("pride_keywords"),
        annotate_similar=True,
        cfg=cfg,
    )
    data["generated_at"] = datetime.now(timezone.utc).isoformat()

    out = _reports_dir(cfg) / f"revisor_scan_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    out.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Известно PMID: {data['known_pmids']} | PXD: {data['known_pxds']}")
    print(f"Новых PRIDE (нет в таблице): {len(data['new_pride'])}")
    for p in data["new_pride"][:8]:
        print(f"  {p.get('accession')} — {(p.get('title') or '')[:70]}")
    print(f"Новых статей (Europe PMC): {len(data['new_publications'])}")
    for p in data["new_publications"][:8]:
        pxds = ", ".join(p.get("pxd_mentioned") or []) or "—"
        print(f"  PMID {p.get('pmid')} PXD:{pxds} — {(p.get('title') or '')[:60]}")
    gh = data.get("new_github_projects") or []
    print(f"Новых на GitHub (нет в CSV): {len(gh)}")
    for p in gh[:6]:
        if p.get("error"):
            print(f"  GitHub: {p['error']}")
            break
        print(f"  {p.get('pxd')} — {p.get('repo', '')} {p.get('github_path', '')}")
    print(f"Отчёт: {out}")
    return 0


def cmd_all(args: argparse.Namespace) -> int:
    cmd_audit(args)
    print()
    cmd_scan(args)
    print()
    return cmd_fix(args)


def main() -> int:
    p = argparse.ArgumentParser(description="Atlas Revisor — проверка и исправление платформы")
    p.add_argument("--config", help="config.yaml")
    sub = p.add_subparsers(dest="command", required=True)

    au = sub.add_parser("audit", help="Аудит таблицы и папок")
    au.add_argument("--file-limit", type=int, default=50)
    au.add_argument("--verbose", "-v", action="store_true")
    au.add_argument("--show", type=int, default=25)
    au.set_defaults(func=cmd_audit)

    fx = sub.add_parser("fix", help="Авто-правки (PMID, пробелы)")
    fx.add_argument("--apply", action="store_true", help="Записать CSV (с бэкапом)")
    fx.set_defaults(func=cmd_fix)

    sc = sub.add_parser("scan", help="Новые PRIDE и публикации")
    sc.set_defaults(func=cmd_scan)

    al = sub.add_parser("all", help="audit + scan + fix dry-run")
    al.add_argument("--file-limit", type=int, default=50)
    al.add_argument("--verbose", "-v", action="store_true")
    al.add_argument("--show", type=int, default=15)
    al.add_argument("--apply", action="store_true")
    al.set_defaults(func=cmd_all)

    args = p.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
