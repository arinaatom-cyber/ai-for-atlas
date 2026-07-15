#!/usr/bin/env python3
"""
Discovery Agent — поиск похожих проектов и статей (PRIDE, PDC, CCLE, GTEx, CPTAC).

ВАЖНО: data/projects.csv только ЧИТАЕТСЯ. Удаление и авто-изменение ЗАПРЕЩЕНЫ.

  python run_discovery.py policy     # правила
  python run_discovery.py scan       # полный поиск + отчёт
  python run_discovery.py latest     # последний отчёт
  python run_discovery.py history    # история еженедельных сканов
  python run_discovery.py profile    # профиль вашего атласа
  python run_discovery.py llm        # какой ИИ активен (Z.AI/Qwen/Claude/GPT4All)
  python run_discovery.py llm --test # проверка API-запроса

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
    sheet_cfg = cfg.get("sheet") or {}
    df = load_catalog_readonly(cfg)
    src = sheet_cfg.get("projects_file") or sheet_cfg.get("projects_csv", "?")
    sh = sheet_cfg.get("projects_sheet", "TMT ATLAS")
    print(f"Каталог: {len(df)} строк · {sh} · read-only")
    print(f"  файл: {src}")
    report = run_discovery_scan(df, cfg, root=ROOT)
    s = report.get("summary") or {}
    print(f"QC candidate: {s.get('candidates', s.get('new_projects', 0))}")
    print(f"  manual check: {s.get('manual_check', 0)} · rejected material: {s.get('rejected_material', 0)}")
    stats = s.get("source_stats") or {}
    if stats:
        print(
            f"  PRIDE JSON: {stats.get('pride_v3_search', 0)} · PDC: {stats.get('pdc_uiStudySummary', 0)}"
            f" · MassIVE: {stats.get('massive_json', 0)} · iProX: {stats.get('iprox_json', 0)}"
            f" · из статей: {stats.get('literature_resolved', 0)}"
        )
        if stats.get("abstract_llm_read") or stats.get("abstract_regex_only"):
            print(
                f"  Абстракты ИИ: {stats.get('abstract_llm_read', 0)}"
                f" · regex: {stats.get('abstract_regex_only', 0)}"
                f" · по смыслу yes/maybe: {stats.get('abstract_atlas_fit_yes', 0)}"
                f"/{stats.get('abstract_atlas_fit_maybe', 0)}"
            )
        if stats.get("semantic_from_abstract") or stats.get("literature_semantic_manual"):
            print(
                f"  Smysl->PRIDE: {stats.get('semantic_from_abstract', 0)}"
                f" · статьи без PXD (ручная): {stats.get('literature_semantic_manual', 0)}"
            )
    if s.get("articles_skipped"):
        print(f"  (статей без номера проекта пропущено: {s.get('articles_skipped')})")
    if s.get("already_in_catalog"):
        print(f"  Уже в каталоге: {s.get('already_in_catalog')}")
    print(f"Отчёт: {report.get('report_md')}")
    if report.get("report_html"):
        print(f"Сайт:  {report.get('report_html')}")
    if report.get("report_qc_html"):
        print(f"QC:    {report.get('report_qc_html')}")
    if report.get("report_site_dir"):
        site = report["report_site_dir"]
        print(f"Сайт:  {site}/discovery.html  (полный анализ)")
        print(f"       {site}/qc.html")
        pubs = len(report.get("publications_analyzed") or [])
        lit = len(report.get("literature_semantic") or [])
        if pubs or lit:
            print(f"       абстрактов: {pubs} · без PXD (ручная): {lit}")
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


def cmd_publish(_args: argparse.Namespace) -> int:
    data = load_latest(ROOT)
    if not data:
        print("Нет сканов. Запустите: python run_discovery.py scan")
        return 1
    from atlas_agent.viz.publish_site import publish_discovery_site

    site_dir = publish_discovery_site(data, ROOT)
    print(f"Сайт обновлён: {site_dir}")
    print(f"  discovery.html — проекты + ИИ-анализ абстрактов")
    print(f"  qc.html — QC отчёт")
    print(f"  latest.json — данные для API")
    pubs = len(data.get("publications_analyzed") or [])
    if not pubs:
        print("  (нет publications_analyzed — запустите scan для полного анализа)")
    return 0


def cmd_llm(args: argparse.Namespace) -> int:
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env")
    cfg = load_config(args.config)
    llm = cfg.get("llm") or {}
    from atlas_agent.llm_client import list_llm_engines, ping_llm, resolve_engine

    provider = llm.get("provider", "auto")
    prefer_cloud = bool(llm.get("prefer_cloud", True))
    engine = resolve_engine(provider, llm.get("base_url"), prefer_cloud=prefer_cloud)
    print("LLM config:")
    print(f"  provider (config): {provider}")
    print(f"  prefer_cloud:      {prefer_cloud}")
    print(f"  engine (active):   {engine}")
    print(f"  model (config):    {llm.get('model', '(default per engine)')}")
    print(f"  enabled:           {llm.get('enabled', True)}")
    print()
    print("Providers:")
    for row in list_llm_engines(prefer_cloud=prefer_cloud):
        mark = " <-- active" if row["active"] else ""
        key = f" [{row['key_env']}]" if row["key_env"] != "—" else ""
        ok = "yes" if row["available"] else "no"
        print(f"  {row['label']:22} available={ok}{key}{mark}")
    print()
    if prefer_cloud and engine in ("gpt4all", "ollama", "local_rules"):
        print("Подсказка: prefer_cloud=true, но облачный ключ не найден.")
        print("  Добавьте в .env: ZAI_API_KEY=... (https://z.ai -> API Keys)")
        print("  или DASHSCOPE_API_KEY / ANTHROPIC_API_KEY")
        print()
    test_result = None
    if getattr(args, "test", False):
        print("Тест API...")
        test_result = ping_llm(
            provider=provider,
            model=llm.get("model"),
            base_url=llm.get("base_url"),
            gpt4all_model=llm.get("gpt4all_model"),
            prefer_cloud=prefer_cloud,
        )
        if test_result.get("ok"):
            print(f"  OK · {test_result.get('engine')}")
            if test_result.get("reply"):
                print(f"  reply: {test_result['reply'][:120]}")
            if test_result.get("usage"):
                print(f"  usage: {test_result['usage']}")
        else:
            print(f"  FAIL · {test_result.get('engine')} · {test_result.get('error')}")
        print()
    print("Discovery abstract_llm:", (cfg.get("discovery") or {}).get("abstract_llm", True))
    print("Полное описание: docs/DISCOVERY_PIPELINE_RU.md")
    if test_result is not None:
        return 0 if test_result.get("ok") else 1
    return 0


def cmd_profile(args: argparse.Namespace) -> int:
    cfg = load_config(args.config)
    df = load_catalog_readonly(cfg)
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
    sub.add_parser("publish", help="Обновить docs/site из последнего скана").set_defaults(func=cmd_publish)
    pr = sub.add_parser("profile", help="Профиль атласа для поиска")
    pr.set_defaults(func=cmd_profile)
    llm_p = sub.add_parser("llm", help="Какой ИИ активен (Z.AI/Qwen/Claude/GPT4All)")
    llm_p.add_argument("--test", action="store_true", help="Отправить тестовый запрос к активному движку")
    llm_p.set_defaults(func=cmd_llm)

    hi = sub.add_parser("history")
    hi.add_argument("--limit", type=int, default=15)
    hi.set_defaults(func=cmd_history)

    args = p.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
