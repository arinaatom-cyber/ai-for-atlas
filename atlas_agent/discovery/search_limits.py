from __future__ import annotations

from typing import Any


def optional_cap(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        n = int(value)
    except (TypeError, ValueError):
        return None
    return None if n <= 0 else n


def cap_label(value: Any, *, ru: str = "без лимита", en: str = "no limit") -> str:
    cap = optional_cap(value)
    return str(cap) if cap is not None else ru
