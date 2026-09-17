"""
ИИ-чтение абстрактов по смыслу TMT ATLAS (Europe PMC).
Номера PXD/PDC в абстракте НЕ ищем — только смысл: human TMT proteomics у пациентов.
"""
from __future__ import annotations

import json
import re
from collections import Counter
from typing import Any

from atlas_agent.discovery.filters import (
    OFF_ATLAS_DISEASE,
    ONCOLOGY_HINT,
    PEPTIDE_ONLY_OMICS,
    PHOSPHOPROTEOMICS,
    PROTEIN_LEVEL_OMICS,
)
from atlas_agent.discovery.evaluation.sanitize import sanitize_summary
from atlas_agent.discovery.catalog_profile import format_atlas_context_for_llm
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
   (tissues: tumor / adjacent normal / human tissue; or human cancer cell lines)?
2) Do NOT search for or return PXD, PDC, MSV, IPX — repository IDs are usually absent.
3) Reject TMT6 or ≤6-plex; atlas accepts TMT/TMTpro with >6 channels (7–18, including TMT18).
4) Reject phosphoproteomics / phosphorylation profiling — atlas needs global protein-level proteome only.
5) Reject peptide-only quantification — need protein groups / proteome, not peptides.
6) Reject non-cancer disease cohorts (glaucoma, retinal detachment, cardiomyopathy, congenital metabolic, hydrocephalus) unless the study is a human cancer proteome.
7) Reject mouse/rat/chicken and mixed human+animal studies. Recombinant human protein in an animal model is not human.
8) Reject plasma/serum/urine/blood-only studies — atlas needs tissue or cell line.
9) FFPE tumor tissue is acceptable — do not reject FFPE when cancer/tumor/biopsy tissue is described.
10) Disease controls (e.g. patients without complication vs with complication) are NOT healthy controls — case-control disease comparisons are OK.
11) Reject microbiome/pathogen/bacteria-only proteomics unless human tumor tissue proteomics is also present.
12) In summary_ru use Russian words «статья», «абстракт», «проект» — never «пейсаж», «пейдж», «пакет».

Return a JSON object (no markdown) with fields:
{{
  "atlas_fit": "yes|maybe|no",
  "atlas_fit_score": 0.0,
  "semantic_evidence": ["short phrases from abstract"],
  "similar_atlas_theme": "e.g. colorectal tumor adjacent normal",
  "organism": "human|mouse|mixed|unclear",
  "tmt": "TMT10|TMT11|TMT12|TMT16|TMTpro16|TMTpro18|TMT7|TMT8|TMT9|ambiguous|none|unclear|TMT6",
  "material": "tumor tissue|adjacent normal|human tissue|cancer cell line|plasma|serum|blood|organoid|pdx|other|unclear",
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
    """True только для 6-plex и ниже — не для 16-plex."""
    label = str(tmt).upper()
    if label in ("TMT6", "TMT2", "TMT3", "TMT4", "TMT5", "6", "2"):
        return True
    m_pro = re.search(r"tmtpro\s*[- ]?(\d{1,2})", blob_l, re.I)
    m_tmt = re.search(r"tmt\s*[- ]?(\d{1,2})\b", blob_l, re.I)
    n = None
    if m_pro:
        n = int(m_pro.group(1))
    elif m_tmt:
        n = int(m_tmt.group(1))
    if n is not None:
        return n <= 6
    return bool(re.search(r"\btmt6\b|\btmt2\b|\b(?:2|6)-plex\b", blob_l, re.I))


def _regex_extract(title: str, abstract: str, extra: str = "") -> dict[str, Any]:
    blob = f"{title} {abstract} {extra}"
    blob_l = blob.lower()
    organism = "unclear"
    if re.search(r"\b(mouse|mice|murine|rat\b|chicken|gallus|zebrafish)\b", blob_l):
        if re.search(r"\b(human|homo sapiens|patients?)\b", blob_l):
            organism = "mixed"
        else:
            organism = "mouse"
    elif re.search(r"\b(human|homo sapiens|patients?)\b", blob_l) or re.search(
        r"\b((human|cancer|tumou?r)\s+cell\s+line|mcf[- ]?7|a549|hct116|hela)\b", blob_l
    ):
        organism = "human"
    tmt = "unclear"
    if re.search(r"\btmt\s*[- ]?6\b|\btmt6\b", blob_l, re.I):
        tmt = "TMT6"
    else:
        m_pro = re.search(r"tmtpro\s*[- ]?(\d{1,2})", blob_l, re.I)
        m_tmt = re.search(r"tmt\s*[- ]?(\d{1,2})", blob_l, re.I)
        if m_pro:
            tmt = f"TMTpro{m_pro.group(1)}"
        elif m_tmt:
            tmt = f"TMT{m_tmt.group(1)}"
        elif re.search(r"\b(tmt|tandem mass tag|isobaric)\b", blob_l):
            tmt = "ambiguous"
    material = "unclear"
    for label, pat in [
        ("organoid", r"\borganoid"),
        ("pdx", r"\b(pdx|xenograft)\b"),
        ("tumor tissue", r"\b(tumor tissue|ffpe|biopsy|tumou?r)\b"),
        ("cancer cell line", r"\b((cancer|human|tumou?r)\s+cell\s+line|mcf[- ]?7|a549|hct116|hela)\b"),
        ("human tissue", r"\b(human tissue|normal tissue|healthy tissue|tissue sample)\b"),
        ("plasma", r"\b(plasma|serum|urine|whole blood)\b"),
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
        evidence.append("TMT6 / ≤6-plex — не атлас (нужно >6 каналов)")
    elif OFF_ATLAS_DISEASE.search(blob) and not ONCOLOGY_HINT.search(blob):
        atlas_fit = "no"
        score = 0.1
        evidence.append("неонкологическая когорта — не атлас")
    elif PHOSPHOPROTEOMICS.search(blob):
        atlas_fit = "no"
        score = 0.1
        evidence.append("фосфопротеомика — нужен protein-level proteome")
    elif PEPTIDE_ONLY_OMICS.search(blob) and not PROTEIN_LEVEL_OMICS.search(blob):
        atlas_fit = "no"
        score = 0.1
        evidence.append("peptide-level — нужны белки (protein groups)")
    elif organism == "human" and re.search(
        r"\b(proteom\w*|mass\s+spectrom\w*|tmt\w*|isobaric|quantitative)\b", blob_l
    ):
        if re.search(r"\b(patients?|clinical|donor|cohort)\b", blob_l):
            evidence.append("human clinical proteomics")
            score = 0.55
            atlas_fit = "maybe"
        if tmt not in ("none", "unclear", "TMT6") and material not in ("organoid", "pdx", "plasma"):
            score = max(score, 0.65)
            atlas_fit = "maybe"
        if re.search(r"\b(tmt|isobaric)\b", blob_l) and re.search(
            r"\b(patients?|tumor|ffpe|tissue|cell\s+line)\b", blob_l
        ) and PROTEIN_LEVEL_OMICS.search(blob_l):
            score = 0.6
            atlas_fit = "maybe"
            evidence.append("TMT + patient samples (regex — conservative maybe)")
    if organism in ("mouse", "mixed") or material in ("organoid", "pdx", "plasma"):
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
        "human_suitable": organism == "human",
        "material_suitable": material not in ("organoid", "pdx", "plasma", "serum", "blood", "unclear"),
        "summary_ru": "",
        "reader": "regex",
    }


def _is_garbage_llm(parsed: dict[str, Any]) -> bool:
    """Reject local-model echo of prompt / schema boilerplate."""
    for key in ("summary_ru", "summary_en"):
        text = str(parsed.get(key) or "")
        if sanitize_summary(text):
            continue
        if text.strip():
            return True
    evidence = parsed.get("semantic_evidence") or []
    if not evidence and str(parsed.get("atlas_fit") or "").lower() == "yes":
        return True
    theme = str(parsed.get("similar_atlas_theme") or "").lower()
    if "json schema" in theme or "valid json" in theme:
        return True
    return False


def _fit_rank(fit: str) -> int:
    return {"no": 0, "maybe": 1, "yes": 2}.get(str(fit or "").lower(), 0)


def _min_fit(a: str, b: str) -> str:
    order = ("no", "maybe", "yes")
    ia, ib = _fit_rank(a), _fit_rank(b)
    return order[min(ia, ib)]


def _regex_summary_ru(regex: dict[str, Any], title: str) -> str:
    fit = regex.get("atlas_fit") or "no"
    evidence = regex.get("semantic_evidence") or []
    tmt = regex.get("tmt") or "?"
    material = regex.get("material") or "?"
    if fit == "no":
        if evidence:
            return f"Не подходит: {evidence[0]}."
        return "Не подходит по regex-правилам атласа."
    if fit == "maybe":
        ev = evidence[0] if evidence else "TMT + клинический контекст"
        return f"Возможно подходит ({ev}); TMT={tmt}, материал={material}."
    ev = evidence[0] if evidence else title[:80]
    return f"Похоже на атлас: {ev}; TMT={tmt}, материал={material}."


def _consensus_with_regex(
    regex: dict[str, Any],
    llm: dict[str, Any],
    *,
    engine: str,
) -> dict[str, Any]:
    """Conservative merge — regex anchors low-trust LLM."""
    from atlas_agent.discovery.evaluation.llm_evaluator import LLMEvaluatorRegistry
    from atlas_agent.discovery.evaluation.schemas import ModelTrustLevel

    trust = LLMEvaluatorRegistry().trust_for_engine(engine)
    merged = dict(llm)
    r_fit = str(regex.get("atlas_fit") or "no").lower()
    l_fit = str(llm.get("atlas_fit") or "no").lower()

    if trust in (ModelTrustLevel.LOW, ModelTrustLevel.RULES):
        # GPT4All / rules: LLM cannot override regex rejection
        merged["atlas_fit"] = _min_fit(l_fit, r_fit) if trust == ModelTrustLevel.LOW else r_fit
        if trust == ModelTrustLevel.LOW and merged["atlas_fit"] == "yes" and r_fit != "yes":
            merged["atlas_fit"] = "maybe" if r_fit == "maybe" else "no"
        try:
            r_score = float(regex.get("atlas_fit_score") or 0)
            l_score = float(llm.get("atlas_fit_score") or 0)
        except (TypeError, ValueError):
            r_score, l_score = 0.0, 0.0
        merged["atlas_fit_score"] = min(r_score or 0.55, l_score or 0.55) if merged["atlas_fit"] != "no" else min(r_score, l_score, 0.35)
    elif trust == ModelTrustLevel.MEDIUM:
        merged["atlas_fit"] = _min_fit(l_fit, r_fit)
        if merged["atlas_fit"] == "yes" and r_fit == "no":
            merged["atlas_fit"] = "maybe"
        try:
            r_score = float(regex.get("atlas_fit_score") or 0)
            l_score = float(llm.get("atlas_fit_score") or 0)
        except (TypeError, ValueError):
            r_score, l_score = 0.0, 0.0
        merged["atlas_fit_score"] = max(r_score, l_score * 0.85) if merged["atlas_fit"] != "no" else min(r_score, l_score, 0.4)
    else:
        merged["atlas_fit"] = _min_fit(l_fit, r_fit)
        try:
            merged["atlas_fit_score"] = min(
                float(llm.get("atlas_fit_score") or 0.7),
                max(float(regex.get("atlas_fit_score") or 0.0), 0.0) + 0.15,
            )
        except (TypeError, ValueError):
            merged["atlas_fit_score"] = regex.get("atlas_fit_score")

    if _is_garbage_llm(merged):
        merged["atlas_fit"] = regex.get("atlas_fit", "no")
        merged["atlas_fit_score"] = regex.get("atlas_fit_score")
        merged["semantic_evidence"] = regex.get("semantic_evidence") or []
        merged["summary_ru"] = _regex_summary_ru(regex, "")
        merged["summary_en"] = merged["summary_ru"]
        merged["reader"] = f"{engine}_regex_fallback"
    elif not sanitize_summary(merged.get("summary_ru")):
        merged["summary_ru"] = _regex_summary_ru(regex, "")
        merged["summary_en"] = merged["summary_ru"]

    merged["model_trust"] = trust.value
    merged["regex_fit"] = r_fit
    return merged


def _normalize_ai_parsed(parsed: dict[str, Any]) -> dict[str, Any]:
    fit = str(parsed.get("atlas_fit") or "no").lower()
    tmt = str(parsed.get("tmt") or "unclear")
    if _tmt6_or_low_plex("", tmt):
        fit = "no"
    organism = str(parsed.get("organism") or "unclear")
    if organism.lower() in ("mouse", "mixed", "rat"):
        fit = "no"
    material = str(parsed.get("material") or "unclear")
    if material.lower() in ("plasma", "serum", "blood"):
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
    material_ok = material.lower() not in ("organoid", "pdx", "plasma", "serum", "blood", "unclear")

    return {
        "atlas_fit": fit,
        "atlas_fit_score": score,
        "semantic_evidence": list(parsed.get("semantic_evidence") or [])[:8],
        "similar_atlas_theme": str(parsed.get("similar_atlas_theme") or "")[:120],
        "accessions": dict(_EMPTY_ACCESSIONS),
        "organism": organism,
        "tmt": tmt,
        "material": material,
        "human_suitable": organism.lower() == "human" and bool(parsed.get("human_suitable", True)),
        "material_suitable": bool(parsed.get("material_suitable", True)) and material_ok,
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
    from atlas_agent.llm_client import DEFAULT_OLLAMA_MODEL

    ollama_model = llm_cfg.get("model") or DEFAULT_OLLAMA_MODEL
    if resolve_engine(
        provider,
        llm_cfg.get("base_url"),
        prefer_cloud=prefer_cloud,
        model=ollama_model,
    ) == "local_rules":
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
    regex_base = _regex_extract(title, abstract, data_avail)

    from atlas_agent.discovery.evaluation.heuristics import has_hard_exclusion, scan_literature_text

    if has_hard_exclusion(scan_literature_text(title, abstract)):
        regex_base["atlas_fit"] = "no"
        regex_base["reader"] = "exclusion_engine"
        out = dict(pub)
        out["abstract_ai"] = regex_base
        out["abstract_reader"] = "exclusion_engine"
        out["atlas_fit"] = "no"
        from atlas_agent.discovery.fit_rules import apply_literature_exclusions

        return apply_literature_exclusions(out)

    if not abstract.strip():
        ai = regex_base
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
            parsed = dict(regex_base)
            parsed["reader"] = f"{engine}_parse_fail"
        else:
            parsed = _normalize_ai_parsed(parsed)
            parsed = _consensus_with_regex(regex_base, parsed, engine=engine)
            parsed["reader"] = parsed.get("reader") or engine
    except Exception as exc:
        parsed = dict(regex_base)
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
