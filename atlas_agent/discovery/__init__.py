"""Discovery package — lazy exports to avoid import cycles."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

    import pandas as pd


def run_discovery_scan(df: "pd.DataFrame", cfg: dict, *, root: "Path | None" = None) -> dict:
    from atlas_agent.discovery.agent import run_discovery_scan as _run

    return _run(df, cfg, root=root)


def load_catalog_readonly(cfg: dict | None = None) -> "pd.DataFrame":
    from atlas_agent.discovery.agent import load_catalog_readonly as _load

    return _load(cfg)


def policy_summary() -> dict:
    from atlas_agent.discovery.policy import policy_summary as _policy

    return _policy()


__all__ = ["run_discovery_scan", "load_catalog_readonly", "policy_summary"]
