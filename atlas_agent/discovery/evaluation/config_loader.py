"""Load evaluation YAML configuration."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import yaml

from atlas_agent.discovery.evaluation.schemas import ExclusionReason, ModelTrustLevel

logger = logging.getLogger(__name__)

_CONFIG_DIR = Path(__file__).resolve().parent / "config"


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.is_file():
        logger.warning("Config file missing: %s", path)
        return {}
    with path.open(encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}
    if not isinstance(data, dict):
        raise ValueError(f"Expected mapping in {path}")
    return data


def load_exclusion_config(path: Path | None = None) -> list[dict[str, Any]]:
    cfg = _load_yaml(path or _CONFIG_DIR / "exclusion_patterns.yaml")
    patterns = cfg.get("patterns") or []
    if not isinstance(patterns, list):
        raise ValueError("exclusion_patterns.yaml: patterns must be a list")
    return [p for p in patterns if isinstance(p, dict)]


def load_providers_config(path: Path | None = None) -> dict[str, Any]:
    return _load_yaml(path or _CONFIG_DIR / "providers.yml")


def parse_exclusion_reason(raw: str) -> ExclusionReason:
    try:
        return ExclusionReason(str(raw).lower())
    except ValueError as exc:
        raise ValueError(f"Unknown ExclusionReason: {raw}") from exc


def parse_trust_level(raw: str) -> ModelTrustLevel:
    try:
        return ModelTrustLevel(str(raw).lower())
    except ValueError as exc:
        raise ValueError(f"Unknown ModelTrustLevel: {raw}") from exc
