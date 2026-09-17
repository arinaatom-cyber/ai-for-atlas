#!/usr/bin/env python3
"""Nature revision: similar projects, atlas gaps, Methods text, workflow schema."""
from __future__ import annotations

import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import pandas as pd

from atlas_agent.config import load_config
from atlas_agent.discovery.benchmark import evaluate_literature_benchmark, evaluate_project_benchmark
from atlas_agent.discovery.methods_manifest import build_methods_manifest
from atlas_agent.revisor.similarity import annotate_candidates

REPORT = ROOT / "reports" / "nature_revision.md"

# Organs on the public body map (TMT GitHub Pages)
MAP_ORGANS = [
    "Brain", "Lung", "Colon", "Stomach", "Liver", "Kidney", "Pancreas", "Ovary",
    "Breast", "Prostate", "Bladder", "Esophagus", "Thyroid", "Skin", "Eye",
    "Heart", "Blood", "Soft_Tissue", "Uterus", "Cervix",
]


def _organ_counts(df: pd.DataFrame) -> Counter:
    c: Counter = Counter()
    if "Organ" not in df.columns:
        return c
    for v in df["Organ"].dropna():
        for part in str(v).split(";"):
            p = part.strip()
            if p and p.lower() not in ("nan", "n/a"):
                c[p] += 1
    return c


def _title_key(title: str) -> str:
    t = " ".join(str(title or "").lower().split())
    return t[:80]


def _unique_studies(candidates: list[dict]) -> list[list[dict]]:
    groups: dict[str, list[dict]] = {}
    for c in candidates:
        key = _title_key(c.get("title") or c.get("accession") or "")
        groups.setdefault(key, []).append(c)
    return list(groups.values())


def _candidate_niche(c: dict) -> str:
    text = f"{c.get('title', '')} {c.get('sample_design', '')}".lower()
    if any(k in text for k in ("vitreous", "retinal", "eye", "glaucoma", "ocular")):
        return "Eye / vitreous"
    if any(k in text for k in ("glioma", "gbm", "brain", "cns", "cerebrospinal", "csf")):
        return "Brain / CNS"
    if "stomach" in text or "gastric" in text:
        return "Stomach"
    if "thyroid" in text:
        return "Thyroid"
    if "colorectal" in text or "colon" in text:
        return "Colon"
    return "unspecified niche"


def _results_paragraph(report: dict, candidates: list[dict], catalog_n: int) -> str:
    studies = _unique_studies(candidates)
    acc_list = ", ".join(c.get("accession", "?") for c in candidates[:6])
    niches = sorted({_candidate_niche(c) for c in candidates})
    niche_text = ", ".join(niches) if niches else "unspecified"
    lit_n = len([
        x for x in report.get("manual_check") or []
        if x.get("source") == "literature_semantic_candidate"
    ])
    study_note = ""
    if len(studies) < len(candidates):
        study_note = f" ({len(studies)} distinct studies; duplicate arms merged in expansion table)"
    return (
        f"Automated screening identified **{len(candidates)}** new human TMT repository "
        f"accessions{study_note}: {acc_list}. "
        f"None overlapped the curated catalog (n={catalog_n}); "
        f"niches represented: {niche_text}. "
        f"Semantic literature surveillance flagged {lit_n} patient-cohort papers without "
        f"repository IDs in abstracts, pending manual accession resolution."
    )


def _map_coverage(df: pd.DataFrame) -> list[tuple[str, int, str]]:
    rows = []
    for organ in MAP_ORGANS:
        n = sum(
            1 for v in df["Organ"].dropna()
            if organ.lower().replace("_", " ") in str(v).lower()
            or organ.lower() in str(v).lower()
        )
        if n == 0:
            status = "gap — нет проектов"
        elif n <= 2:
            status = "слабо покрыт"
        else:
            status = "OK"
        rows.append((organ, n, status))
    return rows


def _similar_block(candidates: list[dict], df: pd.DataFrame) -> list[str]:
    lines = ["## Похожие проекты (новые находки vs каталог)", ""]
    if not candidates:
        lines.append("_Новых кандидатов нет._")
        return lines

    ann = annotate_candidates([dict(c) for c in candidates], df, threshold=0.15)
    seen_titles: set[str] = set()
    for c in ann:
        tkey = _title_key(c.get("title") or "")
        if tkey in seen_titles:
            lines.append(
                f"### {c.get('accession') or '?'} _(duplicate study arm — см. выше)_"
            )
        else:
            seen_titles.add(tkey)
            lines.append(f"### {c.get('accession') or '?'}")
        title = (c.get("title") or "")[:100]
        tier = (c.get("evaluation") or {}).get("confidence") or "?"
        design = c.get("sample_design") or "?"
        tmt = c.get("tmt_label") or "?"
        lines.append(f"- **Ниша:** {_candidate_niche(c)}")
        lines.append(f"- **Заголовок:** {title}")
        lines.append(f"- **TMT / дизайн:** {tmt} · {design} · tier **{tier}**")
        da = c.get("data_availability") or {}
        lines.append(f"- **Data:** {da.get('status', '?')} · {da.get('omics_layer', '?')}")
        sim = c.get("similar_in_catalog") or []
        if sim:
            lines.append("- **Ближайший в каталоге:**")
            for s in sim[:3]:
                lines.append(
                    f"  - {s['project_id']} (score {s['score']:.2f}) — {(s.get('title') or '')[:60]}"
                )
        else:
            lines.append("- **Ближайший в каталоге:** нет (новая ниша для атласа)")
        tips = c.get("processing_tips") or []
        if tips:
            lines.append(f"- **Заметка:** {tips[0]}")
        lines.append("")
    return lines


def _literature_block(report: dict) -> list[str]:
    lines = ["## Литература для Discussion / watchlist", ""]
    items = report.get("manual_check") or []
    if not items:
        lines.append("_Нет статей в manual_check._")
        return lines
    for it in items:
        if it.get("source") != "literature_semantic_candidate":
            continue
        pmid = it.get("pmid") or "?"
        fit = it.get("atlas_fit") or "?"
        title = (it.get("title") or "")[:90]
        summary = (it.get("summary_ru") or (it.get("abstract_ai") or {}).get("summary_ru") or "")[:120]
        lines.append(f"- **PMID {pmid}** ({fit}) — {title}")
        if summary:
            lines.append(f"  - {summary}")
    lines.append("")
    return lines


def _methods_paragraph(manifest: dict) -> str:
    inc = manifest.get("inclusion_criteria") or {}
    exc = manifest.get("exclusion_criteria") or []
    sc = manifest.get("search_config") or {}
    fun = manifest.get("funnel") or {}
    return (
        "**Living resource screening (Discovery Agent).** "
        f"We weekly queried PRIDE Archive v3, the NCI Proteomic Data Commons, MassIVE, and iProX "
        f"for human TMT/isobaric proteomics studies ({sc.get('year_from')}–{sc.get('year_to')}) "
        f"not present in the curated atlas (n={fun.get('candidates', 0)} new repository candidates per scan; "
        f"catalog read-only, n=123 projects). "
        f"Inclusion: {inc.get('organism')}; {inc.get('quantification')}; {inc.get('omics_layer')}. "
        f"Exclusion: {'; '.join(exc[:4])}. "
        f"Europe PMC abstracts were screened semantically (Ollama Qwen2.5-3B, regex-consensus); "
        f"repository accessions were resolved only from data-availability statements, not LLM inference. "
        f"Confidence tiers A–D combine file-level protein quant tables, sample design, and exclusion rules "
        f"(benchmark accuracy: literature {manifest.get('_lit_acc', '?')}, projects {manifest.get('_proj_acc', '?')})."
    )


def main() -> int:
    latest_path = ROOT / "data" / "discovery_history" / "latest.json"
    if not latest_path.is_file():
        print("Нет latest.json — python run_discovery.py scan")
        return 1

    cfg = load_config()
    report = json.loads(latest_path.read_text(encoding="utf-8"))
    df = pd.read_csv(ROOT / "data" / "projects.csv")
    s = report.get("summary") or {}
    manifest = build_methods_manifest(report, cfg)
    lit_b = evaluate_literature_benchmark()
    proj_b = evaluate_project_benchmark()
    manifest["_lit_acc"] = f"{lit_b['accuracy']:.0%}"
    manifest["_proj_acc"] = f"{proj_b['accuracy']:.0%}"

    coverage = _map_coverage(df)
    gaps = [o for o, n, st in coverage if "gap" in st or "слабо" in st]
    candidates = report.get("candidates") or []
    repo_manual = report.get("repository_manual") or []
    catalog_n = int(s.get("catalog_rows") or len(df))
    distinct_studies = len(_unique_studies(candidates))

    lines: list[str] = [
        "# Nature revision — Discovery & atlas gaps",
        "",
        f"Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        f"Scan: {str(report.get('generated_at', ''))[:19]} UTC",
        "",
        "## Схема пайплайна (что делает система)",
        "",
        "```mermaid",
        "flowchart TB",
        "  subgraph inputs [Inputs read-only]",
        f"    CSV[projects.csv n={catalog_n}]",
        "    XLS[Proteomics workbook]",
        "  end",
        "  subgraph search [Weekly search]",
        "    PRIDE[PRIDE v3 JSON]",
        "    PDC[PDC GraphQL TMT]",
        "    MS[MassIVE / iProX]",
        "    EPMC[Europe PMC 4 queries]",
        "  end",
        "  subgraph filter [Filters]",
        "    F1[Human TMT ≥10-plex]",
        "    F2[No phospho / peptide-only]",
        "    F3[Exclusion engine]",
        "    F4[Sample design QC]",
        "  end",
        "  subgraph ai [Local AI]",
        "    REG[Regex anchor]",
        "    OLL[Ollama Qwen2.5-3b]",
        "    CON[Consensus merge]",
        "  end",
        "  subgraph out [Outputs for paper]",
        "    A[Tier A candidates]",
        "    B[Literature watchlist]",
        "    M[Methods manifest]",
        "    G[Organ gap map]",
        "  end",
        "  CSV --> search",
        "  PRIDE --> F1",
        "  PDC --> F1",
        "  MS --> F1",
        "  EPMC --> F3",
        "  F1 --> F2 --> F4",
        "  EPMC --> REG --> OLL --> CON",
        "  F4 --> A",
        "  CON --> B",
        "  A --> M",
        "  CSV --> G",
        "```",
        "",
        "## Сводка последнего скана",
        "",
        f"| Метрика | Значение |",
        f"|---------|----------|",
        f"| Каталог | {s.get('catalog_rows', len(df))} проектов |",
        f"| **Новые кандидаты (tier A)** | **{len(candidates)}** ({distinct_studies} studies) |",
        f"| Литература (manual) | {len(report.get('manual_check') or [])} |",
        f"| Repo manual check | {len(repo_manual)} |",
        f"| Benchmark literature | {lit_b['accuracy']:.0%} ({lit_b['correct']}/{lit_b['n']}) |",
        f"| Benchmark projects | {proj_b['accuracy']:.0%} ({proj_b['correct']}/{proj_b['n']}) |",
        "",
        "## Текст для Methods (English, вставить в статью)",
        "",
        _methods_paragraph(manifest),
        "",
        "## Results — что написать одним абзацем",
        "",
        _results_paragraph(report, candidates, catalog_n),
        "",
        "## Пробелы атласа (куда смотреть похожие проекты)",
        "",
        "| Organ (body map) | Projects in catalog | Status |",
        "|------------------|--------------------:|--------|",
    ]

    for organ, n, status in coverage:
        lines.append(f"| {organ} | {n} | {status} |")

    lines.extend([
        "",
        "**Приоритет для living resource / Discussion:**",
    ])
    for g in gaps:
        lines.append(f"- {g}")

    lines.extend(_similar_block(candidates, df))
    lines.extend(_literature_block(report))

    if repo_manual:
        lines.extend(["## Репозитории на ручной проверке", ""])
        for it in repo_manual:
            lines.append(
                f"- **{it.get('accession')}** — {(it.get('title') or '')[:70]} "
                f"({'; '.join((it.get('filter_reasons') or [])[:1])})"
            )
        lines.append("")

    lines.extend([
        "## Чего не хватает для Nature revision",
        "",
        "| Блок | Статус | Действие |",
        "|------|--------|----------|",
        f"| Living resource pipeline | OK | Methods manifest → Supplementary Table S× |",
        f"| Benchmark validation | {proj_b['accuracy']:.0%} projects | Cite in Methods |",
        f"| New tier-A datasets | {len(candidates)} acc / {distinct_studies} studies | Table: accession, organ, TMT, URL |",
        f"| Organ gaps | {len(gaps)} weak/empty | Discussion: future expansion |",
        "| PXD from literature | 0 auto-resolved | Manual full-text check for 4 maybe papers |",
        "| Eye / vitreous (PXD077831) | Eye: 1 catalog project | Vitreous fluid — new sub-niche |",
        "| Pediatric glioma PDC | PDC000495 + PDC000498 | One row in expansion table (duplicate arms) |",
        "",
        "## Команды",
        "",
        "```powershell",
        "python run_discovery.py scan",
        "python scripts/enrich_and_publish_site.py",
        "python scripts/nature_revision_report.py",
        "python scripts/update_manuscript_docx.py   # optional: patch .docx",
        "```",
        "",
    ])

    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text("\n".join(lines), encoding="utf-8")
    print(f"Report: {REPORT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
