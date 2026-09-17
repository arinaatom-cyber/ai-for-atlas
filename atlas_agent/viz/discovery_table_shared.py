"""Shared row builders for Discovery tables (GitHub + Streamlit)."""
from __future__ import annotations

import html
import re

from atlas_agent.discovery.evaluation import AnalysisFormatter, display_fit_label
from atlas_agent.viz.i18n_defaults import en as i18n_default
from atlas_agent.discovery.evaluation.context import EvaluationContext
from atlas_agent.discovery.evaluation.schemas import ItemKind, ProjectEvaluation
from atlas_agent.discovery.evaluation.stale import should_recompute_evaluation
from atlas_agent.discovery.fit_rules import (
    cohort_verdict,
    is_cohort_excluded,
    literature_verdict,
    project_verdict,
)
from atlas_agent.discovery.evaluation.sanitize import sanitize_summary
from atlas_agent.viz.display_format import format_design_label, format_metadata_part, sentence_cap
from atlas_agent.viz.portal_index import (
    article_description,
    europe_pmc_url,
    pubmed_url,
    repository_url,
    resolve_publication_links,
)

_FORMATTER = AnalysisFormatter()
_TABLE_CTX: EvaluationContext | None = None


def _table_context() -> EvaluationContext:
    global _TABLE_CTX
    if _TABLE_CTX is None:
        _TABLE_CTX = EvaluationContext.create(catalog_df=None)
    return _TABLE_CTX


def _resolve_evaluation(
    item: dict,
    *,
    kind: ItemKind | str,
    has_accession: bool = False,
) -> ProjectEvaluation:
    """Use enriched evaluation from latest.json; re-score stale project rows."""
    force = should_recompute_evaluation(item, kind)
    return _table_context().resolve(
        item,
        kind=kind,
        has_accession=has_accession,
        mutate=force or not item.get("evaluation"),
    )


def _esc(s: object) -> str:
    return html.escape(str(s or ""))


_REPO_PREFIXES = ("PXD", "PDC", "MSV", "IPX")


def _is_repo_accession(acc: str) -> bool:
    a = str(acc or "").strip().upper()
    return any(a.startswith(p) for p in _REPO_PREFIXES)


def source_label(item: dict) -> str:
    acc = (item.get("project_accession") or item.get("accession") or "").upper()
    if _is_repo_accession(acc):
        src = item.get("source") or item.get("consortium") or ""
        if acc.startswith("PDC") or src == "pdc_api":
            return "PDC"
        if acc.startswith("PXD") or "pride" in str(src).lower():
            return "PRIDE"
        if acc.startswith("MSV"):
            return "MassIVE"
        if acc.startswith("IPX"):
            return "iProX"
    src = str(item.get("source") or "").lower()
    if "europe" in src or "literature" in src or "epmc" in src:
        return "Europe PMC"
    return "Europe PMC"


def fit_class(fit: str) -> str:
    return {"yes": "fit-yes", "maybe": "fit-maybe", "no": "fit-no"}.get(str(fit).lower(), "fit-unk")


def weight_badge(fit: str, score: object) -> str:
    fit_s = str(fit or "?").strip()
    score_s = str(score or "").strip()
    label = f"{fit_s} ({score_s})" if score_s else fit_s
    return f'<span class="badge {fit_class(fit_s)}">{_esc(label)}</span>'


def _confidence_cell(tier: str, css: str, bullets: list[str]) -> str:
    if not tier:
        return '<span class="cell-empty">—</span>'
    tip = "; ".join(bullets[:4])
    t = f' title="{_esc(tip)}"' if tip else ""
    body = f'<span class="badge tier-badge {css}"{t}><b>{_esc(tier)}</b></span>'
    return body


def _i18n_badge(key: str, css: str, *, title: str = "", title_key: str = "") -> str:
    t_attr = ""
    if title_key:
        t_attr = f' data-i18n-title="{_esc(title_key)}"'
    elif title:
        t_attr = f' title="{_esc(title)}"'
    text = _esc(i18n_default(key))
    return f'<span class="badge {css}" data-i18n="{_esc(key)}"{t_attr}>{text}</span>'


def _verdict_badge(label: str, css: str, title: str = "") -> str:
    key_map = {
        "Candidate": "verdict_candidate",
        "Watch": "verdict_watch",
        "Exclude": "verdict_exclude",
        "Review": "verdict_review",
    }
    i18n_key = key_map.get(label)
    if i18n_key:
        return _i18n_badge(i18n_key, css, title=title)
    t = f' title="{_esc(title)}"' if title else ""
    return f'<span class="badge {css}"{t}>{_esc(label)}</span>'


def _type_badge(kind: str) -> str:
    keys = {"project": "badge_project", "paper": "badge_paper", "cohort": "badge_cohort"}
    css = {"project": "badge-ok", "paper": "badge-muted", "cohort": "badge-warn"}.get(kind, "badge-muted")
    return _i18n_badge(keys.get(kind, "badge_paper"), css)


def unified_weight_cell(
    *,
    evaluation: ProjectEvaluation | None = None,
    fit: str = "",
    cohort_score: object = None,
) -> str:
    """LLM verdict label + optional cohort score 0–100."""
    parts: list[str] = []
    fit_s = str(fit or "").strip().lower()
    label = (evaluation.display_fit_label if evaluation else "") or ""
    if not label and fit_s in ("yes", "maybe", "no"):
        label = display_fit_label({"atlas_fit": fit_s}, evaluation)
    if label:
        fit_key = f"fit_llm_{fit_s}" if fit_s in ("yes", "maybe", "no") else ""
        if fit_key:
            fit_text = _esc(i18n_default(fit_key))
            hint = _esc(i18n_default("fit_llm_hint"))
            parts.append(
                f'<span class="badge {fit_class(fit_s)}" data-i18n="{fit_key}" '
                f'data-i18n-title="fit_llm_hint" title="{hint}">{fit_text}</span>'
            )
        else:
            parts.append(f'<span class="badge {fit_class(fit_s)}">{_esc(label)}</span>')
    if cohort_score not in (None, ""):
        score_text = _esc(
            i18n_default("badge_cohort_score").replace("{n}", str(cohort_score)).replace("{score}", str(cohort_score))
        )
        hint = _esc(i18n_default("badge_cohort_hint"))
        parts.append(
            f'<span class="badge badge-muted" data-i18n="badge_cohort_score" '
            f'data-i18n-title="badge_cohort_hint" title="{hint}" '
            f'data-i18n-suffix="{_esc(cohort_score)}">{score_text}</span>'
        )
    if not parts:
        return '<span class="cell-empty">—</span>'
    return " ".join(parts)


def score_badge(score: object) -> str:
    s = str(score or "").strip() or "—"
    return f'<span class="badge badge-muted">{_esc(s)}</span>'


def pubmed_link(pmid: str, *, label: str | None = None) -> str:
    if not pmid:
        return ""
    url = pubmed_url(pmid)
    text = label or pmid
    return f'<a href="{_esc(url)}" target="_blank" rel="noopener" class="link-pub">{_esc(text)}</a>'


def epmc_link(pmid: str) -> str:
    if not pmid:
        return ""
    return (
        f'<a href="{_esc(europe_pmc_url(pmid))}" target="_blank" rel="noopener" '
        f'class="link-epmc cell-src"><b data-i18n="link_epmc"></b></a>'
    )


def project_link(acc: str, repo: str) -> str:
    if not repo:
        return ""
    return f'<a href="{_esc(repo)}" target="_blank" rel="noopener" class="link-repo">Project</a>'


def links_cell(*parts: str) -> str:
    body = " · ".join(p for p in parts if p)
    return body or '<span class="cell-empty">—</span>'


def _parse_year(value: object) -> str:
    m = re.search(r"(19|20)\d{2}", str(value or ""))
    return m.group(0) if m else ""


def item_year(item: dict, pubs_by_pmid: dict[str, dict] | None = None) -> str:
    """Year from PRIDE/PDC dates, paper metadata, or linked PMID."""
    for key in ("publication_date", "submission_date", "pub_date", "published"):
        y = _parse_year(item.get(key))
        if y:
            return y
    y = _parse_year(item.get("year"))
    if y:
        return y
    pmid = _norm_pmid(item)
    if pmid and pubs_by_pmid:
        pub = pubs_by_pmid.get(pmid) or {}
        y = _parse_year(pub.get("year"))
        if y:
            return y
    return "—"


def _is_cohort_item(item: dict) -> bool:
    return item.get("cohort_score") is not None


def _item_summaries(item: dict, pubs_by_pmid: dict[str, dict]) -> tuple[str, str]:
    pmid = str(item.get("pmid") or "").strip()
    pub = pubs_by_pmid.get(pmid) if pmid else None
    ai = item.get("abstract_ai") or {}
    if _is_cohort_item(item):
        en = str(item.get("abstract_snippet") or item.get("abstract") or item.get("description_en") or "")
        ru = str(item.get("description_ru") or "")
        return sanitize_summary(en.strip()), sanitize_summary(ru.strip())
    en = str(
        (pub or {}).get("summary_en")
        or ai.get("summary_en")
        or item.get("summary_en")
        or item.get("description_en")
        or item.get("article_description")
        or item.get("description")
        or item.get("abstract_snippet")
        or ""
    )
    ru = str(
        (pub or {}).get("summary_ru")
        or ai.get("summary_ru")
        or item.get("summary_ru")
        or item.get("description_ru")
        or ""
    )
    return en, ru


def _item_summary(item: dict, pubs_by_pmid: dict[str, dict]) -> str:
    en, ru = _item_summaries(item, pubs_by_pmid)
    return en or ru


def _coerce_evaluation(
    item: dict,
    *,
    kind: ItemKind | str,
    has_accession: bool = False,
) -> ProjectEvaluation | None:
    """Parse stored evaluation or compute; None triggers legacy fallback."""
    raw = item.get("evaluation")
    if raw is not None:
        if isinstance(raw, str):
            return None
        if isinstance(raw, dict):
            if "evidence_chain" not in raw:
                return None
            try:
                return ProjectEvaluation.model_validate(raw)
            except Exception:
                return None
    try:
        return _resolve_evaluation(item, kind=kind, has_accession=has_accession)
    except Exception:
        return None


def _render_analysis_cell(
    item: dict,
    *,
    kind: ItemKind | str,
    has_accession: bool = False,
    pubs_by_pmid: dict[str, dict],
) -> str:
    """Analysis column — delegated to AnalysisFormatter with legacy guard."""
    evaluation = _coerce_evaluation(item, kind=kind, has_accession=has_accession)
    if evaluation is None:
        inner = _FORMATTER.legacy_html()
    else:
        en, ru = _item_summaries(item, pubs_by_pmid)
        inner = _FORMATTER.to_html(evaluation, summary=en, summary_ru=ru)
    return f'<div class="cell-stack cell-analysis">{inner}</div>'


def _badge_stack(*badges: str) -> str:
    rows = [b for b in badges if b]
    if not rows:
        return ""
    return f'<div class="badge-stack">{"".join(rows)}</div>'


def _link_chip(href: str, label: str, *, i18n_key: str = "") -> str:
    if not href:
        return ""
    inner = f'<span data-i18n="{_esc(i18n_key)}"></span>' if i18n_key else _esc(label)
    return f'<a href="{_esc(href)}" target="_blank" rel="noopener" class="link-chip">{inner}</a>'


def _links_stack(chips: list[str]) -> str:
    rows = [c for c in chips if c]
    if not rows:
        return (
            '<div class="cell-stack cell-links">'
            '<span class="cell-empty">—</span>'
            "</div>"
        )
    body = "".join(f'<div class="link-row">{c}</div>' for c in rows)
    return f'<div class="cell-stack cell-links"><div class="link-stack">{body}</div></div>'


def _project_links(acc: str, repo: str, pmid: str) -> str:
    chips: list[str] = []
    if pmid:
        chips.append(_link_chip(pubmed_url(pmid), f"PMID {pmid}"))
        chips.append(_link_chip(europe_pmc_url(pmid), "", i18n_key="link_epmc"))
    return _links_stack(chips)


def _literature_links(acc: str, repo: str, pmid: str) -> str:
    chips: list[str] = []
    if pmid:
        chips.append(_link_chip(pubmed_url(pmid), f"PMID {pmid}"))
        chips.append(_link_chip(europe_pmc_url(pmid), "", i18n_key="link_epmc"))
    if repo and acc and not _is_repo_accession(acc):
        src = source_label({"accession": acc})
        chips.append(_link_chip(repo, f"{src} {acc}".strip()))
    return _links_stack(chips)


def _data_status_key(status: str) -> str:
    return {
        "quant_table": "data_quant_table",
        "local_mirror": "data_local_mirror",
        "maybe_table": "data_maybe_table",
        "processed_psm": "data_psm_only",
        "phospho_table": "data_phospho_only",
        "raw_only": "data_raw_only",
        "no_files": "data_no_files",
    }.get(status, "")


def _norm_pmid(item: dict) -> str:
    return re.sub(r"\D", "", str(item.get("pmid") or ""))


def _first_accession(item: dict) -> str:
    for key in ("project_accession", "accession"):
        a = str(item.get(key) or "").strip().upper()
        if _is_repo_accession(a):
            return a
    for key in ("accessions_mentioned", "pxd_mentioned"):
        for acc in item.get(key) or []:
            a = str(acc).strip().upper()
            if _is_repo_accession(a):
                return a
    ai = item.get("abstract_ai") or {}
    for group in (ai.get("accessions") or {}).values():
        for acc in group or []:
            a = str(acc).strip().upper()
            if _is_repo_accession(a):
                return a
    return ""


def _fit_score_fmt(score: object) -> str:
    if score in (None, ""):
        return ""
    try:
        return f"{float(score):.2f}".rstrip("0").rstrip(".")
    except (TypeError, ValueError):
        return str(score)


def _omics_cell(item: dict) -> str:
    omics = item.get("omics") or []
    if not omics:
        return '<span class="cell-empty" data-i18n="cell_empty"></span>'
    keys = {
        "proteomics": "omics_proteomics",
        "phosphoproteomics": "omics_phospho",
        "transcriptomics": "omics_transcriptomics",
        "genomics": "omics_genomics",
        "metabolomics": "omics_metabolomics",
        "lipidomics": "omics_lipidomics",
        "glycoproteomics": "omics_glycoproteomics",
        "multi_omics": "omics_multi",
    }
    parts: list[str] = []
    for o in omics[:6]:
        key = keys.get(o)
        if key:
            parts.append(f'<span data-i18n="{key}"></span>')
        else:
            parts.append(_esc(str(o)))
    return ", ".join(parts)


def _patient_cell(item: dict) -> str:
    hp = item.get("has_patients") or ""
    if hp == "yes":
        return _i18n_badge("pat_yes", "badge-ok")
    if hp == "maybe":
        return _i18n_badge("pat_maybe", "badge-warn")
    if hp == "no":
        return _i18n_badge("pat_no", "badge-bad")
    return '<span class="cell-empty" data-i18n="cell_empty"></span>'


def _num_cell(n: int) -> str:
    return f'<td class="col-num cell-mono"><b>{n}</b></td>'


def _disease_cell(item: dict) -> str:
    d = str(item.get("disease") or "").strip()
    if not d:
        d = str((item.get("abstract_ai") or {}).get("disease") or "").strip()
    if not d:
        return '<span class="cell-empty">—</span>'
    parts = [_esc(format_metadata_part(x)) for x in re.split(r"[;/|]", d) if x.strip()]
    return ", ".join(parts[:3]) if parts else '<span class="cell-empty">—</span>'


def _organ_cell(item: dict) -> str:
    o = str(item.get("primary_site") or item.get("organ") or item.get("tissue") or "").strip()
    if not o:
        o = str((item.get("abstract_ai") or {}).get("organ") or "").strip()
    if not o:
        return '<span class="cell-empty">—</span>'
    parts = [_esc(format_metadata_part(x)) for x in re.split(r"[;/|]", o) if x.strip()]
    return ", ".join(parts[:3]) if parts else '<span class="cell-empty">—</span>'


def _tmt_plex_unspecified(item: dict) -> bool:
    if item.get("tmt_plex_unspecified"):
        return True
    blob = " ".join(str(x) for x in (item.get("filter_reasons") or []))
    if "tmt_plex_unspecified" in blob or "plex not in metadata" in blob:
        return True
    acc = str(item.get("accession") or item.get("project_accession") or "").upper()
    src = str(item.get("source") or "").lower()
    if (acc.startswith("PXD") or src.startswith("pride")) and item.get("tmt_detected"):
        return not bool(item.get("inferred_plex") or item.get("tmt_label"))
    return False


def _design_cell(item: dict) -> str:
    design = _esc(format_design_label(item.get("sample_design") or "—"))
    bits = [f'<span class="cell-design-label">{design}</span>']
    label = str(item.get("tmt_label") or "").strip()
    if label:
        bits.append(f'<span class="badge badge-muted">{_esc(label)}</span>')
    if _tmt_plex_unspecified(item):
        bits.append(_i18n_badge("tmt_plex_unspecified", "badge-warn", title_key="tmt_plex_unspecified_hint"))
    return f'<div class="cell-stack cell-design-block">{"".join(bits)}</div>'


def _abstract_cell(item: dict) -> str:
    snip = (
        item.get("abstract_snippet")
        or item.get("abstract")
        or (item.get("abstract_ai") or {}).get("summary_en")
        or (item.get("abstract_ai") or {}).get("summary_ru")
        or ""
    )
    snip = sentence_cap(re.sub(r"\s+", " ", str(snip).strip()))
    if not snip:
        return '<span class="cell-empty">—</span>'
    return f'<p class="cell-abstract" title="{_esc(snip[:400])}">{_esc(snip[:220])}</p>'


def _similar_cell(item: dict) -> str:
    sim = item.get("similar_in_catalog") or []
    if not sim:
        return '<span class="cell-empty">—</span>'
    chips: list[str] = []
    seen: set[str] = set()
    for hit in sim[:3]:
        pid = str(hit.get("project_id") or "").strip().upper()
        if not pid or pid in seen:
            continue
        seen.add(pid)
        score = hit.get("score")
        try:
            score_s = f"{float(score):.0%}" if score is not None else ""
        except (TypeError, ValueError):
            score_s = str(score or "").strip()
        label = f"{pid} · {score_s}" if score_s else pid
        repo = repository_url(pid)
        chips.append(_link_chip(repo, label) if repo else f'<span class="badge badge-muted">{_esc(label)}</span>')
    return _links_stack(chips) if chips else '<span class="cell-empty">—</span>'


def _data_cell(it: dict) -> str:
    da = it.get("data_availability") or {}
    if isinstance(da, dict) and da:
        status = da.get("status") or "unknown"
        status_key = _data_status_key(status)
        cls = {
            "quant_table": "badge-ok",
            "local_mirror": "badge-ok",
            "maybe_table": "badge-warn",
            "processed_psm": "badge-warn",
            "phospho_table": "badge-bad",
            "raw_only": "badge-bad",
            "no_files": "badge-bad",
        }.get(status, "badge-muted")
        layer = str(da.get("omics_layer") or "")
        if status_key:
            status_badge = _i18n_badge(status_key, cls)
        else:
            status_badge = f'<span class="badge {cls}">{_esc(str(da.get("label") or status))}</span>'
        mixed_badge = (
            _i18n_badge("data_mixed_protein_phospho", "badge-warn", title_key="data_mixed_hint")
            if layer == "mixed"
            else ""
        )
        samples = da.get("proteome_files") or da.get("quant_files") or da.get("sample_files") or []
        fname = _esc(samples[0][:64]) if samples else ""
        body = '<div class="cell-stack cell-data">'
        body += _badge_stack(status_badge, mixed_badge)
        if fname:
            body += f'<code class="file-name" title="{fname}">{fname}</code>'
        guidance = str(da.get("guidance") or "").strip()
        if guidance and not fname:
            body += f'<span class="muted file-hint">{_esc(guidance[:90])}</span>'
        body += "</div>"
        return body
    hint = str(it.get("data_hint") or it.get("data_availability") or "").strip()
    if hint:
        return (
            f'<div class="cell-stack">'
            f'<span class="cell-label" data-i18n="th_data"></span>'
            f'<span class="badge badge-warn">{_esc(hint[:90])}</span>'
            f"</div>"
        )
    return (
        '<div class="cell-stack">'
        '<span class="cell-label" data-i18n="th_data"></span>'
        '<span class="cell-empty" data-i18n="cell_empty"></span>'
        "</div>"
    )


def _source_link_cell(it: dict, *, acc: str = "", pmid: str = "") -> str:
    acc = acc or _first_accession(it)
    if acc and _is_repo_accession(acc):
        return '<span class="cell-empty">—</span>'
    label = source_label(it) if acc else "Europe PMC"
    if acc:
        repo = it.get("repository_url") or it.get("url") or repository_url(acc)
        if repo:
            return (
                f'<a href="{_esc(repo)}" target="_blank" rel="noopener" class="cell-src">'
                f"<b>{_esc(label)}</b></a>"
            )
        return f'<span class="cell-src"><b>{_esc(label)}</b></span>'
    return epmc_link(pmid) if pmid else '<span class="cell-empty">—</span>'


def _id_cell(*, acc: str, repo: str, pmid: str) -> str:
    if acc:
        kind = source_label({"accession": acc})
        acc_esc = _esc(acc)
        if repo:
            repo_link = (
                f'<a href="{_esc(repo)}" target="_blank" rel="noopener" class="cell-src">'
                f"<b>{_esc(kind)}</b></a>"
            )
        else:
            repo_link = f'<span class="cell-src"><b>{_esc(kind)}</b></span>'
        body = (
            f"{repo_link}"
            f'<span class="cell-mono id-acc"><b>{acc_esc}</b></span>'
        )
        return f'<div class="cell-stack id-cell">{body}</div>'
    no_acc = '<span class="id-no-acc" data-i18n="no_accession"></span>'
    return (
        f'<div class="cell-stack id-cell">'
        f'<span class="cell-label" data-i18n="badge_paper"></span>{no_acc}</div>'
    )


def _title_cell(
    title: str,
    pub_url: str,
    repo: str,
    *,
    description: str = "",
    acc: str = "",
) -> str:
    title_esc = _esc(sentence_cap(title[:180] or "—"))
    href = ""
    if repo and acc and _is_repo_accession(acc):
        href = repo
    elif pub_url:
        href = pub_url
    if href:
        head = f'<a href="{_esc(href)}" target="_blank" rel="noopener" class="cell-title">{title_esc}</a>'
    else:
        head = f'<span class="cell-title">{title_esc}</span>'
    bits = [head]
    desc = (description or "").strip()
    if desc:
        bits.append(f'<p class="cell-desc">{_esc(sentence_cap(desc[:320]))}</p>')
    return f'<div class="cell-stack cell-title-block">{"".join(bits)}</div>'


def _papers_without_accession(manual: list[dict], literature: list[dict]) -> list[dict]:
    seen: set[str] = set()
    out: list[dict] = []
    for item in manual + literature:
        pmid = _norm_pmid(item)
        key = pmid or str(item.get("title") or "")[:80]
        if key in seen:
            continue
        seen.add(key)
        out.append(item)
    return out


def _merge_literature(papers: list[dict], cohorts: list[dict]) -> list[dict]:
    """Merge papers and cohorts by PMID into unified literature rows."""
    by_pmid: dict[str, dict] = {}
    order: list[str] = []

    for p in papers:
        pmid = _norm_pmid(p)
        key = pmid or f"paper:{str(p.get('title') or '')[:60]}"
        if key not in by_pmid:
            order.append(key)
            by_pmid[key] = {"paper": p, "cohort": None}
        else:
            by_pmid[key]["paper"] = p

    for c in cohorts:
        pmid = _norm_pmid(c)
        key = pmid or f"cohort:{str(c.get('title') or '')[:60]}"
        if key in by_pmid:
            by_pmid[key]["cohort"] = c
        else:
            order.append(key)
            by_pmid[key] = {"paper": None, "cohort": c}

    rows = []
    for key in order:
        entry = by_pmid[key]
        paper = entry.get("paper")
        cohort = entry.get("cohort")
        base = dict(cohort or paper or {})
        if paper and cohort:
            merged = {**paper, **{k: v for k, v in cohort.items() if v not in (None, "", [])}}
            merged["abstract_ai"] = paper.get("abstract_ai") or {}
            merged["cohort_score"] = cohort.get("cohort_score")
            merged["omics"] = cohort.get("omics") or []
            merged["has_patients"] = cohort.get("has_patients")
            merged["patient_n"] = cohort.get("patient_n")
            merged["description_en"] = cohort.get("description_en")
            base = merged
        rows.append({"paper": paper, "cohort": cohort, "item": base, "kind": _literature_kind(paper, cohort)})
    return rows


def _literature_kind(paper: dict | None, cohort: dict | None) -> str:
    if paper and cohort:
        return "cohort"
    if cohort:
        return "cohort"
    return "paper"


def build_unified_discovery_rows(
    projects: list[dict],
    papers: list[dict],
    cohorts: list[dict],
    pubs_by_pmid: dict[str, dict],
) -> tuple[str, int]:
    """One tbody for GitHub Discovery: projects + literature + cohorts."""
    rows: list[str] = []
    total = 0
    row_num = 0

    for it in projects:
        row_num += 1
        resolve_publication_links(it, fetch_pride_pmid=False)
        raw_acc = _first_accession(it)
        repo = it.get("repository_url") or it.get("url") or repository_url(raw_acc)
        pmid = str(it.get("pmid") or "").strip()
        pub = it.get("pubmed_url") or pubmed_url(pmid)
        title = (it.get("title") or "").strip()
        desc = article_description(it)
        year = item_year(it, pubs_by_pmid)
        design_cell = _design_cell(it)
        src_key = source_label(it).lower()
        search = f"{raw_acc} {title} {pmid} {desc} {year} {it.get('program') or ''}".lower()

        evaluation = _resolve_evaluation(it, kind=ItemKind.PROJECT)
        vlabel, vcss, vtitle = project_verdict(it)
        verdict_cell = _verdict_badge(vlabel, vcss, vtitle)
        tier = it.get("confidence_tier") or evaluation.confidence
        conf_cell = _confidence_cell(tier, it.get("confidence_css") or evaluation.confidence_css, evaluation.confidence_bullets)

        rows.append(
            f"<tr data-type='project' data-src='{src_key}' data-search='{_esc(search)}' data-patients='' data-tier='{_esc(tier)}'>"
            f"{_num_cell(row_num)}"
            f"<td class='col-type'>{_type_badge('project')}</td>"
            f"<td class='col-id'>{_id_cell(acc=raw_acc, repo=repo, pmid=pmid)}</td>"
            f"<td class='col-year cell-mono'><b>{_esc(year)}</b></td>"
            f"<td class='col-title'>{_title_cell(title, pub, repo, description=desc, acc=raw_acc)}</td>"
            f"<td class='col-disease'>{_disease_cell(it)}</td>"
            f"<td class='col-organ'>{_organ_cell(it)}</td>"
            f"<td class='col-src col-split'>{_source_link_cell(it, acc=raw_acc)}</td>"
            f"<td class='col-design'>{design_cell}</td>"
            f"<td class='col-verdict col-split'>{verdict_cell}</td>"
            f"<td class='col-confidence'>{conf_cell}</td>"
            f"<td class='col-similar'>{_similar_cell(it)}</td>"
            f"<td class='col-abstract'>{_abstract_cell(it)}</td>"
            f"<td class='col-weight'><span class='cell-empty'>—</span></td>"
            f"<td class='col-analysis analysis-cell'>{_render_analysis_cell(it, kind=ItemKind.PROJECT, pubs_by_pmid=pubs_by_pmid)}</td>"
            f"<td class='col-data'>{_data_cell(it)}</td>"
            f"<td class='col-links'>{_project_links(raw_acc, repo, pmid)}</td>"
            f"</tr>"
        )
        total += 1

    lit_rows = _merge_literature(papers, cohorts)
    for entry in lit_rows:
        row_num += 1
        it = entry["item"]
        resolve_publication_links(it, fetch_pride_pmid=False)
        paper = entry.get("paper")
        cohort = entry.get("cohort")
        kind = entry["kind"]
        pmid = _norm_pmid(it)
        pub = pubmed_url(pmid)
        acc = _first_accession(it)
        repo = it.get("repository_url") or (repository_url(acc) if acc else "")
        title = (it.get("title") or "").strip()
        year = item_year(it if paper else (cohort or it), pubs_by_pmid)
        if year == "—" and cohort:
            year = item_year(cohort, pubs_by_pmid)
        design = "—"
        if paper:
            mat = (paper.get("abstract_ai") or {}).get("material") or ""
            if mat and mat != "unclear":
                design = _esc(str(mat).replace("|", ", ")[:60])
        fit = ""
        if paper:
            fit = paper.get("atlas_fit") or (paper.get("abstract_ai") or {}).get("atlas_fit") or ""
        cohort_score = (cohort or it).get("cohort_score")
        hp = it.get("has_patients") or ""
        desc = article_description(it)
        search = f"{title} {pmid} {acc} {desc}".lower()

        if kind == "cohort" and is_cohort_excluded(title, str(it.get("abstract") or "")):
            vlabel, vcss, vtitle = ("Exclude", "badge-bad", "Review / software / narrative")
        elif kind == "cohort":
            vlabel, vcss, vtitle = cohort_verdict(it)
        elif paper:
            vlabel, vcss, vtitle = literature_verdict(paper, has_accession=bool(acc))
        else:
            vlabel, vcss, vtitle = ("Watch", "badge-warn", "Literature surveillance")

        lit_kind = ItemKind.LITERATURE if paper else ItemKind.COHORT
        evaluation = _resolve_evaluation(it, kind=lit_kind, has_accession=bool(acc))
        tier = it.get("confidence_tier") or evaluation.confidence
        conf_cell = _confidence_cell(tier, it.get("confidence_css") or evaluation.confidence_css, evaluation.confidence_bullets)

        rows.append(
            f"<tr data-type='{kind}' data-src='epmc' data-search='{_esc(search)}' data-patients='{_esc(hp)}' data-tier='{_esc(tier)}'>"
            f"{_num_cell(row_num)}"
            f"<td class='col-type'>{_type_badge(kind)}</td>"
            f"<td class='col-id'>{_id_cell(acc=acc, repo=repo, pmid=pmid)}</td>"
            f"<td class='col-year cell-mono'><b>{_esc(year)}</b></td>"
            f"<td class='col-title'>{_title_cell(title, pub, repo, description=desc, acc=acc)}</td>"
            f"<td class='col-disease'>{_disease_cell(it)}</td>"
            f"<td class='col-organ'>{_organ_cell(it)}</td>"
            f"<td class='col-src col-split'>{_source_link_cell(it, acc=acc, pmid=pmid)}</td>"
            f"<td class='col-design'>{design}</td>"
            f"<td class='col-verdict col-split'>{_verdict_badge(vlabel, vcss, vtitle)}</td>"
            f"<td class='col-confidence'>{conf_cell}</td>"
            f"<td class='col-similar'>{_similar_cell(it)}</td>"
            f"<td class='col-abstract'>{_abstract_cell(paper or it)}</td>"
            f"<td class='col-weight'>{unified_weight_cell(evaluation=evaluation, fit=fit, cohort_score=cohort_score)}</td>"
            f"<td class='col-analysis analysis-cell'>{_render_analysis_cell(it, kind=lit_kind, has_accession=bool(acc), pubs_by_pmid=pubs_by_pmid)}</td>"
            f"<td class='col-data'>{_data_cell(paper or it)}</td>"
            f"<td class='col-links'>{_literature_links(acc, repo, pmid)}</td>"
            f"</tr>"
        )
        total += 1

    body = "\n".join(rows) or '<tr><td colspan="17" data-i18n="no_rows"></td></tr>'
    return body, total
