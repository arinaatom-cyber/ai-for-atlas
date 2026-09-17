#!/usr/bin/env python3
"""Анализ последнего Discovery-скана."""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    p = ROOT / "data" / "discovery_history" / "latest.json"
    if not p.is_file():
        print("Нет скана. Запустите: python run_discovery.py scan")
        return 1

    d = json.loads(p.read_text(encoding="utf-8"))
    s = d.get("summary") or {}
    st = s.get("source_stats") or {}

    print("=" * 60)
    print("DISCOVERY — ТЕСТ И АНАЛИЗ")
    print("=" * 60)
    print(f"Скан:     {str(d.get('generated_at', ''))[:19]} UTC")
    print(f"Каталог:  {s.get('catalog_rows')} строк · {s.get('catalog_unique_ids')} ID (TMT ATLAS)")
    print()

    print("--- Воронка QC ---")
    funnel = [
        ("Кандидаты (новые проекты)", s.get("candidates")),
        ("Manual check", s.get("manual_check")),
        ("Rejected (материал)", s.get("rejected_material")),
        ("Уже в каталоге", s.get("already_in_catalog")),
        ("Technical filter", s.get("filtered_out")),
        ("Duplicate similar", s.get("duplicate_similar")),
    ]
    for label, val in funnel:
        print(f"  {label:28} {val}")

    print()
    print("--- Источники API ---")
    for k in (
        "pride_v3_search", "pdc_uiStudySummary", "massive_json", "iprox_json",
        "literature_resolved", "semantic_from_abstract", "literature_semantic_manual",
        "publications_scanned", "abstract_llm_read", "abstract_regex_only",
        "literature_raw_hits", "literature_prefilter_kept", "literature_with_repo_id",
    ):
        if k in st:
            print(f"  {k:28} {st[k]}")

    pubs = d.get("publications_analyzed") or []
    fit = Counter(p.get("atlas_fit") for p in pubs)
    readers = Counter(p.get("abstract_reader", "?") for p in pubs)
    with_ids = sum(
        1 for p in pubs
        if any((p.get("accessions") or {}).get(k) for k in ("PXD", "PDC", "MSV", "IPX"))
    )

    print()
    print("--- ИИ: evaluation pipeline ---")
    tiers: Counter[str] = Counter()
    verdicts: Counter[str] = Counter()
    missing_ev = 0
    for key in ("candidates", "manual_check", "literature_semantic", "cohort_literature"):
        for item in d.get(key) or []:
            ev = item.get("evaluation")
            if not ev:
                missing_ev += 1
                continue
            tiers[str(ev.get("confidence") or "?")] += 1
            verdicts[str(ev.get("final_verdict") or "?")] += 1
    if missing_ev:
        print(f"  Без evaluation:           {missing_ev} — запустите scripts/enrich_and_publish_site.py")
    else:
        print("  Все bucket-items имеют evaluation")
    if tiers:
        print(f"  Confidence tiers:           {dict(tiers)}")
        print(f"  Final verdicts:             {dict(verdicts)}")

    qm = s.get("quality_metrics") or d.get("quality_metrics")
    if qm:
        bl = qm.get("benchmark_literature") or {}
        bp = qm.get("benchmark_projects") or {}
        if bl:
            print(f"  Benchmark literature:       precision={bl.get('precision')} recall={bl.get('recall')}")
        if bp:
            print(f"  Benchmark projects:         precision={bp.get('precision')} recall={bp.get('recall')}")

    print()
    print("--- ИИ: абстракты Europe PMC ---")
    print(f"  На сайте проанализировано:  {len(pubs)}")
    print(f"  atlas_fit yes/maybe/no:     {fit.get('yes',0)} / {fit.get('maybe',0)} / {fit.get('no',0)}")
    print(f"  LLM vs regex:               {st.get('abstract_llm_read',0)} / {st.get('abstract_regex_only',0)}")
    print(f"  PXD в тексте абстракта:     {with_ids}")
    print(f"  Без номера проекта:         {len(pubs) - with_ids}")

    print()
    print("--- Кандидаты по базе ---")
    cands = d.get("candidates") or []
    src = Counter()
    for c in cands:
        acc = (c.get("accession") or c.get("project_accession") or "").upper()
        if acc.startswith("PXD"):
            src["PRIDE"] += 1
        elif acc.startswith("PDC"):
            src["PDC"] += 1
        elif acc.startswith("MSV"):
            src["MassIVE"] += 1
        elif acc.startswith("IPX"):
            src["iProX"] += 1
        else:
            src["other"] += 1
    for k, v in src.most_common():
        print(f"  {k:12} {v}")

    lit = d.get("literature_semantic") or []
    print()
    print(f"--- Статьи без PXD (ручная, {len(lit)}) ---")
    for x in lit[:8]:
        title = (x.get("title") or "")[:55]
        print(f"  PMID {x.get('pmid')}  fit={x.get('atlas_fit')}  {title}")

    print()
    print("--- Топ по смыслу (yes / maybe) ---")
    ranked = sorted(
        [p for p in pubs if p.get("atlas_fit") in ("yes", "maybe")],
        key=lambda x: float(x.get("atlas_fit_score") or 0),
        reverse=True,
    )
    for p in ranked[:8]:
        summary = (p.get("summary_ru") or p.get("title") or "")[:72]
        print(f"  [{p.get('atlas_fit')} {p.get('atlas_fit_score')}] PMID {p.get('pmid')}: {summary}")

    print()
    print("--- Вывод ---")
    if s.get("candidates", 0) > 50:
        print("  Много кандидатов — нужна ручная приоритизация по organ/disease.")
    if fit.get("yes", 0) + fit.get("maybe", 0) > 0 and st.get("literature_resolved", 0) == 0:
        print("  ИИ находит похожие статьи, но PXD редко в абстракте — смотрите раздел «Без PXD» на сайте.")
    if st.get("semantic_from_abstract", 0) > 0:
        print(f"  Смысл -> PRIDE сработал: {st.get('semantic_from_abstract')} проект(ов).")
    print()
    print(f"Сайт: {ROOT / 'docs' / 'site' / 'discovery.html'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
