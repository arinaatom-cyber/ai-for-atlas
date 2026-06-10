#!/usr/bin/env python3
"""
Atlas mini-app — прозрачный CLI без ключей API.

  python atlas_app.py lookup PXD012173   # где файлы, что не заполнено, stat-план
  python atlas_app.py todo               # проекты «белые» (нужно дочитать)
  python atlas_app.py stats PXD012173    # статистика по пациентам/дизайну
  python atlas_app.py export             # все stat-планы → data/stats_plans/
  python atlas_app.py sync               # workflow_audit.csv
  python atlas_app.py revisor audit      # ревизор: ошибки в таблице
  python atlas_app.py revisor scan       # новые статьи / PRIDE
  python atlas_app.py github compare     # CSV vs GitHub (только чтение)
  python atlas_app.py tmt PXD005410      # один проект
  python atlas_app.py tmt-all            # все ваши TMT (~121) + index.html
  python atlas_app.py discovery scan     # поиск похожих проектов (read-only catalog)
  python atlas_app.py channels build     # green Protomix: канал→пациент + обучение
  python atlas_app.py channels show PXD026279
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from atlas_agent.config import load_config
from atlas_agent.sources.projects_table import load_projects_table, primary_project_id
from atlas_agent.workflow.completeness import audit_table, row_completeness
from atlas_agent.workflow.project_lookup import find_project_row, project_card


def _paths(cfg: dict) -> tuple[str, Path]:
    sheet = cfg.get("sheet") or {}
    paths = cfg.get("paths") or {}
    csv_path = sheet.get("projects_csv")
    root = Path(__file__).parent
    out = Path(paths.get("reports_dir") or root / "data")
    return csv_path, out


def cmd_lookup(args: argparse.Namespace) -> int:
    cfg = load_config(args.config)
    csv_path, _ = _paths(cfg)
    df = load_projects_table(csv_path)
    tmt_root = (cfg.get("paths") or {}).get("tmt_projects_dir", "")
    card = project_card(df, args.project, tmt_root)

    if not card.get("found"):
        print(f"Проект {args.project} не найден в {csv_path}")
        return 1

    if args.json:
        print(json.dumps(card, ensure_ascii=False, indent=2))
        return 0

    print(f"=== {card['project_id']} ===")
    print(card["title"][:120])
    print(f"Organ: {card['organ']} | Disease: {card['disease']}")
    print(f"Status: {card['completeness']['status']} ({card['completeness']['score_pct']}%)")
    print()
    print("Unified (как в таблице):")
    for k, v in card["unified_fields"].items():
        vshort = (v[:100] + "…") if len(v) > 100 else v
        print(f"  {k}: {vshort or '(пусто)'}")
    print()
    print("Где лежит:")
    for k, v in card["paths"].items():
        if v:
            print(f"  {k}: {v}")
    if card.get("local_files"):
        print(f"  local files: {', '.join(card['local_files'][:8])}")
    print()
    print("Пациенты / образцы:")
    ps = card["patient_summary"]
    print(f"  level: {ps['level']} | n_samples: {ps.get('n_samples_used')} | n_patients: {ps.get('n_patients_hint')}")
    print()
    print("Stat plan:")
    sp = card["stats_plan"]
    print(f"  design: {sp['design_type']} | test: {sp['test']} | blocking: {sp['blocking_factors']}")
    for w in sp.get("warnings", []):
        print(f"  ! {w}")
    print()
    print("Дальше:")
    for a in card["what_to_do_next"]:
        print(f"  - {a}")
    return 0


def cmd_todo(args: argparse.Namespace) -> int:
    cfg = load_config(args.config)
    csv_path, out = _paths(cfg)
    df = load_projects_table(csv_path)
    audit = audit_table(df)
    todo = audit[audit["status"].isin(["todo", "partial"])]
    if args.status:
        todo = audit[audit["status"] == args.status]

    out_file = Path(__file__).parent / "data" / "workflow_audit.csv"
    audit.to_csv(out_file, index=False, encoding="utf-8-sig")
    print(f"Сохранено: {out_file}")
    print(f"complete: {(audit['status'] == 'complete').sum()} | partial: {(audit['status'] == 'partial').sum()} | todo: {(audit['status'] == 'todo').sum()}")
    print()
    for _, r in todo.head(args.limit).iterrows():
        print(f"{r['project_id']:16} {r['status']:8} missing: {r['missing'][:60]}")
    if len(todo) > args.limit:
        print(f"... и ещё {len(todo) - args.limit}")
    return 0


def cmd_stats(args: argparse.Namespace) -> int:
    cfg = load_config(args.config)
    csv_path, _ = _paths(cfg)
    df = load_projects_table(csv_path)
    tmt_root = (cfg.get("paths") or {}).get("tmt_projects_dir", "")

    if args.project:
        card = project_card(df, args.project, tmt_root)
        if not card.get("found"):
            print("Not found")
            return 1
        print(card["stats_plan"]["r_template"])
        return 0

    out_dir = Path(__file__).parent / "data" / "stats_plans"
    out_dir.mkdir(parents=True, exist_ok=True)
    from atlas_agent.analysis.stats_plan import build_stats_plan

    n = 0
    for _, row in df.iterrows():
        pid = primary_project_id(str(row.get("Project ID", "")))
        if not pid:
            continue
        plan = build_stats_plan(row)
        path = out_dir / f"{pid}_stats.R"
        path.write_text(plan["r_template"], encoding="utf-8")
        meta = out_dir / f"{pid}_plan.json"
        meta.write_text(
            json.dumps({k: v for k, v in plan.items() if k != "r_template"}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        n += 1
    print(f"Exported {n} stat plans to {out_dir}")
    return 0


def cmd_sync(args: argparse.Namespace) -> int:
    if not hasattr(args, "limit"):
        args.limit = 30
    if not hasattr(args, "status"):
        args.status = None
    return cmd_todo(args)


def _print_tmt_view(pid: str, view: dict) -> None:
    print(f"=== TMT {pid} ===\n")
    print("--- Дизайн (таблица) ---")
    for k, v in view["sample_design"].items():
        if v and str(v) != "nan":
            print(f"  {k}: {v}")
    print("\n--- Каналы (аннотация из CSV) ---")
    for c in view["channels"]:
        print(f"  {c['tag']:6} | {c['role_ru']:22} | {c['label'][:50]}  [{c['from_column']}]")
    print("\n--- Нормализация ---")
    n = view["normalization"]
    print(f"  Strategy: {n.get('strategy_sheet')}")
    print(f"  Format:   {n.get('quantification_format')}")
    print(f"  {n.get('interpretation')}")
    m = view.get("matrix") or {}
    if m.get("found"):
        print(f"\n--- Матрица: {m.get('path')} ---")
        print(f"  Сырые каналы ({len(m.get('raw_channel_columns') or [])}): "
              f"{', '.join((m.get('raw_channel_columns') or [])[:10])}")
        rc = m.get("ratio_columns") or []
        if rc:
            print(f"  Ratio ({len(rc)}): {', '.join(rc[:4])} ...")
    else:
        print("\n--- Матрица: файл не найден ---")


def cmd_discovery(args: argparse.Namespace) -> int:
    import run_discovery

    if args.discovery_cmd == "scan":
        return run_discovery.cmd_scan(argparse.Namespace(config=args.config))
    if args.discovery_cmd == "latest":
        return run_discovery.cmd_latest(argparse.Namespace(config=args.config))
    if args.discovery_cmd == "history":
        return run_discovery.cmd_history(argparse.Namespace(config=args.config, limit=15))
    if args.discovery_cmd == "profile":
        return run_discovery.cmd_profile(argparse.Namespace(config=args.config))
    print("Подкоманды: scan | latest | history | profile")
    return 1


def cmd_channels(args: argparse.Namespace) -> int:
    import run_channels

    if args.channels_cmd == "build":
        ns = argparse.Namespace(
            config=args.config,
            all_projects=args.all_projects,
            pdc=getattr(args, "pdc", False),
        )
        return run_channels.cmd_build(ns)
    if args.channels_cmd == "show":
        ns = argparse.Namespace(config=args.config, project=args.project)
        return run_channels.cmd_show(ns)
    if args.channels_cmd == "apply":
        ns = argparse.Namespace(config=args.config)
        return run_channels.cmd_apply(ns)
    print("Подкоманды: build | show | apply")
    return 1


def cmd_tmt_all(args: argparse.Namespace) -> int:
    cfg = load_config(args.config)
    csv_path, out = _paths(cfg)
    df = load_projects_table(csv_path)
    tmt_root = (cfg.get("paths") or {}).get("tmt_projects_dir", "")

    from atlas_agent.analysis.tmt_batch import run_tmt_batch

    print("Обработка всех TMT-проектов из data/projects.csv ...")
    use_html = not args.no_html
    result = run_tmt_batch(
        df,
        tmt_root,
        out,
        html=use_html,
        limit=args.limit or 0,
        only_with_matrix=args.only_matrix,
    )
    print(f"Обработано: {result['processed']} / {result['total_tmt_projects']}")
    print(f"Ошибок: {result['errors']}")
    print(f"CSV: {result['csv']}")
    if result.get("index_html"):
        print(f"Каталог: {result['index_html']}")
    if result.get("html_dir"):
        print(f"HTML: {result['html_dir']}/")
    return 0


def cmd_tmt(args: argparse.Namespace) -> int:
    cfg = load_config(args.config)
    csv_path, out = _paths(cfg)
    df = load_projects_table(csv_path)
    row = find_project_row(df, args.project)
    if row is None:
        print(f"Проект {args.project} не найден")
        return 1

    from atlas_agent.analysis.tmt_channels import build_tmt_view
    from atlas_agent.viz.tmt_view import save_tmt_view_html

    pid = primary_project_id(str(row["Project ID"]))
    tmt_root = (cfg.get("paths") or {}).get("tmt_projects_dir", "")
    view = build_tmt_view(row, tmt_root)

    if args.json:
        print(json.dumps(view, ensure_ascii=False, indent=2, default=str))
        return 0

    _print_tmt_view(pid, view)
    m = view.get("matrix") or {}
    if m.get("found"):
        stats = m.get("column_stats") or {}
        for col, st in list(stats.items())[:6]:
            print(f"    {col}: median={st.get('median')}")

    if args.html:
        html_path = save_tmt_view_html(pid, view, out)
        print(f"\nHTML: {html_path}")
    return 0


def cmd_github(args: argparse.Namespace) -> int:
    import run_github

    ns = argparse.Namespace(config=args.config, json=True, repo="data", path="", limit=30, project="", head=80, max_bytes=200_000)
    if args.github_cmd == "compare":
        return run_github.cmd_compare(ns)
    if args.github_cmd == "report":
        return run_github.cmd_report(ns)
    if args.github_cmd == "projects":
        return run_github.cmd_projects(ns)
    print("Подкоманды: compare | report | projects")
    return 1


def cmd_revisor(args: argparse.Namespace) -> int:
    import run_revisor

    ns = argparse.Namespace(
        config=args.config,
        file_limit=50,
        verbose=args.verbose,
        show=20,
        apply=args.apply,
    )
    if args.revisor_cmd == "audit":
        return run_revisor.cmd_audit(ns)
    if args.revisor_cmd == "scan":
        return run_revisor.cmd_scan(ns)
    if args.revisor_cmd == "fix":
        return run_revisor.cmd_fix(ns)
    print("Подкоманды: audit | scan | fix")
    return 1


def main() -> int:
    p = argparse.ArgumentParser(description="Atlas mini-app")
    p.add_argument("--config", help="config.yaml")
    sub = p.add_subparsers(dest="command", required=True)

    lk = sub.add_parser("lookup", help="Карточка проекта")
    lk.add_argument("project")
    lk.add_argument("--json", action="store_true")
    lk.set_defaults(func=cmd_lookup)

    td = sub.add_parser("todo", help="Незаполненные unified-колонки")
    td.add_argument("--status", choices=["todo", "partial", "complete"])
    td.add_argument("--limit", type=int, default=30)
    td.set_defaults(func=cmd_todo)

    sub.add_parser("sync", help="= todo + workflow_audit.csv").set_defaults(func=cmd_sync)

    st = sub.add_parser("stats", help="R-шаблон статистики")
    st.add_argument("project", nargs="?", help="Один PXD или все")
    st.set_defaults(func=cmd_stats)

    ex = sub.add_parser("export", help="Все stat-планы в data/stats_plans/")
    ex.set_defaults(func=cmd_stats, project=None)

    tm = sub.add_parser("tmt", help="TMT-каналы, матрица, нормализация (один PXD)")
    tm.add_argument("project")
    tm.add_argument("--json", action="store_true")
    tm.add_argument("--html", action="store_true", help="Сохранить reports/tmt_view_PXD.html")
    tm.set_defaults(func=cmd_tmt)

    dc = sub.add_parser("discovery", help="Discovery Agent (read-only catalog)")
    dc.add_argument("discovery_cmd", choices=["scan", "latest", "history", "profile"])
    dc.set_defaults(func=cmd_discovery)

    ch = sub.add_parser("channels", help="Канал→пациент (green + файлы + GitHub)")
    ch.add_argument("channels_cmd", choices=["build", "show", "apply"])
    ch.add_argument("project", nargs="?", help="для show")
    ch.add_argument("--all-projects", action="store_true")
    ch.add_argument("--pdc", action="store_true", help="только green PDC")
    ch.set_defaults(func=cmd_channels)

    ta = sub.add_parser("tmt-all", help="Все TMT-проекты из вашей таблицы")
    ta.add_argument("--no-html", action="store_true", help="Только CSV, без HTML")
    ta.add_argument("--limit", type=int, default=0, help="Ограничить число проектов")
    ta.add_argument("--only-matrix", action="store_true", help="Только с файлом матрицы")
    ta.set_defaults(func=cmd_tmt_all)

    gh = sub.add_parser("github", help="GitHub read-only: compare / report / projects")
    gh.add_argument("github_cmd", choices=["compare", "report", "projects"])
    gh.set_defaults(func=cmd_github)

    rv = sub.add_parser("revisor", help="Ревизор: audit / scan / fix")
    rv.add_argument("revisor_cmd", choices=["audit", "scan", "fix"])
    rv.add_argument("--apply", action="store_true", help="fix: записать CSV")
    rv.add_argument("-v", "--verbose", action="store_true")
    rv.set_defaults(func=cmd_revisor)

    args = p.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
