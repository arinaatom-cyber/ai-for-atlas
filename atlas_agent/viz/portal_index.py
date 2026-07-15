"""Индекс каталога TMT ATLAS: органы, ссылки на GitHub, репозитории, краткие описания."""
from __future__ import annotations

import re
from typing import Any

import pandas as pd

from atlas_agent.catalog.organ_classify import map_project, normalize_project_id
from atlas_agent.sources.dataset_resolve import _url_for_accession
from atlas_agent.sources.github_client import parse_repo_url
from atlas_agent.sources.projects_table import primary_project_id

ATLAS_MAP_BASE = "https://arinaatom-cyber.github.io/TMT/"
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


def atlas_organ_map_url(organ_canon: str) -> str:
    """Диплинк на интерактивную карту (параметр ?organ= как в TMT Pages)."""
    key = (organ_canon or "").strip().replace(" ", "_")
    if not key or key == "Other":
        return ATLAS_MAP_BASE
    return f"{ATLAS_MAP_BASE}?organ={key}"


def github_tree_url(repo_url: str, branch: str, subpath: str) -> str:
    ref = parse_repo_url(repo_url, default_branch=branch)
    path = subpath.strip("/")
    return f"{ref.url}/tree/{ref.branch}/{path}" if path else f"{ref.url}/tree/{ref.branch}"


def project_github_links(cfg: dict, project_id: str) -> dict[str, str]:
    """Папки в tmt-projects и (для PXD) в репозитории TMT."""
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
    """Краткое описание для портала — не дословный заголовок статьи."""
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
    """Группировка проектов каталога по органу для Streamlit / отчётов."""
    by_organ: dict[str, list[dict[str, Any]]] = {}
    all_projects: list[dict[str, Any]] = []

    for _, row in df.iterrows():
        card = catalog_row_to_portal(row, cfg)
        all_projects.append(card)
        for organ in card["organs"]:
            by_organ.setdefault(organ, []).append(card)

    organ_counts = {k: len(v) for k, v in sorted(by_organ.items(), key=lambda x: (-len(x[1]), x[0]))}
    gh_cfg = cfg.get("github") or {}

    return {
        "n_projects": len(all_projects),
        "by_organ": by_organ,
        "organ_counts": organ_counts,
        "projects": all_projects,
        "github": {
            "atlas_repo": gh_cfg.get("atlas_repo", ""),
            "data_repo": gh_cfg.get("data_repo", ""),
            "atlas_map": ATLAS_MAP_BASE,
            "discovery_site": DISCOVERY_SITE,
            "portal_site": PORTAL_SITE,
        },
    }


def format_finding_note(item: dict, *, keywords: list[str] | None = None) -> str:
    """
    Текст «что найдено» для Discovery / keyword search.
    Не дублирует заголовок статьи — поясняет, почему запись попала в выдачу.
    """
    parts: list[str] = []
    acc = item.get("project_accession") or item.get("accession") or ""
    src = item.get("source") or item.get("consortium") or ""

    if keywords:
        parts.append(f"Совпадение по ключевым словам: {', '.join(keywords[:6])}")

    sim = (item.get("similar_in_catalog") or [{}])[0]
    if sim.get("project_id"):
        parts.append(f"Похоже на {sim['project_id']} (score {sim.get('score', '—')})")

    ai = item.get("abstract_ai") or {}
    if ai.get("summary_ru"):
        parts.append(ai["summary_ru"])
    elif ai.get("similar_atlas_theme"):
        parts.append(f"Тема: {ai['similar_atlas_theme']}")

    if item.get("atlas_fit"):
        parts.append(f"Atlas fit: {item['atlas_fit']}")

    reasons = item.get("qc_reasons") or item.get("filter_reasons") or []
    if reasons:
        parts.append("; ".join(str(r) for r in reasons[:2]))

    sig = item.get("material_signals") or {}
    inc = sig.get("included") or []
    if inc:
        parts.append(f"Материал: {', '.join(inc[:3])}")

    if acc and src:
        parts.append(f"Источник {src}, ID {acc}")
    elif acc:
        parts.append(f"Репозиторий {acc}")

    if not parts:
        title = (item.get("title") or "")[:80]
        return f"Кандидат TMT human proteomics{f' — {title}' if title else ''}"

    return " · ".join(parts)[:400]
