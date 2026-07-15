#!/usr/bin/env python3
"""Запуск Atlas Agent (локальные данные + Claude API)."""
from __future__ import annotations

import argparse
import sys

from dotenv import load_dotenv

from atlas_agent.agent import AtlasAgent
from atlas_agent.llm_client import is_llm_available, resolve_engine


def cmd_run(args: argparse.Namespace) -> int:
    agent = AtlasAgent(config_path=args.config)
    print(f"Загружено проектов: {len(agent.df)}")
    use_ai = not getattr(args, "no_ai", False) and not args.no_claude
    if use_ai:
        eng = resolve_engine(agent.llm_provider, agent.llm_base_url, prefer_cloud=agent.llm_prefer_cloud)
        if eng == "local_rules":
            print("ИИ: regex (нет API-ключа — добавьте ZAI_API_KEY в .env)")
        else:
            print(f"ИИ: {eng} · model={agent.llm_model or '(default)'}")
    else:
        print("ИИ: выключен")
    report = agent.run_full(
        validate_limit=args.validate_limit,
        file_audit_limit=args.file_audit_limit,
        pride_scan=not args.no_pride_scan,
        use_claude=use_ai,
    )
    json_path, md_path = agent.save_report(report)
    print(f"JSON: {json_path}")
    print(f"Markdown: {md_path}")
    return 0


def cmd_ask(args: argparse.Namespace) -> int:
    agent = AtlasAgent(config_path=args.config)
    print(agent.ask(args.project, question=args.question))
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Atlas Agent — data/projects.csv + Claude (platform.claude.com)"
    )
    p.add_argument("--config", help="config.yaml")
    sub = p.add_subparsers(dest="command")

    run_p = sub.add_parser("run", help="Полный отчёт")
    run_p.add_argument("--validate-limit", type=int, default=25)
    run_p.add_argument("--file-audit-limit", type=int, default=20)
    run_p.add_argument("--no-pride-scan", action="store_true")
    run_p.add_argument("--no-claude", action="store_true", help="Без ИИ-слоя")
    run_p.add_argument("--no-ai", action="store_true", help="= --no-claude")
    run_p.set_defaults(func=cmd_run)

    ask_p = sub.add_parser("ask", help="Вопрос по проекту")
    ask_p.add_argument("-p", "--project", required=True)
    ask_p.add_argument("-q", "--question")
    ask_p.set_defaults(func=cmd_ask)

    # Флаги верхнего уровня для python run_agent.py (без подкоманды run)
    p.add_argument("--validate-limit", type=int, default=25)
    p.add_argument("--file-audit-limit", type=int, default=20)
    p.add_argument("--no-pride-scan", action="store_true")
    p.add_argument("--no-claude", action="store_true")
    p.add_argument("--no-ai", action="store_true")
    return p


def main() -> int:
    load_dotenv()
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "ask":
        return cmd_ask(args)
    # run явно или по умолчанию
    return cmd_run(args)


if __name__ == "__main__":
    sys.exit(main())
