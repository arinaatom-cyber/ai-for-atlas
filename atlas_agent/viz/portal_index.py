from __future__ import annotations

import html
import re
from typing import Any

import pandas as pd

from atlas_agent.catalog.organ_classify import map_project, normalize_project_id
from atlas_agent.viz.display_format import is_stub_description
from atlas_agent.sources.dataset_resolve import _url_for_accession
from atlas_agent.sources.github_client import parse_repo_url
from atlas_agent.sources.projects_table import primary_project_id

ATLAS_MAP_BASE = "https://arinaatom-cyber.github.io/TMT/"
STREAMLIT_ATLAS_URL = "https://human-cancser-tmt-proteome-atlas.streamlit.app/"
DISCOVERY_SITE = "https://arinaatom-cyber.github.io/ai-for-atlas/site/discovery.html"
PORTAL_SITE = "https://arinaatom-cyber.github.io/ai-for-atlas/"


def _clean_pmid(raw: Any) -> str:
    if raw is None or (isinstance(raw, float) and pd.isna(raw)):
        return ""
    return re.sub(r"\D", "", str(raw).split(".")[0])


def repository_url(accession: str) -> str:
    acc = (accession or "").strip().upper()
    if not acc:
        return ""
    url = _url_for_accession(acc)
    return url or ""


def pubmed_url(pmid: Any) -> str:
    p = _clean_pmid(pmid)
    return f"https://pubmed.ncbi.nlm.nih.gov/{p}/" if p else ""


def europe_pmc_url(pmid: Any) -> str:
    p = _clean_pmid(pmid)
    return f"https://europepmc.org/article/MED/{p}" if p else ""


def atlas_organ_map_url(organ_canon: str, *, base: str | None = None) -> str:
    map_base = (base or ATLAS_MAP_BASE).rstrip("/")
    key = (organ_canon or "").strip().replace(" ", "_")
    if "streamlit.app" in map_base:
        return map_base if not key or key == "Other" else f"{map_base}?organ={key}"
    if not key or key == "Other":
        return f"{map_base}/" if not map_base.endswith("/") else map_base
    return f"{map_base}?organ={key}"


def github_tree_url(repo_url: str, branch: str, subpath: str) -> str:
    ref = parse_repo_url(repo_url, default_branch=branch)
    path = subpath.strip("/")
    return f"{ref.url}/tree/{ref.branch}/{path}" if path else f"{ref.url}/tree/{ref.branch}"


def project_github_links(cfg: dict, project_id: str) -> dict[str, str]:
    gh = cfg.get("github") or {}
    pid = primary_project_id(project_id)
    branch = gh.get("raw_branch") or "main"
    out: dict[str, str] = {}

    data_repo = gh.get("data_repo")
    data_path = gh.get("data_projects_path") or "Projects"
    if data_repo and pid.startswith("PXD"):
        out["tmt_projects_folder"] = github_tree_url(data_repo, branch, f"{data_path}/{pid}")

    atlas_repo = gh.get("atlas_repo")
    atlas_path = gh.get("atlas_projects_path") or "projects"
    if atlas_repo and pid.startswith("PXD"):
        out["atlas_repo_folder"] = github_tree_url(atlas_repo, branch, f"{atlas_path}/{pid}")

    if gh.get("atlas_repo"):
        out["atlas_repo"] = gh["atlas_repo"].rstrip("/")
    if gh.get("data_repo"):
        out["data_repo"] = gh["data_repo"].rstrip("/")

    return out


def brief_description(row: dict | pd.Series) -> str:
    for col in ("Short Description", "Short description", "Design", "Tissue Cell Type Detailed"):
        val = str(row.get(col) or "").strip()
        if len(val) > 20:
            return val[:280]
    title = str(row.get("Title") or "").strip()
    disease = str(row.get("Disease") or row.get("Tumor Type") or "").strip()
    tissue = str(row.get("Tissue") or "").strip()
    parts = [p for p in (disease, tissue) if p and p.lower() not in ("nan", "not specified")]
    if parts:
        return f"{title[:120]} — {'; '.join(parts)}"[:280] if title else "; ".join(parts)[:280]
    return title[:280] if title else ""


def catalog_row_to_portal(row: dict | pd.Series, cfg: dict) -> dict[str, Any]:
    mapped = map_project(dict(row))
    pid = mapped["pid"] or normalize_project_id(str(row.get("Project ID") or ""))
    organs = mapped.get("organs") or ["Other"]
    gh = project_github_links(cfg, pid)
    pmid = row.get("PMID")
    return {
        "project_id": pid,
        "database": str(row.get("Database") or "").strip(),
        "organs": organs,
        "organ_primary": organs[0] if organs else "Other",
        "organ_raw": mapped.get("organ_raw") or "",
        "disease": str(row.get("Disease") or row.get("Tumor Type") or "").strip(),
        "tissue": str(row.get("Tissue") or "").strip(),
        "tmt": str(row.get("TMT Label (Unified)") or "").strip(),
        "patients": row.get("Patients / donors") or row.get("Total Samples"),
        "description": brief_description(row),
        "title": str(row.get("Title") or "").strip()[:200],
        "pmid": _clean_pmid(pmid),
        "repository_url": repository_url(pid),
        "pubmed_url": pubmed_url(pmid),
        "europe_pmc_url": europe_pmc_url(pmid),
        "atlas_map_url": atlas_organ_map_url(organs[0]),
        "github": gh,
    }


def build_organ_index(df: pd.DataFrame, cfg: dict) -> dict[str, Any]:
    by_organ: dict[str, list[dict[str, Any]]] = {}
    all_projects: list[dict[str, Any]] = []

    for _, row in df.iterrows():
        card = catalog_row_to_portal(row, cfg)
        all_projects.append(card)
        for organ in card["organs"]:
            by_organ.setdefault(organ, []).append(card)

    organ_counts = {k: len(v) for k, v in sorted(by_organ.items(), key=lambda x: (-len(x[1]), x[0]))}
    gh_cfg = cfg.get("github") or {}
    streamlit_map = gh_cfg.get("streamlit_app") or STREAMLIT_ATLAS_URL

    return {
        "n_projects": len(all_projects),
        "by_organ": by_organ,
        "organ_counts": organ_counts,
        "projects": all_projects,
        "github": {
            "atlas_repo": gh_cfg.get("atlas_repo", ""),
            "data_repo": gh_cfg.get("data_repo", ""),
            "atlas_map": ATLAS_MAP_BASE,
            "streamlit_map": streamlit_map,
            "discovery_site": DISCOVERY_SITE,
            "portal_site": PORTAL_SITE,
        },
    }


MATERIAL_SIGNAL_EN: dict[str, str] = {
    "clinical_human": "human clinical samples",
    "pdc_clinical_tumor": "PDC clinical tumor cohort",
    "human_tumor_tissue": "tumor tissue",
    "normal_adjacent": "adjacent normal tissue",
    "patient_fluid": "patient plasma/serum/blood/CSF",
    "human_cancer_cell_line": "human cancer cell line",
}

MATERIAL_KEYWORD_PATTERNS: list[tuple[str, str]] = [
    ("vitreous", r"\bvitreous\b"),
    ("retinal", r"\bretinal\b"),
    ("case-control", r"case[- ]?control"),
    ("paired tumor/normal", r"paired\s+(tumor|normal)|tumor[- ]adjacent"),
    ("adjacent normal", r"adjacent\s+normal|peritumoral"),
    ("tumor tissue", r"\b(tumor\s+tissue|ffpe|biopsy|resected)\b"),
    ("plasma", r"\b(plasma|serum|blood)\b"),
    ("CSF", r"\b(csf|cerebrospinal)\b"),
    ("urine", r"\burine\b"),
    ("cancer cell line", r"\b(cell\s+line|mcf[- ]?7|a549|hct116)\b"),
    ("gastric", r"\bgastric\b"),
    ("lung", r"\b(lung|luad|adenocarcinoma)\b"),
    ("proteome", r"\bproteome\b"),
]


def material_keywords_from_item(item: dict) -> list[str]:
    blob = " ".join(
        str(item.get(k) or "")
        for k in ("title", "description", "abstract", "disease", "experiment_type", "analytical_fraction")
    )
    found: list[str] = []
    for label, pat in MATERIAL_KEYWORD_PATTERNS:
        if re.search(pat, blob, re.I) and label not in found:
            found.append(label)
    return found[:8]


def _resolve_pmid_from_literature(item: dict) -> str:
    acc = (item.get("project_accession") or item.get("accession") or "").strip().upper()
    title = (item.get("title") or "").strip()
    queries: list[str] = []
    if acc:
        queries.append(acc)
    if title and len(title) > 20:
        queries.append(f'"{title[:120]}"')
    if not queries:
        return ""
    try:
        import requests

        for q in queries:
            r = requests.get(
                "https://www.ebi.ac.uk/europepmc/webservices/rest/search",
                params={"query": q, "format": "json", "pageSize": 1, "resultType": "core"},
                timeout=25,
            )
            r.raise_for_status()
            hits = (r.json().get("resultList") or {}).get("result") or []
            if hits:
                pmid = _clean_pmid(hits[0].get("pmid"))
                if pmid:
                    return pmid
    except Exception:
        pass
    return ""


def _plain_description(text: str) -> str:
    s = html.unescape(str(text or ""))
    s = re.sub(r"<[^>]+>", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def article_description(item: dict) -> str:
    if item.get("cohort_score") is not None:
        for key in ("abstract_snippet", "abstract", "article_description", "finding_note"):
            val = str(item.get(key) or "").strip()
            if val and val.lower() not in ("nan", "none", "—") and not is_stub_description(val):
                return _plain_description(val)
    for key in (
        "article_description",
        "description_en",
        "description",
        "abstract_snippet",
        "abstract",
        "projectDescription",
        "finding_note",
    ):
        val = str(item.get(key) or "").strip()
        if val and val.lower() not in ("nan", "none", "—") and not is_stub_description(val):
            return _plain_description(val)
    ai = item.get("abstract_ai") or {}
    for key in ("summary_en", "summary_ru"):
        val = str(ai.get(key) or item.get(key) or "").strip()
        if val:
            return _plain_description(val)
    return ""


def _pmid_from_text(*parts: object) -> str:
    blob = " ".join(str(p or "") for p in parts)
    m = re.search(r"\b(?:PMID[:\s]*)?(\d{7,9})\b", blob, re.I)
    return m.group(1) if m else ""


_PRIDE_DETAIL_CACHE: dict[str, dict] = {}


def _fetch_pride_project_cached(acc: str) -> dict:
    key = acc.strip().upper()
    if key in _PRIDE_DETAIL_CACHE:
        return _PRIDE_DETAIL_CACHE[key]
    try:
        from atlas_agent.sources.pride import fetch_project

        detail = fetch_project(key) or {}
    except Exception:
        detail = {}
    _PRIDE_DETAIL_CACHE[key] = detail
    return detail


def resolve_publication_links(item: dict, *, fetch_pride_pmid: bool = True) -> None:
    acc = (item.get("project_accession") or item.get("accession") or "").strip().upper()
    if acc.startswith("PMID:"):
        acc = ""
    item["repository_url"] = item.get("repository_url") or item.get("url") or repository_url(acc)
    pmid = _clean_pmid(item.get("pmid"))
    if not pmid:
        pmid = _pmid_from_text(
            item.get("description"),
            item.get("abstract"),
            item.get("abstract_snippet"),
            item.get("title"),
        )
    if not pmid and fetch_pride_pmid:
        pmid = _resolve_pmid_from_literature(item)
    if not pmid and acc.startswith("PDC"):
        try:
            from atlas_agent.sources.pdc import pdc_publication_for_study

            pub = pdc_publication_for_study(acc)
        except Exception:
            pub = None
        if pub:
            pmid = pmid or _clean_pmid(pub.get("pmid"))
            if pub.get("doi") and not item.get("doi"):
                item["doi"] = pub["doi"]
            if pub.get("year") and not item.get("publication_date"):
                item["publication_date"] = pub["year"]
            paper_title = str(pub.get("title") or "").strip()
            if paper_title:
                item["publication_title"] = paper_title
                current_title = str(item.get("title") or "")
                if len(paper_title) > 20 and (
                    not current_title or current_title.startswith(acc) or " — " in current_title
                ):
                    item["title"] = paper_title[:500]
            abstract = str(pub.get("abstract") or "").strip()
            if abstract:
                item["abstract"] = abstract
                item["abstract_snippet"] = abstract[:1200]
    if not pmid and fetch_pride_pmid and acc.startswith("PXD"):
        try:
            detail = _fetch_pride_project_cached(acc)
            for ref in detail.get("references") or []:
                pmid = _clean_pmid(ref.get("pubmedID"))
                if pmid:
                    break
            if not item.get("description"):
                desc = str(detail.get("projectDescription") or "").strip()
                if desc:
                    item["description"] = desc[:800]
            if not item.get("title"):
                item["title"] = str(detail.get("title") or "")[:500]
        except Exception:
            pass
    if pmid:
        item["pmid"] = pmid
    item["pubmed_url"] = pubmed_url(pmid)
    item["europe_pmc_url"] = europe_pmc_url(pmid)
    desc = article_description(item)
    if desc:
        item["article_description"] = desc
        if not str(item.get("description") or "").strip():
            item["description"] = desc[:800]
    if item.get("pmid") and not item.get("doi"):
        item.setdefault("doi", "")


def _data_file_hint(item: dict) -> str:
    da = item.get("data_availability") or {}
    layer = da.get("omics_layer") or ""
    proteome = da.get("proteome_files") or []
    phospho = da.get("phospho_files") or []
    files = da.get("quant_files") or da.get("sample_files") or []
    if layer == "phospho_only" or da.get("status") == "phospho_table":
        top = phospho[0] if phospho else (files[0] if files else "")
        return f"Phospho table only (not global proteome){': ' + top[:70] if top else ''}"
    if proteome:
        return f"Download: {proteome[0][:70]} (protein-level table)"
    if not files:
        return ""
    top = files[0]
    low = top.lower()
    if low == "protein.txt" or ("proteome" in low and "phospho" not in low):
        layer_hint = "protein-level table"
    elif "phospho" in low:
        layer_hint = "phospho layer (not global proteome)"
    elif "peptide" in low:
        layer_hint = "peptide table"
    else:
        layer_hint = "quant table"
    return f"Download: {top[:70]} ({layer_hint})"


def format_finding_note(item: dict, *, keywords: list[str] | None = None) -> str:
    parts: list[str] = []

    kw = list(keywords or []) + material_keywords_from_item(item)
    if kw:
        seen: set[str] = set()
        uniq = []
        for k in kw:
            kl = k.lower()
            if kl not in seen:
                seen.add(kl)
                uniq.append(k)
        parts.append("Keywords from title: " + ", ".join(uniq[:8]))

    sig = item.get("material_signals") or {}
    inc = [MATERIAL_SIGNAL_EN.get(x, x.replace("_", " ")) for x in (sig.get("included") or [])]
    if inc:
        parts.append("Material type: " + ", ".join(inc[:3]))

    design = str(item.get("sample_design") or "").strip()
    if design and design != "unknown":
        parts.append(f"Design: {design.replace('_', '-')}")

    file_hint = _data_file_hint(item)
    if file_hint:
        parts.append(file_hint)
    elif (item.get("data_availability") or {}).get("guidance"):
        parts.append(str(item["data_availability"]["guidance"])[:120])

    sim = (item.get("similar_in_catalog") or [{}])[0]
    if sim.get("project_id"):
        parts.append(f"Similar to catalog {sim['project_id']} (score {sim.get('score', '—')})")

    ai = item.get("abstract_ai") or {}
    if ai.get("summary_en"):
        parts.append(ai["summary_en"])
    elif ai.get("material") and ai.get("material") != "unclear":
        parts.append(f"LLM material: {ai['material']}")

    if item.get("atlas_fit"):
        parts.append(f"Atlas fit: {item['atlas_fit']}")

    if not parts:
        title = (item.get("title") or "")[:80]
        return f"TMT human proteomics candidate{f' — {title}' if title else ''}"

    return " · ".join(parts)[:420]
