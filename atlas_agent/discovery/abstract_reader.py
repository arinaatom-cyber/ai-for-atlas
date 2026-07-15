"""
ИИ-чтение абстрактов по смыслу TMT ATLAS (Europe PMC).
Номера PXD/PDC в абстракте НЕ ищем — только смысл: human TMT proteomics у пациентов.
"""
from __future__ import annotations

import json
import re
from collections import Counter
from typing import Any

from atlas_agent.discovery.filters import PHOSPHOPROTEOMICS, PEPTIDE_ONLY_OMICS, PROTEIN_LEVEL_OMICS
from atlas_agent.discovery.fit_rules import sanitize_summary
from atlas_agent.llm_client import _run_llm, resolve_engine

ABSTRACT_SYSTEM = """You are a curator assistant for a human TMT proteomics atlas.
Read abstracts by MEANING using the reference atlas — do NOT extract repository accession numbers.
Reply with ONLY valid JSON, no markdown. Be conservative: if unclear, use "unclear"."""

ABSTRACT_PROMPT = """{atlas_context}

---
NEW PAPER TO EVALUATE

Title: {title}

Abstract:
{abstract}

Data availability (if any):
{data_availability}

Task:
1) Does this describe human TMT/isobaric quantitative proteomics like the atlas
   (patients, tumor tissue, adjacent normal, plasma, cancer cell lines)?
2) Do NOT search for or return PXD, PDC, MSV, IPX — repository IDs are usually absent.
3) Reject TMT6 or <=6-plex; atlas uses TMT10/11/12/16 only.
4) Reject phosphoproteomics / phosphorylation profiling — atlas needs global protein-level proteome only.
5) Reject peptide-only quantification — need protein groups / proteome, not peptides.

JSON schema:
{{
  "atlas_fit": "yes|maybe|no",
  "atlas_fit_score": 0.0,
  "semantic_evidence": ["short phrases from abstract"],
  "similar_atlas_theme": "e.g. colorectal tumor adjacent normal",
  "organism": "human|mouse|mixed|unclear",
  "tmt": "TMT10|TMT11|TMT16|TMTpro16|ambiguous|none|unclear|TMT6",
  "material": "tumor tissue|adjacent normal|plasma|serum|blood|cancer cell line|organoid|pdx|other|unclear",
  "human_suitable": true,
  "material_suitable": true,
  "summary_ru": "one sentence in Russian: why fits or not"
}}"""

_EMPTY_ACCESSIONS = {"PXD": [], "PDC": [], "MSV": [], "IPX": []}


def _default_atlas_context() -> str:
    return format_atlas_context_for_llm(
        examples=[
            {
                "organ": "colon",
                "disease": "colorectal cancer",
                "tissue": "tumor and adjacent normal",
                "tmt": "TMT 10-plex",
                "design": "TMT quantitative proteomics of paired tumor/adjacent tissue from patients",
            }
        ],
        organs=Counter({"colon": 1}),
        diseases=Counter({"cancer": 1}),
        tmt_labels=Counter({"TMT 10-plex": 1}),
        reject_hints=[],
        n_atlas=123,
    )


def _tmt6_or_low_plex(blob_l: str, tmt: str) -> bool:
    if re.search(r"\btmt\s*[- ]?6\b|\btmt6\b|6\s*[- ]?plex", blob_l, re.I):
        return True
    return str(tmt).upper() in ("TMT6", "6")


def _regex_extract(title: str, abstract: str, extra: str = "") -> dict[str, Any]:
    blob = f"{title} {abstract} {extra}"
    blob_l = blob.lower()
    organism = "unclear"
    if re.search(r"\b(human|homo sapiens|patient|clinical|donor|cohort)\b", blob_l):
        organism = "human" if not re.search(r"\b(mouse|mice|murine|rat)\b", blob_l) else "mixed"
    elif re.search(r"\b(mouse|mice|murine)\b", blob_l):
        organism = "mouse"
    tmt = "unclear"
    if re.search(r"\btmt\s*[- ]?6\b|\btmt6\b", blob_l, re.I):
        tmt = "TMT6"
    elif re.search(r"tmt\s*[- ]?(10|11|16)|tmtpro\s*16", blob_l, re.I):
        m = re.search(r"tmtpro\s*16|tmt\s*[- ]?16", blob_l, re.I)
        tmt = "TMTpro16" if m and "pro" in m.group(0).lower() else (
            "TMT11" if "11" in blob_l else "TMT10" if "10" in blob_l else "TMT16"
        )
    elif re.search(r"\b(tmt|tandem mass tag|isobaric)\b", blob_l):
        tmt = "ambiguous"
    material = "unclear"
    for label, pat in [
        ("organoid", r"\borganoid"),
        ("pdx", r"\b(pdx|xenograft)\b"),
        ("tumor tissue", r"\b(tumor tissue|ffpe|biopsy|tumou?r)\b"),
        ("plasma", r"\b(plasma|serum|blood)\b"),
        ("cancer cell line", r"\b(cancer cell line|mcf[- ]?7|a549)\b"),
    ]:
        if re.search(pat, blob_l, re.I):
            material = label
            break

    atlas_fit = "no"
    score = 0.2
    evidence: list[str] = []
    if _tmt6_or_low_plex(blob_l, tmt):
        atlas_fit = "no"
        score = 0.1
        evidence.append("TMT6 / <=6-plex — не атлас")
    elif PHOSPHOPROTEOMICS.search(blob):
        atlas_fit = "no"
        score = 0.1
        evidence.append("фосфопротеомика — нужен protein-level proteome")
    elif PEPTIDE_ONLY_OMICS.search(blob) and not PROTEIN_LEVEL_OMICS.search(blob):
        atlas_fit = "no"
        score = 0.1
        evidence.append("peptide-level — нужны белки (protein groups)")
    elif organism in ("human", "unclear") and re.search(
        r"\b(proteom|mass spectrom|tmt|isobaric|quantitative)\b", blob_l
    ):
        if re.search(r"\b(patient|clinical|donor|cohort)\b", blob_l):
            evidence.append("human clinical proteomics")
            score = 0.55
            atlas_fit = "maybe"
        if tmt not in ("none", "unclear", "TMT6") and material not in ("organoid", "pdx"):
            score = max(score, 0.65)
            atlas_fit = "maybe"
        if re.search(r"\b(tmt|isobaric)\b", blob_l) and re.search(
            r"\b(patient|tumor|plasma|ffpe)\b", blob_l
        ) and PROTEIN_LEVEL_OMICS.search(blob_l):
            score = 0.6
            atlas_fit = "maybe"
            evidence.append("TMT + patient samples (regex — conservative maybe)")
    if organism == "mouse" or material in ("organoid", "pdx"):
        atlas_fit = "no"
        score = 0.15

    return {
        "atlas_fit": atlas_fit,
        "atlas_fit_score": score,
        "semantic_evidence": evidence,
        "similar_atlas_theme": "",
        "accessions": dict(_EMPTY_ACCESSIONS),
        "organism": organism,
        "tmt": tmt,
        "material": material,
        "human_suitable": organism in ("human", "unclear"),
        "material_suitable": material not in ("organoid", "pdx", "unclear"),
        "summary_ru": "",
        "reader": "regex",
    }


def _normalize_ai_parsed(parsed: dict[str, Any]) -> dict[str, Any]:
    fit = str(parsed.get("atlas_fit") or "no").lower()
    tmt = str(parsed.get("tmt") or "unclear")
    if _tmt6_or_low_plex("", tmt):
        fit = "no"
    blob = f"{parsed.get('title', '')} {parsed.get('summary_ru', '')}"
    if PHOSPHOPROTEOMICS.search(blob):
        fit = "no"
    if fit not in ("yes", "maybe", "no"):
        fit = "maybe" if parsed.get("human_suitable") and parsed.get("material_suitable") else "no"
    try:
        score = float(parsed.get("atlas_fit_score") or 0)
    except (TypeError, ValueError):
        score = 0.0
    # Do not inflate scores — 0.7 floor was misleading on the public site.
    score = max(0.0, min(1.0, score)) if score else None

    summary_ru = sanitize_summary(parsed.get("summary_ru"))
    summary_en = sanitize_summary(parsed.get("summary_en")) or summary_ru

    return {
        "atlas_fit": fit,
        "atlas_fit_score": score,
        "semantic_evidence": list(parsed.get("semantic_evidence") or [])[:8],
        "similar_atlas_theme": str(parsed.get("similar_atlas_theme") or "")[:120],
        "accessions": dict(_EMPTY_ACCESSIONS),
        "organism": str(parsed.get("organism") or "unclear"),
        "tmt": tmt,
        "material": str(parsed.get("material") or "unclear"),
        "human_suitable": bool(parsed.get("human_suitable", True)),
        "material_suitable": bool(parsed.get("material_suitable", True)),
        "summary_ru": summary_ru,
        "summary_en": summary_en,
    }


def read_abstract_with_llm(
    pub: dict[str, Any],
    *,
    cfg: dict | None = None,
    atlas_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """ИИ читает абстракт по смыслу (без поиска PXD/PDC)."""
    cfg = cfg or {}
    llm_cfg = cfg.get("llm") or {}
    disc = cfg.get("discovery") or {}
    ctx_block = (atlas_context or {}).get("prompt_block") or _default_atlas_context()

    if not disc.get("abstract_llm", True) or not llm_cfg.get("enabled", True):
        ai = _regex_extract(
            str(pub.get("title") or ""),
            str(pub.get("abstract") or ""),
            str(pub.get("data_availability") or ""),
        )
        out = dict(pub)
        out["abstract_ai"] = ai
        out["abstract_reader"] = "regex"
        return out

    provider = llm_cfg.get("provider", "auto")
    prefer_cloud = bool(llm_cfg.get("prefer_cloud", True))
    if resolve_engine(provider, llm_cfg.get("base_url"), prefer_cloud=prefer_cloud) == "local_rules":
        ai = _regex_extract(
            str(pub.get("title") or ""),
            str(pub.get("abstract") or ""),
            str(pub.get("data_availability") or ""),
        )
        out = dict(pub)
        out["abstract_ai"] = ai
        out["abstract_reader"] = "regex"
        return out

    title = str(pub.get("title") or "")[:500]
    abstract = str(pub.get("abstract") or "")[:3500]
    data_avail = str(pub.get("data_availability") or "")[:1500]
    if not abstract.strip():
        ai = _regex_extract(title, "", data_avail)
        out = dict(pub)
        out["abstract_ai"] = ai
        out["abstract_reader"] = "regex_no_abstract"
        return out

    prompt = ABSTRACT_PROMPT.format(
        atlas_context=ctx_block,
        title=title,
        abstract=abstract,
        data_availability=data_avail or "(not provided)",
    )
    try:
        raw, engine, _usage = _run_llm(
            prompt,
            ABSTRACT_SYSTEM,
            provider=provider,
            model=llm_cfg.get("model"),
            base_url=llm_cfg.get("base_url"),
            gpt4all_model=llm_cfg.get("gpt4all_model"),
            max_tokens=min(int(llm_cfg.get("max_tokens") or 1024), 900),
            prefer_cloud=prefer_cloud,
        )
        text = raw.strip()
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?\s*", "", text)
            text = re.sub(r"\s*```$", "", text)
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            parsed = {}
        if "atlas_fit" not in parsed and "organism" not in parsed:
            parsed = _regex_extract(title, abstract, data_avail)
            parsed["reader"] = f"{engine}_parse_fail"
        else:
            parsed = _normalize_ai_parsed(parsed)
            parsed["reader"] = engine
    except Exception as exc:
        parsed = _regex_extract(title, abstract, data_avail)
        parsed["reader"] = f"regex_error:{exc.__class__.__name__}"

    out = dict(pub)
    out["abstract_ai"] = parsed
    out["abstract_reader"] = parsed.get("reader", "llm")
    out["pxd_mentioned"] = []
    out["accessions_mentioned"] = []
    out["atlas_fit"] = parsed.get("atlas_fit")
    out["atlas_fit_score"] = parsed.get("atlas_fit_score")
    from atlas_agent.discovery.fit_rules import apply_literature_exclusions

    return apply_literature_exclusions(out)


def enrich_publications_with_ai(
    pubs: list[dict],
    *,
    cfg: dict | None = None,
    atlas_context: dict[str, Any] | None = None,
    max_llm: int | None = None,
) -> tuple[list[dict], dict[str, Any]]:
    """ИИ-чтение абстрактов по смыслу (без PXD/PDC в тексте)."""
    cfg = cfg or {}
    disc = cfg.get("discovery") or {}
    limit = max_llm if max_llm is not None else int(disc.get("abstract_llm_max") or 25)
    stats = {
        "llm_read": 0,
        "regex_only": 0,
        "atlas_fit_yes": 0,
        "atlas_fit_maybe": 0,
        "engines": {},
    }

    out: list[dict] = []
    for i, pub in enumerate(pubs):
        if i < limit and (pub.get("abstract") or "").strip():
            enriched = read_abstract_with_llm(pub, cfg=cfg, atlas_context=atlas_context)
            reader = enriched.get("abstract_reader", "")
            if reader.startswith("regex"):
                stats["regex_only"] += 1
            else:
                stats["llm_read"] += 1
                stats["engines"][reader] = stats["engines"].get(reader, 0) + 1
            fit = (enriched.get("abstract_ai") or {}).get("atlas_fit")
            if fit == "yes":
                stats["atlas_fit_yes"] += 1
            elif fit == "maybe":
                stats["atlas_fit_maybe"] += 1
        else:
            enriched = read_abstract_with_llm(
                {**pub},
                cfg={**cfg, "discovery": {**disc, "abstract_llm": False}},
                atlas_context=atlas_context,
            )
            stats["regex_only"] += 1
        out.append(enriched)
    return out, stats
