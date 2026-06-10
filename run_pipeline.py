#!/usr/bin/env python3
"""
Полный прогон платформы от и до:
  audit → fix → scan 2026 (PRIDE JSON + статьи) → добавить новые PXD → sync → dashboard → agent

  python run_pipeline.py
  python run_pipeline.py --apply          # записать fix + новые строки в CSV
  python run_pipeline.py --no-ai          # без локального ИИ (быстрее)
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from atlas_agent.config import load_config
from atlas_agent.revisor import fix_and_save, run_full_audit, scan_new_content
from atlas_agent.revisor.catalog_update import append_candidates
from atlas_agent.sources.projects_table import load_projects_table
from atlas_agent.viz.dashboard import generate_dashboard
from atlas_agent.workflow.completeness import audit_table


def _csv(cfg) -> Path:
    return Path((cfg.get("sheet") or {}).get("projects_csv", "./data/projects.csv"))


def _reports(cfg) -> Path:
    p = Path((cfg.get("paths") or {}).get("reports_dir", "./reports"))
    p.mkdir(parents=True, exist_ok=True)
    return p


def step(title: str) -> None:
    print(f"\n{'='*60}\n{title}\n{'='*60}")


def main() -> int:
    p = argparse.ArgumentParser(description="Atlas full pipeline")
    p.add_argument("--config", help="config.yaml")
    p.add_argument("--apply", action="store_true", help="Записать fix и новые PXD в CSV")
    p.add_argument("--no-ai", action="store_true")
    p.add_argument("--skip-agent", action="store_true")
    p.add_argument("--add-all", action="store_true", help="Добавлять даже при похожих (не skip_similar)")
    args = p.parse_args()

    cfg = load_config(args.config)
    csv_path = _csv(cfg)
    reports = _reports(cfg)
    scan_cfg = cfg.get("scan") or {}
    year = int(scan_cfg.get("scan_year") or 2026)

    step("1/7 Ревизор: аудит таблицы")
    df = load_projects_table(str(csv_path))
    tmt_root = (cfg.get("paths") or {}).get("tmt_projects_dir", "")
    audit = run_full_audit(df, tmt_root=tmt_root, file_check_limit=80)
    audit_path = reports / f"revisor_audit_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    audit_path.write_text(
        json.dumps({**audit.to_dict(), "generated_at": datetime.now(timezone.utc).isoformat()}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    c = audit.by_severity()
    print(f"Ошибки {c.get('error',0)} | предупреждения {c.get('warning',0)} | → {audit_path}")

    step("2/7 Авто-правки (PMID, пробелы)")
    fix_res = fix_and_save(csv_path, dry_run=not args.apply)
    print(f"Правок: {fix_res.get('changes',0)} | saved={fix_res.get('saved')}")
    if fix_res.get("backup"):
        print(f"Бэкап: {fix_res['backup']}")
    df = load_projects_table(str(csv_path))

    step(f"3/7 Скан 2026: PRIDE JSON + Europe PMC ({year})")
    scan_data = scan_new_content(
        df,
        pride_max=int(scan_cfg.get("pride_max_results") or 50),
        pub_max=int(scan_cfg.get("publications_max") or 40),
        year_from=year,
        year_to=int(scan_cfg.get("scan_year_to") or year),
        pride_keywords=scan_cfg.get("pride_keywords"),
        annotate_similar=True,
    )
    scan_data["generated_at"] = datetime.now(timezone.utc).isoformat()
    scan_path = reports / f"revisor_scan_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    scan_path.write_text(json.dumps(scan_data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"PRIDE JSON кандидатов: {scan_data.get('pride_json_total',0)} | новых PXD: {len(scan_data['new_pride'])}")
    print(f"Новых статей: {len(scan_data['new_publications'])} | → {scan_path}")

    step("4/7 Добавление новых PXD в таблицу")
    add_res = append_candidates(
        df,
        scan_data.get("new_pride") or [],
        csv_path,
        dry_run=not args.apply,
        skip_similar=not args.add_all,
    )
    print(f"Добавить: {add_res.get('added',0)} | пропущено: {len(add_res.get('skipped',[]))}")
    for acc in add_res.get("accessions", [])[:10]:
        print(f"  + {acc}")
    if not args.apply and add_res.get("added"):
        print("  (dry-run) python run_pipeline.py --apply")

    pending_path = Path("data") / "pending_candidates.json"
    pending_path.write_text(
        json.dumps(
            {
                "pride": scan_data.get("new_pride"),
                "publications": scan_data.get("new_publications"),
                "append_result": add_res,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"Черновик кандидатов: {pending_path}")

    df = load_projects_table(str(csv_path))

    step("5/7 Workflow audit")
    wf = audit_table(df)
    wf_path = Path("data/workflow_audit.csv")
    wf.to_csv(wf_path, index=False, encoding="utf-8-sig")
    print(f"complete={(wf['status']=='complete').sum()} partial={(wf['status']=='partial').sum()} todo={(wf['status']=='todo').sum()}")
    print(f"→ {wf_path}")

    step("6/7 Визуализация (HTML dashboard)")
    dash = generate_dashboard(
        csv_path=str(csv_path),
        reports_dir=str(reports),
        out_path=str(reports / "dashboard.html"),
    )
    print(f"Откройте в браузере: {dash.resolve()}")

    if not args.skip_agent:
        step("7/7 Atlas Agent")
        cmd = [sys.executable, "run_agent.py"]
        if args.no_ai:
            cmd.append("--no-ai")
        r = subprocess.run(cmd, cwd=Path(__file__).parent)
        if r.returncode != 0:
            print("Agent завершился с ошибкой")
            return r.returncode
    else:
        print("\n7/7 Agent пропущен (--skip-agent)")

    print("\n✓ Pipeline завершён")
    return 0


if __name__ == "__main__":
    sys.exit(main())
