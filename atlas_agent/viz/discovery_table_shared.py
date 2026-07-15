"""Shared row builders for Discovery tables (GitHub + Streamlit)."""
from __future__ import annotations

import html
import re

from atlas_agent.discovery.confidence import attach_confidence
from atlas_agent.discovery.fit_rules import (
    cohort_verdict,
    fit_display_label,
    is_cohort_excluded,
    literature_verdict,
    project_verdict,
)
from atlas_agent.viz.portal_index import (
    europe_pmc_url,
    format_finding_note,
    pubmed_url,
    repository_url,
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


def _evidence_inline(bullets: list[str]) -> str:
    if not bullets:
        return ""
    items = "".join(f"<li>{_esc(b)}</li>" for b in bullets[:4])
    return f'<ul class="cell-bullets evidence-bullets">{items}</ul>'


def _verdict_badge(label: str, css: str, title: str = "") -> str:
    t = f' title="{_esc(title)}"' if title else ""
    return f'<span class="badge {css}"{t}>{_esc(label)}</span>'


def _type_badge(kind: str) -> str:
    labels = {"project": "Project", "paper": "Paper", "cohort": "Cohort"}
    css = {"project": "badge-ok", "paper": "badge-muted", "cohort": "badge-warn"}.get(kind, "badge-muted")
    return _verdict_badge(labels.get(kind, kind), css)


def unified_weight_cell(*, fit: str = "", fit_score: object = None, cohort_score: object = None) -> str:
    """LLM verdict label (no inflated 0.7) + optional cohort score 0–100."""
    parts: list[str] = []
    fit_s = str(fit or "").strip().lower()
    if fit_s in ("yes", "maybe", "no"):
        parts.append(
            f'<span class="badge {fit_class(fit_s)}" title="LLM atlas screening (trained on catalog exclusions)">'
            f"{_esc(fit_display_label({'atlas_fit': fit_s}))}</span>"
        )
    if cohort_score not in (None, ""):
        parts.append(
            f'<span class="badge badge-muted" title="Cohort relevance 0–100">cohort {_esc(cohort_score)}</span>'
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
        f'class="link-epmc cell-src"><b>Europe PMC</b></a>'
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


def _note_bullets(note: str) -> str:
    parts = [p.strip() for p in str(note or "").split(" · ") if p.strip()]
    if not parts:
        return ""
    items = "".join(f"<li>{_esc(p)}</li>" for p in parts[:8])
    return f'<ul class="cell-bullets">{items}</ul>'


def _dedupe_evidence(note: str, bullets: list[str]) -> list[str]:
    """Skip bullets already present in finding_note or Design column."""
    note_l = str(note or "").lower()
    out: list[str] = []
    for b in bullets:
        bl = str(b or "").strip()
        if not bl:
            continue
        low = bl.lower()
        if low in note_l:
            continue
        if low.startswith("design:") and "design:" in note_l:
            continue
        if "mixed protein" in low and "mixed protein" in note_l:
            continue
        if low.startswith("tmt ") and "tmt" in note_l:
            continue
        out.append(bl)
    return out


def _badge_stack(*badges: str) -> str:
    rows = [b for b in badges if b]
    if not rows:
        return ""
    return f'<div class="badge-stack">{"".join(rows)}</div>'


def _link_chip(href: str, label: str) -> str:
    if not href:
        return ""
    return (
        f'<a href="{_esc(href)}" target="_blank" rel="noopener" class="link-chip">{_esc(label)}</a>'
    )


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
    src = source_label({"accession": acc}) if acc else ""
    chips: list[str] = []
    if repo:
        chips.append(_link_chip(repo, src or "Repo"))
    if pmid:
        chips.append(_link_chip(pubmed_url(pmid), "PubMed"))
        chips.append(_link_chip(europe_pmc_url(pmid), "EPMC"))
    return _links_stack(chips)


def _literature_links(acc: str, repo: str, pmid: str) -> str:
    chips: list[str] = []
    if pmid:
        chips.append(_link_chip(pubmed_url(pmid), "PubMed"))
        chips.append(_link_chip(europe_pmc_url(pmid), "EPMC"))
    if repo and acc:
        chips.append(_link_chip(repo, f"{acc} project"))
    return _links_stack(chips)


def _data_status_label(status: str, label: str) -> str:
    friendly = {
        "quant_table": "Protein table",
        "local_mirror": "Local mirror",
        "maybe_table": "Possible table",
        "processed_psm": "PSM only",
        "phospho_table": "Phospho only",
        "raw_only": "RAW only",
        "no_files": "No files",
    }
    return friendly.get(status, label or status or "Unknown")


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
        return '<span class="cell-empty">—</span>'
    labels = {
        "proteomics": "proteomics",
        "phosphoproteomics": "phosphoproteomics",
        "transcriptomics": "transcriptomics",
        "genomics": "genomics",
        "metabolomics": "metabolomics",
        "lipidomics": "lipidomics",
        "glycoproteomics": "glycoproteomics",
        "multi_omics": "multi-omics",
    }
    return ", ".join(_esc(labels.get(o, o)) for o in omics[:6])


def _patient_cell(item: dict) -> str:
    hp = item.get("has_patients") or ""
    if hp == "yes":
        return '<span class="badge badge-ok">yes</span>'
    if hp == "maybe":
        return '<span class="badge badge-warn">maybe</span>'
    if hp == "no":
        return '<span class="badge badge-bad">no</span>'
    return '<span class="cell-empty">—</span>'


def _data_cell(it: dict) -> str:
    da = it.get("data_availability") or {}
    if isinstance(da, dict) and da:
        status = da.get("status") or "unknown"
        label = _data_status_label(status, str(da.get("label") or ""))
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
        status_badge = f'<span class="badge {cls}">{_esc(label)}</span>'
        mixed_badge = (
            '<span class="badge badge-warn" title="Protein and phospho files — manual check">'
            "mixed protein+phospho</span>"
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
            f'<span class="cell-label">Data files</span>'
            f'<span class="badge badge-warn">{_esc(hint[:90])}</span>'
            f"</div>"
        )
    return (
        '<div class="cell-stack">'
        '<span class="cell-label">Data files</span>'
        '<span class="cell-empty">—</span>'
        "</div>"
    )


def _source_link_cell(it: dict, *, acc: str = "", pmid: str = "") -> str:
    acc = acc or _first_accession(it)
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
            body = (
                f'<a href="{_esc(repo)}" target="_blank" rel="noopener" class="cell-mono id-acc">'
                f"<b>{acc_esc}</b></a>"
            )
        else:
            body = f'<span class="cell-mono id-acc"><b>{acc_esc}</b></span>'
        return (
            f'<div class="cell-stack id-cell">'
            f'<span class="cell-label">{_esc(kind)}</span>{body}</div>'
        )
    pub = pubmed_url(pmid) if pmid else ""
    no_acc = '<span class="id-no-acc">No PXD/PDC</span>'
    if pub:
        no_acc = (
            f'<a href="{_esc(pub)}" target="_blank" rel="noopener" class="id-no-acc">No PXD/PDC</a>'
        )
    return (
        f'<div class="cell-stack id-cell">'
        f'<span class="cell-label">Paper</span>{no_acc}</div>'
    )


def _title_cell(title: str, pub_url: str, repo: str) -> str:
    title_esc = _esc(title[:140])
    if pub_url:
        return f'<a href="{_esc(pub_url)}" target="_blank" rel="noopener" class="cell-title">{title_esc}</a>'
    if repo:
        return f'<a href="{_esc(repo)}" target="_blank" rel="noopener" class="cell-title">{title_esc}</a>'
    return f'<span class="cell-title">{title_esc}</span>'


def _analysis_project(it: dict, pubs_by_pmid: dict[str, dict]) -> str:
    blocks: list[str] = ['<div class="cell-stack cell-analysis">']
    note = it.get("finding_note") or format_finding_note(it)
    bullets = _note_bullets(note)
    if bullets:
        blocks.append(bullets)
    pmid = str(it.get("pmid") or "").strip()
    pub = pubs_by_pmid.get(pmid) if pmid else None
    summary = ""
    if pub and pub.get("summary_en"):
        summary = pub["summary_en"]
    else:
        ai = it.get("abstract_ai") or {}
        summary = ai.get("summary_en") or ""
    if summary:
        blocks.append(f'<p class="cell-summary cell-clip">{_esc(summary[:280])}</p>')
    ev = _dedupe_evidence(note, list(it.get("confidence_evidence") or []))
    if ev:
        blocks.append(f'<div class="cell-clip">{_evidence_inline(ev[:3])}</div>')
    if len(blocks) == 1:
        blocks.append('<span class="cell-empty">—</span>')
    blocks.append("</div>")
    return "".join(blocks)


def _analysis_literature(paper: dict | None, cohort: dict | None) -> str:
    blocks: list[str] = ['<div class="cell-stack cell-analysis">']
    if paper:
        note = paper.get("finding_note") or format_finding_note(paper) or ""
        bullets = _note_bullets(note)
        if bullets:
            blocks.append(bullets)
        ai = paper.get("abstract_ai") or {}
        summary = ai.get("summary_en") or paper.get("summary_en") or ""
        if summary and summary not in note:
            blocks.append(f'<p class="cell-summary cell-clip">{_esc(summary[:240])}</p>')
        ev = list((paper or {}).get("confidence_evidence") or (paper or {}).get("abstract_ai", {}).get("semantic_evidence") or [])[:2]
        if ev:
            blocks.append(f'<div class="cell-clip">{_evidence_inline(ev)}</div>')
    if cohort:
        desc = cohort.get("description_en") or cohort.get("description_ru") or ""
        if desc:
            blocks.append(f'<p class="cell-cohort">{_esc(desc[:280])}</p>')
    if len(blocks) == 1:
        blocks.append('<span class="cell-empty">—</span>')
    blocks.append("</div>")
    return "".join(blocks)


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

    for it in projects:
        raw_acc = _first_accession(it)
        repo = it.get("repository_url") or it.get("url") or repository_url(raw_acc)
        pmid = str(it.get("pmid") or "").strip()
        pub = it.get("pubmed_url") or pubmed_url(pmid)
        title = (it.get("title") or "").strip()
        year = item_year(it, pubs_by_pmid)
        design = _esc(str(it.get("sample_design") or "—").replace("_", "-"))
        src_key = source_label(it).lower()
        search = f"{raw_acc} {title} {year} {it.get('program') or ''}".lower()

        omics_cell = _omics_cell(it) if it.get("omics") else '<span class="cell-empty">—</span>'

        attach_confidence(it, kind="project")
        vlabel, vcss, vtitle = project_verdict(it)
        verdict_cell = _verdict_badge(vlabel, vcss, vtitle)
        tier = it.get("confidence_tier") or ""
        conf_cell = _confidence_cell(tier, it.get("confidence_css") or "tier-c", it.get("confidence_evidence") or [])

        rows.append(
            f"<tr data-type='project' data-src='{src_key}' data-search='{_esc(search)}' data-patients='' data-tier='{_esc(tier)}'>"
            f"<td class='col-type'>{_type_badge('project')}</td>"
            f"<td class='col-id'>{_id_cell(acc=raw_acc, repo=repo, pmid=pmid)}</td>"
            f"<td class='col-year cell-mono'><b>{_esc(year)}</b></td>"
            f"<td class='col-title'>{_title_cell(title, pub, repo)}</td>"
            f"<td class='col-src col-split'>{_source_link_cell(it, acc=raw_acc)}</td>"
            f"<td class='col-design'>{design}</td>"
            f"<td class='col-omics'>{omics_cell}</td>"
            f"<td class='col-pat'><span class='cell-empty'>—</span></td>"
            f"<td class='col-n'><span class='cell-empty'>—</span></td>"
            f"<td class='col-verdict col-split'>{verdict_cell}</td>"
            f"<td class='col-confidence'>{conf_cell}</td>"
            f"<td class='col-weight'><span class='cell-empty'>—</span></td>"
            f"<td class='col-analysis analysis-cell'>{_analysis_project(it, pubs_by_pmid)}</td>"
            f"<td class='col-data'>{_data_cell(it)}</td>"
            f"<td class='col-links'>{_project_links(raw_acc, repo, pmid)}</td>"
            f"</tr>"
        )
        total += 1

    lit_rows = _merge_literature(papers, cohorts)
    for entry in lit_rows:
        it = entry["item"]
        paper = entry.get("paper")
        cohort = entry.get("cohort")
        kind = entry["kind"]
        pmid = _norm_pmid(it)
        pub = pubmed_url(pmid)
        acc = _first_accession(it)
        repo = repository_url(acc) if acc else ""
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
        n = it.get("patient_n") or ""
        n_cell = f"<b>{_esc(n)}</b>" if n not in (None, "") else '<span class="cell-empty">—</span>'
        hp = it.get("has_patients") or ""
        search = f"{title} {pmid} {acc} {it.get('description_en') or ''}".lower()

        if kind == "cohort" and is_cohort_excluded(title, str(it.get("abstract") or "")):
            vlabel, vcss, vtitle = ("Exclude", "badge-bad", "Review / software / narrative")
        elif kind == "cohort":
            vlabel, vcss, vtitle = cohort_verdict(it)
        elif paper:
            vlabel, vcss, vtitle = literature_verdict(paper, has_accession=bool(acc))
        else:
            vlabel, vcss, vtitle = ("Watch", "badge-warn", "Literature surveillance")

        lit_kind = "paper" if paper else "cohort"
        attach_confidence(it, kind=lit_kind, has_accession=bool(acc))
        tier = it.get("confidence_tier") or ""
        conf_cell = _confidence_cell(tier, it.get("confidence_css") or "tier-c", it.get("confidence_evidence") or [])

        rows.append(
            f"<tr data-type='{kind}' data-src='epmc' data-search='{_esc(search)}' data-patients='{_esc(hp)}' data-tier='{_esc(tier)}'>"
            f"<td class='col-type'>{_type_badge(kind)}</td>"
            f"<td class='col-id'>{_id_cell(acc=acc, repo=repo, pmid=pmid)}</td>"
            f"<td class='col-year cell-mono'><b>{_esc(year)}</b></td>"
            f"<td class='col-title'>{_title_cell(title, pub, repo)}</td>"
            f"<td class='col-src col-split'>{_source_link_cell(it, acc=acc, pmid=pmid)}</td>"
            f"<td class='col-design'>{design}</td>"
            f"<td class='col-omics'>{_omics_cell(it)}</td>"
            f"<td class='col-pat'>{_patient_cell(it)}</td>"
            f"<td class='col-n cell-mono'>{n_cell}</td>"
            f"<td class='col-verdict col-split'>{_verdict_badge(vlabel, vcss, vtitle)}</td>"
            f"<td class='col-confidence'>{conf_cell}</td>"
            f"<td class='col-weight'>{unified_weight_cell(fit=fit, cohort_score=cohort_score)}</td>"
            f"<td class='col-analysis analysis-cell'>{_analysis_literature(paper, cohort)}</td>"
            f"<td class='col-data'>{_data_cell(paper or it)}</td>"
            f"<td class='col-links'>{_literature_links(acc, repo, pmid)}</td>"
            f"</tr>"
        )
        total += 1

    body = "\n".join(rows) or '<tr><td colspan="15" data-i18n="no_rows"></td></tr>'
    return body, total
