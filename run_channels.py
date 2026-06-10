#!/usr/bin/env python3
"""
Канал TMT → пациент: зелёные проекты Protomix + таблица + диск + GitHub.

  python run_channels.py build          # датасет + обучение правил
  python run_channels.py build --pdc    # только зелёные PDC
  python run_channels.py show PXD026279 # один проект
  python run_channels.py apply          # применить модель к неразмеченным
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from atlas_agent.analysis.channel_patient import (
    apply_learned_rules,
    build_full_dataset,
    build_project_channel_map,
    learn_label_rules,
    save_channel_dataset,
)
from atlas_agent.config import load_config
from atlas_agent.sources.projects_table import load_projects_table
from atlas_agent.workflow.project_lookup import find_project_row


def cmd_build(args: argparse.Namespace) -> int:
    cfg = load_config(args.config)
    csv_path = (cfg.get("sheet") or {}).get("projects_csv")
    df = load_projects_table(csv_path)
    tmt_root = (cfg.get("paths") or {}).get("tmt_projects_dir", "")
    data_dir = Path(__file__).parent / "data"

    database = "PDC" if getattr(args, "pdc", False) else None
    tag = "pdc_green" if database == "PDC" else ""
    label = "зелёные PDC" if database == "PDC" else "зелёные (complete)"
    print(f"Сбор аннотаций ({label})...")
    dataset = build_full_dataset(
        df,
        tmt_root=tmt_root,
        cfg=cfg,
        only_green=not args.all_projects,
        database=database,
    )
    if dataset.empty:
        print("Нет данных. Проверьте TMT Label, статус complete и фильтр PDC.")
        return 1

    model = learn_label_rules(dataset)
    dataset = apply_learned_rules(dataset, model)
    paths = save_channel_dataset(df, dataset, model, data_dir, tag=tag)

    n_pat = (dataset["patient_id"].astype(str).str.len() > 0).sum()
    print(f"Проектов: {dataset['project_id'].nunique()}")
    print(f"Каналов: {len(dataset)} | с patient_id: {n_pat}")
    print(f"Правил обучено: {model['n_rules']}")
    print(f"Датасет: {paths['dataset']}")
    print(f"Обучение (green): {paths['training_green']}")
    print(f"Модель: {paths['model']}")
    return 0


def cmd_show(args: argparse.Namespace) -> int:
    cfg = load_config(args.config)
    df = load_projects_table((cfg.get("sheet") or {}).get("projects_csv"))
    row = find_project_row(df, args.project)
    if row is None:
        print("Не найден")
        return 1
    pid = str(row["Project ID"])
    from atlas_agent.sources.projects_table import primary_project_id

    pid = primary_project_id(pid)
    tmt_root = (cfg.get("paths") or {}).get("tmt_projects_dir", "")
    recs = build_project_channel_map(row, pid, tmt_root=tmt_root, cfg=cfg)
    print(f"=== {pid} ({len(recs)} каналов) ===\n")
    print(f"{'Tag':6} {'Patient':16} {'Role/Cond':30} {'Source'}")
    for r in sorted(recs, key=lambda x: x.get("channel_tag", "")):
        print(
            f"{r.get('channel_tag',''):6} "
            f"{str(r.get('patient_id',''))[:16]:16} "
            f"{str(r.get('condition', r.get('label','')))[:30]:30} "
            f"{r.get('source','')}"
        )
    return 0


def cmd_apply(args: argparse.Namespace) -> int:
    model_path = Path(__file__).parent / "data" / "channel_patient_model.json"
    if not model_path.is_file():
        print("Сначала: python run_channels.py build")
        return 1
    model = json.loads(model_path.read_text(encoding="utf-8"))
    cfg = load_config(args.config)
    df = load_projects_table((cfg.get("sheet") or {}).get("projects_csv"))
    tmt_root = (cfg.get("paths") or {}).get("tmt_projects_dir", "")
    dataset = build_full_dataset(df, tmt_root=tmt_root, cfg=cfg, only_green=False)
    updated = apply_learned_rules(dataset, model)
    out = Path(__file__).parent / "data" / "channel_patient_suggestions.csv"
    todo = updated[updated["source"].astype(str).str.contains("learned")]
    todo.to_csv(out, index=False, encoding="utf-8-sig")
    print(f"Подсказки для неразмеченных: {len(todo)} → {out}")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description="TMT channel → patient mapping")
    p.add_argument("--config")
    sub = p.add_subparsers(dest="command", required=True)

    b = sub.add_parser("build", help="Датасет + обучение на green проектах")
    b.add_argument("--all-projects", action="store_true", help="Не только green")
    b.add_argument("--pdc", action="store_true", help="Только зелёные PDC (Protomix)")
    b.set_defaults(func=cmd_build)

    s = sub.add_parser("show", help="Каналы одного PXD")
    s.add_argument("project")
    s.set_defaults(func=cmd_show)

    sub.add_parser("apply", help="Подсказки patient_id по модели").set_defaults(func=cmd_apply)

    args = p.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
