"""Профиль вашего каталога — для поиска похожих проектов в интернете."""
from __future__ import annotations

import re
from collections import Counter
from typing import Any

import pandas as pd

from atlas_agent.sources.projects_table import primary_project_id


def build_catalog_profile(df: pd.DataFrame) -> dict[str, Any]:
    ids = []
    organs: Counter = Counter()
    diseases: Counter = Counter()
    databases: Counter = Counter()
    tmt_labels: Counter = Counter()

    for _, r in df.iterrows():
        pid = primary_project_id(str(r.get("Project ID", "")))
        if pid:
            ids.append(pid)
        db = str(r.get("Database", "") or "").strip()
        if db:
            databases[db] += 1
        for col, bucket in (("Organ", organs), ("Disease", diseases)):
            val = str(r.get(col, "") or "")
            for part in re.split(r"[;,/|]", val):
                part = part.strip()
                if len(part) > 2:
                    bucket[part.lower()] += 1
        tmt = str(r.get("TMT Label (Unified)", "") or "")
        if "tmt" in tmt.lower():
            tmt_labels[tmt[:40]] += 1

    return {
        "n_rows": len(df),
        "n_unique_ids": len(set(ids)),
        "project_ids_sample": sorted(set(ids))[:30],
        "databases": dict(databases.most_common(10)),
        "top_organs": [k for k, _ in organs.most_common(12)],
        "top_diseases": [k for k, _ in diseases.most_common(12)],
        "tmt_plexes": [k for k, _ in tmt_labels.most_common(8)],
        "search_keywords": _build_keywords(organs, diseases, tmt_labels),
    }


def _build_keywords(organs, diseases, tmt_labels) -> list[str]:
    kw = ["TMT", "tandem mass tag", "human proteomics", "isobaric"]
    kw.extend([o for o, _ in organs.most_common(5) if o not in ("", "nan")])
    kw.extend([d for d, _ in diseases.most_common(5) if d not in ("", "nan", "healthy")])
    kw.extend(["PDC", "CPTAC", "CCLE", "GTEx", "proteogenomics"])
    # unique preserve order
    seen = set()
    out = []
    for k in kw:
        kl = k.lower().strip()
        if kl and kl not in seen:
            seen.add(kl)
            out.append(k)
    return out[:20]


def build_atlas_semantic_context(
    df: pd.DataFrame,
    *,
    max_examples: int = 8,
    rejected_titles: list[str] | None = None,
) -> dict[str, Any]:
    """
    Контекст из TMT ATLAS для ИИ: читать абстракт по смыслу, как ваши 123 проекта.
    В статьях часто нет PXD — только «proteomics у пациентов», TMT, tumor/plasma.
    """
    organs: Counter = Counter()
    diseases: Counter = Counter()
    tissues: Counter = Counter()
    tmt_labels: Counter = Counter()
    sample_types: Counter = Counter()
    design_snippets: list[str] = []

    for _, r in df.iterrows():
        for col, bucket in (
            ("Organ", organs),
            ("Disease", diseases),
            ("Tissue", tissues),
            ("Sample Type", sample_types),
        ):
            val = str(r.get(col) or "")
            for part in re.split(r"[;,/|]", val):
                part = part.strip()
                if len(part) > 2:
                    bucket[part.lower()] += 1
        tmt = str(r.get("TMT Label (Unified)") or "").strip()
        if tmt:
            tmt_labels[tmt[:40]] += 1
        sd = str(r.get("Short Description") or "").strip()
        if len(sd) > 25:
            design_snippets.append(sd[:140])

    examples: list[dict[str, str]] = []
    seen_organs: set[str] = set()
    for _, r in df.iterrows():
        organ = str(r.get("Organ") or "").strip()
        organ_key = organ.lower()[:40]
        if organ_key in seen_organs and len(examples) >= max_examples:
            continue
        design = str(r.get("Short Description") or "").strip()
        if len(design) < 20:
            design = str(r.get("Tissue") or "")[:100]
        if len(design) < 15:
            continue
        examples.append(
            {
                "organ": organ[:50],
                "disease": str(r.get("Disease") or "")[:60],
                "tissue": str(r.get("Tissue") or "")[:80],
                "tmt": str(r.get("TMT Label (Unified)") or "")[:35],
                "design": design[:150],
            }
        )
        if organ_key:
            seen_organs.add(organ_key)
        if len(examples) >= max_examples:
            break

    reject_hints = [t[:100] for t in (rejected_titles or []) if t][:5]

    return {
        "n_atlas": len(df),
        "examples": examples,
        "top_organs": [k for k, _ in organs.most_common(10)],
        "top_diseases": [k for k, _ in diseases.most_common(10)],
        "top_tissues": [k for k, _ in tissues.most_common(8)],
        "top_tmt": [k for k, _ in tmt_labels.most_common(6)],
        "top_sample_types": [k for k, _ in sample_types.most_common(6)],
        "design_snippets": design_snippets[:12],
        "reject_hints": reject_hints,
        "prompt_block": format_atlas_context_for_llm(
            examples,
            organs,
            diseases,
            tmt_labels,
            reject_hints,
            n_atlas=len(df),
        ),
    }


def format_atlas_context_for_llm(
    examples: list[dict[str, str]],
    organs: Counter,
    diseases: Counter,
    tmt_labels: Counter,
    reject_hints: list[str],
    *,
    n_atlas: int,
) -> str:
    """Компактный блок для промпта LLM (обучение на вашем каталоге)."""
    lines = [
        f"REFERENCE ATLAS: {n_atlas} human TMT proteomics projects already curated.",
        "Typical fit: tumor/adjacent tissue, plasma/serum from patients, cancer cell lines.",
        "TMT 10/11/16-plex; paired case-control; clinical cohorts.",
        f"Top organs: {', '.join(k for k, _ in organs.most_common(6))}.",
        f"Top diseases: {', '.join(k for k, _ in diseases.most_common(6))}.",
        f"TMT in atlas: {', '.join(k for k, _ in tmt_labels.most_common(4))}.",
        "",
        "IMPORTANT: abstracts often have NO PXD/PDC/MSV numbers.",
        "Judge by meaning: proteomics + patients + TMT/isobaric + human tissue/plasma.",
        "Phrases like 'quantitative proteomics', 'mass spectrometry', 'patient cohort' may still fit.",
        "",
        "REJECT (not atlas): organoids-only, PDX-only, mouse/rat only, label-free only, reviews.",
    ]
    if reject_hints:
        lines.append("Previously rejected themes (avoid): " + "; ".join(reject_hints[:3]))
    lines.append("")
    lines.append("Examples from curator's atlas (learn the pattern):")
    for i, ex in enumerate(examples[:8], 1):
        lines.append(
            f"{i}. {ex.get('disease') or '?'} / {ex.get('organ') or '?'} | "
            f"{ex.get('tmt') or 'TMT'} | {ex.get('design') or ex.get('tissue')}"
        )
    return "\n".join(lines)
