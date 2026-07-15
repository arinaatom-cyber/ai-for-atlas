"""Shared row builders for Discovery tables (GitHub + Streamlit)."""
from __future__ import annotations

import html
import re

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


def unified_weight_cell(*, fit: str = "", fit_score: object = None, cohort_score: object = None) -> str:
    """fit 0–1 (LLM atlas match) vs cohort 0–100 (literature mining)."""
    parts: list[str] = []
    if fit_score not in (None, ""):
        fs = fit_score
        try:
            fs = f"{float(fit_score):.2f}".rstrip("0").rstrip(".")
        except (TypeError, ValueError):
            fs = str(fit_score)
        fit_s = str(fit or "").strip()
        label = f"fit {fit_s} {fs}".strip() if fit_s else f"fit {fs}"
        parts.append(f'<span class="badge {fit_class(fit_s or "unk")}" title="LLM atlas fit 0–1">{_esc(label)}</span>')
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
    if not da:
        note = str(it.get("data_availability") or "").strip()
        if note:
            return f'<span class="badge badge-warn">{_esc(note[:80])}</span>'
        return '<span class="cell-empty">—</span>'
    status = da.get("status") or "unknown"
    label = _esc(da.get("label") or status)
    cls = {
        "quant_table": "badge-ok",
        "local_mirror": "badge-ok",
        "maybe_table": "badge-warn",
        "processed_psm": "badge-warn",
        "phospho_table": "badge-bad",
        "raw_only": "badge-bad",
        "no_files": "badge-bad",
    }.get(status, "badge-muted")
    samples = da.get("proteome_files") or da.get("quant_files") or da.get("sample_files") or []
    fname = _esc(samples[0][:70]) if samples else ""
    body = f'<span class="badge {cls}">{label}</span>'
    if fname:
        body += f'<br/><span class="muted file-hint">{fname}</span>'
    return body


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


def _id_cell(*, acc: str, repo: str, pmid: str, fit_score: object) -> str:
    if acc:
        acc_esc = _esc(acc)
        if repo:
            return (
                f'<a href="{_esc(repo)}" target="_blank" rel="noopener" class="cell-mono">'
                f"<b>{acc_esc}</b></a>"
            )
        return f'<span class="cell-mono"><b>{acc_esc}</b></span>'
    score_s = _fit_score_fmt(fit_score)
    label = f"No, {score_s}" if score_s else "No"
    pub = pubmed_url(pmid) if pmid else ""
    if pub:
        return f'<a href="{_esc(pub)}" target="_blank" rel="noopener" class="cell-mono"><b>{_esc(label)}</b></a>'
    return f'<span class="cell-mono"><b>{_esc(label)}</b></span>'


def _title_cell(title: str, pub_url: str, repo: str) -> str:
    title_esc = _esc(title[:140])
    if pub_url:
        return f'<a href="{_esc(pub_url)}" target="_blank" rel="noopener" class="cell-title">{title_esc}</a>'
    if repo:
        return f'<a href="{_esc(repo)}" target="_blank" rel="noopener" class="cell-title">{title_esc}</a>'
    return f'<span class="cell-title">{title_esc}</span>'


def _analysis_project(it: dict, pubs_by_pmid: dict[str, dict]) -> str:
    parts: list[str] = []
    note = it.get("finding_note") or format_finding_note(it)
    if note:
        parts.append(f'<span class="muted">{_esc(note[:420])}</span>')
    pmid = str(it.get("pmid") or "").strip()
    pub = pubs_by_pmid.get(pmid) if pmid else None
    if pub and pub.get("summary_en"):
        parts.append(f'<span class="muted llm-block">{_esc(pub["summary_en"][:300])}</span>')
    else:
        ai = it.get("abstract_ai") or {}
        if ai.get("summary_en"):
            parts.append(f'<span class="muted llm-block">{_esc(ai["summary_en"][:300])}</span>')
    return "<br/>".join(parts) if parts else '<span class="cell-empty">—</span>'


def _analysis_literature(paper: dict | None, cohort: dict | None) -> str:
    parts: list[str] = []
    if paper:
        ai = paper.get("abstract_ai") or {}
        summary = ai.get("summary_en") or paper.get("summary_en") or ""
        if summary:
            parts.append(_esc(summary[:300]))
        note = paper.get("finding_note") or format_finding_note(paper) or ""
        if note and note != summary:
            parts.append(f'<span class="muted">{_esc(note[:280])}</span>')
    if cohort:
        desc = cohort.get("description_en") or cohort.get("description_ru") or ""
        if desc:
            parts.append(f'<span class="muted">{_esc(desc[:280])}</span>')
    body = "<br/>".join(parts)
    return body or '<span class="cell-empty">—</span>'


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
        year = str(it.get("year") or "—")
        design = _esc(str(it.get("sample_design") or "—").replace("_", "-"))
        src_key = source_label(it).lower()
        search = f"{raw_acc} {title} {it.get('program') or ''}".lower()

        rows.append(
            f"<tr data-type='project' data-src='{src_key}' data-search='{_esc(search)}' data-patients=''>"
            f"<td class='col-id'>{_id_cell(acc=raw_acc, repo=repo, pmid=pmid, fit_score=None)}</td>"
            f"<td class='col-year cell-mono'>{_esc(year)}</td>"
            f"<td class='col-title'>{_title_cell(title, pub, repo)}</td>"
            f"<td class='col-src'>{_source_link_cell(it, acc=raw_acc)}</td>"
            f"<td class='col-design'>{design}</td>"
            f"<td class='col-omics'><span class='cell-empty'>—</span></td>"
            f"<td class='col-pat'><span class='cell-empty'>—</span></td>"
            f"<td class='col-n'><span class='cell-empty'>—</span></td>"
            f"<td class='col-weight'><span class='cell-empty'>—</span></td>"
            f"<td class='col-analysis analysis-cell'>{_analysis_project(it, pubs_by_pmid)}</td>"
            f"<td class='col-data'>{_data_cell(it)}</td>"
            f"<td class='col-links cell-links'>{links_cell(project_link(raw_acc, repo), pubmed_link(pmid), epmc_link(pmid))}</td>"
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
        year = str(it.get("year") or cohort and cohort.get("year") or "—")
        design = "—"
        if paper:
            mat = (paper.get("abstract_ai") or {}).get("material") or ""
            if mat and mat != "unclear":
                design = _esc(str(mat).replace("|", ", ")[:60])
        fit = ""
        fit_score = None
        if paper:
            fit = paper.get("atlas_fit") or (paper.get("abstract_ai") or {}).get("atlas_fit") or ""
            fit_score = paper.get("atlas_fit_score") or (paper.get("abstract_ai") or {}).get("atlas_fit_score")
        cohort_score = (cohort or it).get("cohort_score")
        n = it.get("patient_n") or ""
        n_cell = f"<b>{_esc(n)}</b>" if n not in (None, "") else '<span class="cell-empty">—</span>'
        hp = it.get("has_patients") or ""
        search = f"{title} {pmid} {acc} {it.get('description_en') or ''}".lower()

        rows.append(
            f"<tr data-type='{kind}' data-src='epmc' data-search='{_esc(search)}' data-patients='{_esc(hp)}'>"
            f"<td class='col-id'>{_id_cell(acc=acc, repo=repo, pmid=pmid, fit_score=fit_score if not acc else None)}</td>"
            f"<td class='col-year cell-mono'>{_esc(year)}</td>"
            f"<td class='col-title'>{_title_cell(title, pub, repo)}</td>"
            f"<td class='col-src'>{_source_link_cell(it, acc=acc, pmid=pmid)}</td>"
            f"<td class='col-design'>{design}</td>"
            f"<td class='col-omics'>{_omics_cell(it)}</td>"
            f"<td class='col-pat'>{_patient_cell(it)}</td>"
            f"<td class='col-n cell-mono'>{n_cell}</td>"
            f"<td class='col-weight'>{unified_weight_cell(fit=fit, fit_score=fit_score, cohort_score=cohort_score)}</td>"
            f"<td class='col-analysis analysis-cell'>{_analysis_literature(paper, cohort)}</td>"
            f"<td class='col-data'>{_data_cell(paper or it)}</td>"
            f"<td class='col-links cell-links'>{links_cell(pubmed_link(pmid), epmc_link(pmid), project_link(acc, repo))}</td>"
            f"</tr>"
        )
        total += 1

    body = "\n".join(rows) or '<tr><td colspan="12" data-i18n="no_rows"></td></tr>'
    return body, total
