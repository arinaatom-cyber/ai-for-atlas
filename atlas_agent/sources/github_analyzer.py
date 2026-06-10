"""Анализ репозиториев GitHub vs локальный каталог и CSV."""
from __future__ import annotations

import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from atlas_agent.sources.github_client import GitHubClient, RepoRef, parse_repo_url
from atlas_agent.sources.projects_table import primary_project_id

MATRIX_EXT = {".tsv", ".txt", ".csv", ".xlsx", ".xls"}
SKIP = re.compile(r"\bpsm\b|perc_psm|\.pdf$|\.fasta$|readme", re.I)


def _local_pxd_dirs(root: str | Path) -> dict[str, dict]:
    root = Path(root)
    if not root.is_dir():
        return {}
    out = {}
    for name in os.listdir(root):
        m = re.match(r"^(PXD\d+)", name, re.I)
        if not m:
            continue
        pxd = m.group(1).upper()
        folder = root / name
        if not folder.is_dir():
            continue
        files = []
        for fn in os.listdir(folder):
            fp = folder / fn
            if fp.is_file() and fp.suffix.lower() in MATRIX_EXT and not SKIP.search(fn):
                files.append(fn)
        out[pxd] = {"path": str(folder), "files": files[:20], "file_count": len(files)}
    return out


def _csv_pxd_set(df: pd.DataFrame) -> set[str]:
    if "Project ID" not in df.columns:
        return set()
    return {
        primary_project_id(str(x))
        for x in df["Project ID"].dropna()
        if str(x).strip()
    }


def analyze_repo_projects(
    client: GitHubClient,
    repo: RepoRef,
    projects_subdir: str,
    *,
    sample_files: int = 15,
) -> list[dict[str, Any]]:
    folders = client.list_pxd_directories(repo, projects_subdir)
    results = []
    for f in folders:
        pxd = f["pxd"]
        path = f["path"]
        children = client.list_contents(repo, path)
        files = [
            {
                "name": c.get("name"),
                "size": c.get("size"),
                "path": c.get("path"),
            }
            for c in children
            if c.get("type") == "file"
        ]
        matrix = [
            x
            for x in files
            if Path(x["name"]).suffix.lower() in MATRIX_EXT and not SKIP.search(x["name"])
        ]
        results.append(
            {
                "pxd": pxd,
                "repo": repo.slug,
                "github_path": path,
                "html_url": f.get("html_url") or f"{repo.url}/tree/{repo.branch}/{path}",
                "files_total": len(files),
                "matrix_candidates": matrix[:sample_files],
                "subdir": projects_subdir,
            }
        )
    return results


def compare_sources(
    df: pd.DataFrame,
    *,
    github_projects: list[dict],
    local_root: str | None,
) -> dict[str, Any]:
    csv_set = _csv_pxd_set(df)
    gh_set = {p["pxd"] for p in github_projects}
    local_map = _local_pxd_dirs(local_root) if local_root else {}
    local_set = set(local_map)

    only_github = sorted(gh_set - csv_set)
    only_csv = sorted(csv_set - gh_set)
    only_local = sorted(local_set - csv_set)
    in_all = sorted(csv_set & gh_set & local_set) if local_set else sorted(csv_set & gh_set)

    return {
        "csv_count": len(csv_set),
        "github_count": len(gh_set),
        "local_count": len(local_set),
        "only_on_github": only_github,
        "only_in_csv": only_csv,
        "only_local_disk": only_local,
        "in_csv_and_github": sorted(csv_set & gh_set),
        "local_detail": local_map,
    }


def build_github_integration_report(cfg: dict, df: pd.DataFrame) -> dict[str, Any]:
    gh_cfg = cfg.get("github") or {}
    client = GitHubClient()
    local_root = (cfg.get("paths") or {}).get("tmt_projects_dir")

    repos_report = []
    all_github_projects: list[dict] = []

    specs = [
        ("atlas_web", gh_cfg.get("atlas_repo"), gh_cfg.get("atlas_projects_path") or "projects"),
        ("data", gh_cfg.get("data_repo"), gh_cfg.get("data_projects_path") or "Projects"),
    ]

    for label, url, subdir in specs:
        if not url:
            continue
        try:
            ref = parse_repo_url(url, default_branch=gh_cfg.get("raw_branch") or "main")
        except ValueError as e:
            repos_report.append({"label": label, "error": str(e)})
            continue

        meta = client.repo_meta(ref)
        entry: dict[str, Any] = {
            "label": label,
            "repo": ref.slug,
            "url": ref.url,
            "branch": ref.branch,
            "projects_path": subdir,
            "accessible": meta is not None,
            "private": (meta or {}).get("private"),
        }
        if meta is None:
            entry["error"] = (
                "Репозиторий недоступен (приватный или не найден). "
                "Задайте GITHUB_TOKEN с правом read."
            )
            repos_report.append(entry)
            continue

        projects = analyze_repo_projects(client, ref, subdir)
        entry["pxd_folders"] = len(projects)
        entry["projects_sample"] = projects[:10]
        repos_report.append(entry)
        all_github_projects.extend(projects)

    comparison = compare_sources(
        df,
        github_projects=all_github_projects,
        local_root=local_root,
    )

    novel_for_catalog = [
        p
        for p in all_github_projects
        if p["pxd"] in comparison.get("only_on_github", [])
    ]

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "policy": client.policy(),
        "repos": repos_report,
        "comparison": comparison,
        "novel_github_projects": novel_for_catalog[:50],
        "integration_hints": [
            "PXD только на GitHub → кандидат в data/projects.csv",
            "PXD только в CSV → проверить clone tmt-projects или токен",
            "Локальная папка без GitHub → синхронизация вручную",
        ],
    }
