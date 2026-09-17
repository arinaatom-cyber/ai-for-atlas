from __future__ import annotations

from atlas_agent.viz.i18n_loader import en as _en
from atlas_agent.viz.i18n_loader import ru as _ru

BRAND_NAME = "Human Cancer-Associated TMT Proteome Atlas"


def ru(key: str) -> str:
    val = _ru(key)
    return val if val != key else _en(key)


def en(key: str) -> str:
    return _en(key)
