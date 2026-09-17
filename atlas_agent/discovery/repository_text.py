from __future__ import annotations

import json
import re
import time
from typing import Any, Callable

from atlas_agent.discovery.abstract_reader import _regex_extract
from atlas_agent.llm_client import DEFAULT_OLLAMA_MODEL, _run_llm, is_ollama_available
from atlas_agent.sources.literature import fetch_abstract

_PMID_CACHE: dict[str, dict] = {}
_SNIPPET_LEN = 420
_QWEN_SYS = "You curate a human TMT proteome atlas. Reply with ONLY valid JSON, no markdown."
_QWEN_PROMPT = """Title: {title}

Text from PubMed and/or PRIDE/PDC:
{text}

Decide sample material and atlas fit.
Atlas wants human tumor/adjacent/human tissue or a cancer cell line. Reject plasma/serum/urine-only, organoid-only, PDX-only, TMT6.

JSON:
{{"atlas_fit":"yes|maybe|no","material":"tumor tissue|adjacent normal|human tissue|cancer cell line|plasma|organoid|pdx|unclear","material_suitable":true,"summary_en":"one sentence","summary_ru":"одно предложение"}}"""


def _parse_qwen_json(raw: str) -> dict[str, Any]:
    text = str(raw or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", text, re.S)
        if not m:
            return {}
        try:
            parsed = json.loads(m.group(0))
        except json.JSONDecodeError:
            return {}
    return parsed if isinstance(parsed, dict) else {}


def _qwen_material_fit(title: str, text: str, *, cfg: dict | None = None) -> dict[str, Any] | None:
    if not is_ollama_available():
        return None
    llm_cfg = (cfg or {}).get("llm") or {}
    model = str(llm_cfg.get("model") or DEFAULT_OLLAMA_MODEL)
    prompt = _QWEN_PROMPT.format(title=(title or "")[:400], text=(text or "")[:2800])
    try:
        raw, engine, _usage = _run_llm(
            prompt,
            _QWEN_SYS,
            provider="ollama",
            model=model,
            base_url=llm_cfg.get("base_url") or "http://127.0.0.1:11434/v1",
            gpt4all_model=None,
            max_tokens=min(int(llm_cfg.get("max_tokens") or 400), 400),
            prefer_cloud=False,
        )
    except Exception:
        return None
    parsed = _parse_qwen_json(raw)
    if not parsed:
        return None
    material = str(parsed.get("material") or "unclear").strip().lower()
    if "|" in material:
        allowed = (
            "tumor tissue",
            "adjacent normal",
            "human tissue",
            "cancer cell line",
            "plasma",
            "organoid",
            "pdx",
        )
        hits = [p.strip() for p in material.split("|") if p.strip() in allowed]
        material = hits[0] if hits else "unclear"
    fit = str(parsed.get("atlas_fit") or "maybe").strip().lower()
    if fit not in ("yes", "maybe", "no"):
        fit = "maybe"
    parsed["material"] = material
    parsed["atlas_fit"] = fit
    parsed["reader"] = engine or "ollama"
    parsed["material_suitable"] = bool(parsed.get("material_suitable", True)) and material not in (
        "plasma", "serum", "blood", "organoid", "pdx", "unclear",
    )
    return parsed


def _clean_pmid(value: object) -> str:
    digits = re.sub(r"\D", "", str(value or ""))
    return digits if len(digits) >= 7 else ""


def _join_parts(*parts: object) -> str:
    out: list[str] = []
    seen: set[str] = set()
    for raw in parts:
        text = re.sub(r"\s+", " ", str(raw or "")).strip()
        if len(text) < 8:
            continue
        key = text[:80].lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(text)
    return " ".join(out)


def local_repository_text(item: dict[str, Any]) -> str:
    return _join_parts(
        item.get("abstract"),
        item.get("abstract_snippet"),
        item.get("description"),
        item.get("projectDescription"),
        item.get("sample_processing_protocol"),
        item.get("disease"),
        item.get("primary_site"),
        item.get("experiment_type"),
        item.get("program"),
        item.get("analytical_fraction"),
    )


def excerpt_source_label(item: dict[str, Any]) -> str:
    if str(item.get("abstract") or item.get("abstract_snippet") or "").strip() and item.get("pmid"):
        if item.get("excerpt_source") == "pubmed":
            return "pubmed"
    src = str(item.get("source") or "").lower()
    acc = str(item.get("accession") or item.get("project_accession") or "").upper()
    if acc.startswith("PDC") or src == "pdc_api" or item.get("consortium") == "PDC":
        return "pdc"
    if acc.startswith("PXD") or src.startswith("pride"):
        return "pride"
    if acc.startswith("MSV"):
        return "massive"
    if acc.startswith("IPX"):
        return "iprox"
    return "repository"


def attach_local_excerpt(item: dict[str, Any]) -> dict[str, Any]:
    text = local_repository_text(item)
    if text and not str(item.get("abstract_snippet") or "").strip():
        item["abstract_snippet"] = text[:_SNIPPET_LEN]
    if text and not str(item.get("abstract") or "").strip():
        item["abstract"] = text[:3500]
    item.setdefault("excerpt_source", excerpt_source_label(item))
    return item


def attach_pubmed_abstract(
    item: dict[str, Any],
    *,
    fetch_fn: Callable[[str], dict] | None = None,
    delay_s: float = 0.08,
) -> bool:
    pmid = _clean_pmid(item.get("pmid"))
    if not pmid:
        return False
    existing = str(item.get("abstract") or "").strip()
    if len(existing) >= 80 and item.get("excerpt_source") == "pubmed":
        return True
    getter = fetch_fn or fetch_abstract
    if pmid in _PMID_CACHE:
        meta = _PMID_CACHE[pmid]
    else:
        try:
            meta = getter(pmid) or {}
        except Exception:
            meta = {}
        if str(meta.get("abstract") or "").strip():
            _PMID_CACHE[pmid] = meta
        if fetch_fn is None and delay_s:
            time.sleep(delay_s)
    abstract = str(meta.get("abstract") or "").strip()
    if not abstract:
        return False
    item["pmid"] = pmid
    item["abstract"] = abstract[:3500]
    item["abstract_snippet"] = abstract[:_SNIPPET_LEN]
    item["excerpt_source"] = "pubmed"
    if meta.get("title") and not str(item.get("title") or "").strip():
        item["title"] = str(meta["title"])[:500]
    if meta.get("year") and not str(item.get("year") or "").strip():
        item["year"] = str(meta["year"])[:4]
    return True


def combined_reader_text(item: dict[str, Any]) -> str:
    return _join_parts(
        item.get("abstract"),
        item.get("abstract_snippet"),
        item.get("description"),
        item.get("sample_processing_protocol"),
        item.get("disease"),
        item.get("primary_site"),
        item.get("experiment_type"),
    )


def read_repository_material(
    item: dict[str, Any],
    *,
    cfg: dict | None = None,
    atlas_context: dict[str, Any] | None = None,
    use_llm: bool = False,
) -> dict[str, Any]:
    del atlas_context
    blob = combined_reader_text(item) or str(item.get("title") or "")
    title = str(item.get("title") or "")
    extra = str(item.get("sample_processing_protocol") or "")
    ai = _regex_extract(title, blob, extra)
    reader = "regex"
    if use_llm:
        qwen = _qwen_material_fit(title, blob, cfg=cfg)
        if qwen:
            ai = {**ai, **{k: v for k, v in qwen.items() if v not in (None, "", [])}}
            reader = str(qwen.get("reader") or "ollama")
    item["abstract_ai"] = {**(item.get("abstract_ai") or {}), **ai}
    item["abstract_reader"] = reader
    if ai.get("atlas_fit"):
        item["atlas_fit"] = ai.get("atlas_fit")
        item["atlas_fit_score"] = ai.get("atlas_fit_score")
    if ai.get("summary_en") and not str(item.get("abstract_snippet") or "").strip():
        item["abstract_snippet"] = str(ai["summary_en"])[:_SNIPPET_LEN]
    return item


def _material_unspecified(item: dict[str, Any]) -> bool:
    reasons = list(item.get("filter_reasons") or []) + list(item.get("qc_reasons") or [])
    return any("Material not specified" in str(r) for r in reasons)


def enrich_items_for_display(
    items: list[dict[str, Any]],
    *,
    cfg: dict | None = None,
    atlas_context: dict[str, Any] | None = None,
    fetch_pubmed: bool = True,
    use_llm: bool = False,
) -> int:
    filled = 0
    for item in items:
        got = False
        if fetch_pubmed:
            got = attach_pubmed_abstract(item)
        attach_local_excerpt(item)
        if not got and not str(item.get("abstract_snippet") or "").strip():
            continue
        read_repository_material(item, cfg=cfg, atlas_context=atlas_context, use_llm=use_llm)
        filled += 1
    return filled


def enrich_existing_report(
    report: dict[str, Any],
    catalog_index: dict[str, set[str]],
    *,
    cfg: dict | None = None,
    fetch_pubmed: bool = True,
    use_llm: bool = True,
) -> dict[str, int]:
    candidates = list(report.get("candidates") or report.get("new_projects") or [])
    display_n = enrich_items_for_display(
        candidates, cfg=cfg, fetch_pubmed=fetch_pubmed, use_llm=use_llm
    )
    enrich_items_for_display(
        report.get("repository_manual") or [],
        cfg=cfg,
        fetch_pubmed=fetch_pubmed,
        use_llm=use_llm,
    )
    buckets = {
        "recommended": candidates,
        "rejected": list(report.get("rejected_material") or []),
        "filtered_out": list(report.get("filtered_out") or []),
        "requires_manual_check": list(report.get("repository_manual") or []),
        "already_in_catalog": [],
        "duplicate_similar": [],
    }
    rescue = rescue_unspecified_material(
        buckets, catalog_index, cfg=cfg, fetch_pubmed=fetch_pubmed, use_llm=use_llm
    )
    report["candidates"] = buckets["recommended"]
    report["new_projects"] = buckets["recommended"]
    report["rejected_material"] = buckets["rejected"]
    report["filtered_out"] = buckets["filtered_out"]
    report["repository_manual"] = buckets["requires_manual_check"]
    summary = report.setdefault("summary", {})
    summary["candidates"] = len(buckets["recommended"])
    summary["new_projects"] = len(buckets["recommended"])
    summary["rejected_material"] = len(buckets["rejected"])
    summary["filtered_out"] = int(summary.get("filtered_out") or 0)
    summary["repository_manual"] = len(buckets["requires_manual_check"])
    summary["material_rescue"] = rescue
    rescue["display_filled"] = display_n
    return rescue


def rescue_unspecified_material(
    buckets: dict[str, list[dict]],
    catalog_index: dict[str, set[str]],
    *,
    cfg: dict | None = None,
    fetch_pubmed: bool = True,
    use_llm: bool = False,
) -> dict[str, int]:
    from atlas_agent.discovery.filters import classify_candidate, default_filter_config

    fcfg = {**default_filter_config(), **(cfg or {})}
    stats = {"inspected": 0, "rescued": 0, "still_rejected": 0, "qwen_read": 0}
    remaining: list[dict] = []
    for item in buckets.get("rejected") or []:
        if not _material_unspecified(item):
            remaining.append(item)
            continue
        stats["inspected"] += 1
        had_pubmed = False
        if fetch_pubmed:
            had_pubmed = attach_pubmed_abstract(item)
        else:
            had_pubmed = item.get("excerpt_source") == "pubmed" or len(str(item.get("abstract") or "")) >= 80
        if not had_pubmed:
            stats["still_rejected"] += 1
            remaining.append(item)
            continue
        attach_local_excerpt(item)
        read_repository_material(item, cfg=cfg, use_llm=False)
        out = classify_candidate(item, catalog_index, cfg=fcfg)
        if out.get("verdict") == "rejected" and _material_unspecified(out) and use_llm:
            read_repository_material(out, cfg=cfg, use_llm=True)
            stats["qwen_read"] += 1
            out = classify_candidate(out, catalog_index, cfg=fcfg)
        verdict = out.get("verdict") or "rejected"
        if verdict == "rejected" and _material_unspecified(out):
            stats["still_rejected"] += 1
            remaining.append(out)
            continue
        stats["rescued"] += 1
        if verdict == "recommended":
            buckets.setdefault("recommended", []).append(out)
        else:
            buckets.setdefault(verdict, []).append(out)
    buckets["rejected"] = remaining
    return stats
