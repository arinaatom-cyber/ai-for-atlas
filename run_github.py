#!/usr/bin/env python3
"""
GitHub для Atlas — ТОЛЬКО чтение (ничего не удаляется и не пушится).

  python run_github.py policy          # правила безопасности
  python run_github.py repos           # статус репозиториев из config.yaml
  python run_github.py ls Projects     # список файлов/папок в data_repo
  python run_github.py cat projects/PXD005410/README.md
  python run_github.py projects        # все PXD на GitHub
  python run_github.py compare         # CSV vs GitHub vs локальный диск
  python run_github.py analyze PXD005410
  python run_github.py report          # полный JSON для интеграции
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from atlas_agent.config import load_config
from atlas_agent.sources.github_analyzer import (
    analyze_repo_projects,
    build_github_integration_report,
    compare_sources,
)
from atlas_agent.sources.github_client import GitHubClient, parse_repo_url
from atlas_agent.sources.github_policy import policy_summary
from atlas_agent.sources.projects_table import load_projects_table


def _gh_cfg(cfg: dict) -> dict:
    return cfg.get("github") or {}


def _data_repo(cfg: dict):
    g = _gh_cfg(cfg)
    return parse_repo_url(g["data_repo"], default_branch=g.get("raw_branch") or "main")


def _atlas_repo(cfg: dict):
    g = _gh_cfg(cfg)
    return parse_repo_url(g["atlas_repo"], default_branch=g.get("raw_branch") or "main")


def cmd_policy(_args: argparse.Namespace) -> int:
    print(json.dumps(policy_summary(), ensure_ascii=False, indent=2))
    print("\nЗапись и удаление на GitHub в этой платформе не выполняются.")
    return 0


def cmd_repos(args: argparse.Namespace) -> int:
    cfg = load_config(args.config)
    client = GitHubClient()
    g = _gh_cfg(cfg)
    for label, url in [("atlas_web", g.get("atlas_repo")), ("data", g.get("data_repo"))]:
        if not url:
            continue
        ref = parse_repo_url(url, default_branch=g.get("raw_branch") or "main")
        meta = client.repo_meta(ref)
        if meta:
            print(f"[OK] {label}: {ref.slug}  private={meta.get('private')}  stars={meta.get('stargazers_count')}")
        else:
            print(f"[--] {label}: {ref.slug}  недоступен (приватный? нужен GITHUB_TOKEN)")
    return 0


def cmd_ls(args: argparse.Namespace) -> int:
    cfg = load_config(args.config)
    ref = _data_repo(cfg) if args.repo == "data" else _atlas_repo(cfg)
    client = GitHubClient()
    items = client.list_contents(ref, args.path or "")
    if not items:
        print("Пусто или нет доступа.")
        return 1
    for it in items:
        kind = it.get("type", "?")
        size = it.get("size") or ""
        print(f"  {kind:6} {it.get('name',''):40} {size}")
    return 0


def cmd_cat(args: argparse.Namespace) -> int:
    cfg = load_config(args.config)
    ref = _data_repo(cfg) if args.repo == "data" else _atlas_repo(cfg)
    client = GitHubClient()
    out = client.get_file_text(ref, args.path, max_bytes=args.max_bytes)
    if not out.get("found"):
        print(out.get("error", "not found"))
        return 1
    if out.get("truncated"):
        print(out.get("message"))
        return 0
    text = out.get("text", "")
    if args.head:
        text = "\n".join(text.splitlines()[: args.head])
    print(text)
    return 0


def cmd_projects(args: argparse.Namespace) -> int:
    cfg = load_config(args.config)
    g = _gh_cfg(cfg)
    client = GitHubClient()
    for label, url, sub in [
        ("data", g.get("data_repo"), g.get("data_projects_path") or "Projects"),
        ("atlas", g.get("atlas_repo"), g.get("atlas_projects_path") or "projects"),
    ]:
        if not url:
            continue
        ref = parse_repo_url(url, default_branch=g.get("raw_branch") or "main")
        folders = client.list_pxd_directories(ref, sub)
        print(f"\n=== {label} ({ref.slug}/{sub}) — {len(folders)} папок PXD ===")
        for f in folders[: args.limit]:
            print(f"  {f['pxd']:16} {f['path']}")
        if len(folders) > args.limit:
            print(f"  ... ещё {len(folders) - args.limit}")
    return 0


def cmd_compare(args: argparse.Namespace) -> int:
    cfg = load_config(args.config)
    df = load_projects_table((cfg.get("sheet") or {}).get("projects_csv"))
    g = _gh_cfg(cfg)
    client = GitHubClient()
    all_gh = []
    if g.get("data_repo"):
        ref = parse_repo_url(g["data_repo"], default_branch=g.get("raw_branch") or "main")
        if client.repo_meta(ref):
            all_gh.extend(
                analyze_repo_projects(
                    client, ref, g.get("data_projects_path") or "Projects"
                )
            )
    if g.get("atlas_repo"):
        ref = parse_repo_url(g["atlas_repo"], default_branch=g.get("raw_branch") or "main")
        if client.repo_meta(ref):
            all_gh.extend(
                analyze_repo_projects(
                    client, ref, g.get("atlas_projects_path") or "projects"
                )
            )
    local = (cfg.get("paths") or {}).get("tmt_projects_dir")
    cmp = compare_sources(df, github_projects=all_gh, local_root=local)

    print(f"CSV: {cmp['csv_count']} | GitHub: {cmp['github_count']} | Локально: {cmp['local_count']}")
    print(f"\nТолько на GitHub ({len(cmp['only_on_github'])}):")
    for p in cmp["only_on_github"][:15]:
        print(f"  {p}")
    print(f"\nТолько в CSV ({len(cmp['only_in_csv'])}):")
    for p in cmp["only_in_csv"][:15]:
        print(f"  {p}")
    if cmp.get("only_local_disk"):
        print(f"\nТолько на диске ({len(cmp['only_local_disk'])}):")
        for p in cmp["only_local_disk"][:10]:
            print(f"  {p}")

    if args.json:
        out = Path((cfg.get("paths") or {}).get("reports_dir") or "./reports")
        out.mkdir(parents=True, exist_ok=True)
        path = out / f"github_compare_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        path.write_text(json.dumps(cmp, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\nJSON: {path}")
    return 0


def cmd_analyze(args: argparse.Namespace) -> int:
    cfg = load_config(args.config)
    g = _gh_cfg(cfg)
    client = GitHubClient()
    pxd = args.project.upper()
    found = False
    for url, sub in [
        (g.get("data_repo"), g.get("data_projects_path") or "Projects"),
        (g.get("atlas_repo"), g.get("atlas_projects_path") or "projects"),
    ]:
        if not url:
            continue
        ref = parse_repo_url(url, default_branch=g.get("raw_branch") or "main")
        path = f"{sub.strip('/')}/{pxd}"
        items = client.list_contents(ref, path)
        if items:
            found = True
            print(f"Repo: {ref.slug}  path: {path}")
            for it in items:
                print(f"  {it.get('type'):6} {it.get('name')}  ({it.get('size')} B)")
    if not found:
        print(f"{pxd} не найден на GitHub (или нет доступа).")
        local = (cfg.get("paths") or {}).get("tmt_projects_dir")
        if local:
            from pathlib import Path

            folder = Path(local) / pxd
            if folder.is_dir():
                print(f"Локально: {folder}")
                for fn in sorted(folder.iterdir())[:20]:
                    print(f"  {fn.name}")
        return 1
    return 0


def cmd_report(args: argparse.Namespace) -> int:
    cfg = load_config(args.config)
    df = load_projects_table((cfg.get("sheet") or {}).get("projects_csv"))
    report = build_github_integration_report(cfg, df)
    out_dir = Path((cfg.get("paths") or {}).get("reports_dir") or "./reports")
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"github_integration_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Отчёт: {path}")
    cmp = report.get("comparison") or {}
    print(f"CSV {cmp.get('csv_count')} | GitHub {cmp.get('github_count')} | local {cmp.get('local_count')}")
    print(f"Новых на GitHub (нет в CSV): {len(cmp.get('only_on_github') or [])}")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description="Atlas GitHub (read-only)")
    p.add_argument("--config", help="config.yaml")
    sub = p.add_subparsers(dest="command", required=True)

    sub.add_parser("policy").set_defaults(func=cmd_policy)
    sub.add_parser("repos").set_defaults(func=cmd_repos)

    ls = sub.add_parser("ls", help="Список пути в репо")
    ls.add_argument("path", nargs="?", default="")
    ls.add_argument("--repo", choices=["data", "atlas"], default="data")
    ls.set_defaults(func=cmd_ls)

    cat = sub.add_parser("cat", help="Показать файл")
    cat.add_argument("path")
    cat.add_argument("--repo", choices=["data", "atlas"], default="atlas")
    cat.add_argument("--head", type=int, default=80)
    cat.add_argument("--max-bytes", type=int, default=200_000)
    cat.set_defaults(func=cmd_cat)

    pr = sub.add_parser("projects", help="Папки PXD на GitHub")
    pr.add_argument("--limit", type=int, default=40)
    pr.set_defaults(func=cmd_projects)

    cp = sub.add_parser("compare", help="CSV vs GitHub vs disk")
    cp.add_argument("--json", action="store_true")
    cp.set_defaults(func=cmd_compare)

    an = sub.add_parser("analyze", help="Файлы одного PXD")
    an.add_argument("project")
    an.set_defaults(func=cmd_analyze)

    sub.add_parser("report").set_defaults(func=cmd_report)

    args = p.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
