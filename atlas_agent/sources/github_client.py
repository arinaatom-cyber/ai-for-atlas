"""Клиент GitHub REST API — только чтение."""
from __future__ import annotations

import base64
import os
import re
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

import requests

from atlas_agent.sources.github_policy import assert_read_only, policy_summary

API = "https://api.github.com"
PXD_DIR_RE = re.compile(r"^(PXD\d+)", re.I)


@dataclass
class RepoRef:
    owner: str
    name: str
    branch: str = "main"
    url: str = ""

    @property
    def slug(self) -> str:
        return f"{self.owner}/{self.name}"


def parse_repo_url(url: str, *, default_branch: str = "main") -> RepoRef:
    u = urlparse(url.strip())
    parts = [p for p in u.path.split("/") if p]
    if len(parts) < 2:
        raise ValueError(f"Некорректный URL репозитория: {url}")
    return RepoRef(
        owner=parts[0],
        name=parts[1].replace(".git", ""),
        branch=default_branch,
        url=f"https://github.com/{parts[0]}/{parts[1]}",
    )


class GitHubClient:
    """Только GET-операции к GitHub API."""

    def __init__(self, token: str | None = None):
        self.token = token or os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
        self._session = requests.Session()
        self._session.headers.update(
            {
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            }
        )
        if self.token:
            self._session.headers["Authorization"] = f"Bearer {self.token}"

    def policy(self) -> dict:
        return policy_summary()

    def _get(self, path: str, params: dict | None = None) -> Any:
        assert_read_only("get")
        url = path if path.startswith("http") else f"{API}{path}"
        r = self._session.get(url, params=params or {}, timeout=60)
        if r.status_code == 404:
            return None
        r.raise_for_status()
        return r.json()

    def repo_meta(self, repo: RepoRef) -> dict | None:
        return self._get(f"/repos/{repo.slug}")

    def list_contents(self, repo: RepoRef, path: str = "") -> list[dict]:
        data = self._get(f"/repos/{repo.slug}/contents/{path.strip('/')}", {"ref": repo.branch})
        if data is None:
            return []
        if isinstance(data, dict):
            return [data]
        return list(data)

    def get_file_text(self, repo: RepoRef, path: str, *, max_bytes: int = 512_000) -> dict:
        assert_read_only("get_file")
        data = self._get(f"/repos/{repo.slug}/contents/{path.strip('/')}", {"ref": repo.branch})
        if not data:
            return {"found": False, "path": path, "error": "not_found"}
        if data.get("type") != "file":
            return {"found": False, "path": path, "error": "not_a_file"}
        size = int(data.get("size") or 0)
        if size > max_bytes:
            return {
                "found": True,
                "path": path,
                "truncated": True,
                "size": size,
                "message": f"Файл слишком большой ({size} B), лимит {max_bytes}",
            }
        if data.get("content"):
            raw = base64.b64decode(data["content"])
            try:
                text = raw.decode("utf-8")
            except UnicodeDecodeError:
                text = raw.decode("utf-8", errors="replace")
            return {
                "found": True,
                "path": path,
                "size": size,
                "sha": data.get("sha"),
                "text": text,
                "html_url": data.get("html_url"),
            }
        return {"found": False, "path": path, "error": "empty"}

    def list_tree_paths(self, repo: RepoRef, *, max_paths: int = 8000) -> list[str]:
        """Рекурсивное дерево (для поиска PXD). Ограничено max_paths."""
        tree = self._get(f"/repos/{repo.slug}/git/trees/{repo.branch}", {"recursive": "1"})
        if not tree:
            return []
        paths = []
        for node in tree.get("tree") or []:
            if node.get("type") == "tree":
                continue
            paths.append(node.get("path", ""))
            if len(paths) >= max_paths:
                break
        return paths

    def list_pxd_directories(
        self,
        repo: RepoRef,
        projects_subdir: str,
    ) -> list[dict[str, Any]]:
        """
        Папки PXD* в projects_subdir (например Projects или projects).
        """
        sub = projects_subdir.strip("/")
        entries = self.list_contents(repo, sub)
        out = []
        for e in entries:
            if e.get("type") != "dir":
                continue
            name = e.get("name", "")
            m = PXD_DIR_RE.match(name)
            if m:
                out.append(
                    {
                        "pxd": m.group(1).upper(),
                        "name": name,
                        "path": e.get("path", f"{sub}/{name}"),
                        "html_url": e.get("html_url", ""),
                    }
                )
        return sorted(out, key=lambda x: x["pxd"])
