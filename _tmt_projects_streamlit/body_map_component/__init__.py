"""Bidirectional anatomical map — Streamlit custom component (self-contained frontend)."""
from __future__ import annotations

import base64
from pathlib import Path

import streamlit.components.v1 as components

_FRONTEND = Path(__file__).resolve().parent / "frontend"
_body_map = components.declare_component("body_map", path=str(_FRONTEND))

GITHUB_MAP = "https://arinaatom-cyber.github.io/TMT/"
DISCOVERY_URL = "https://arinaatom-cyber.github.io/TMT/discovery/discovery.html"
DISCOVERY_PORTAL = "https://arinaatom-cyber.github.io/TMT/discovery/index.html"


def render_body_map(
    svg: str,
    selected: str | None = None,
    *,
    height: int = 780,
    dual: bool = False,
    key: str | None = None,
) -> str | None:
    """Render interactive SVG; returns clicked organ id ('' clears selection)."""
    svg_b64 = base64.b64encode(svg.encode("utf-8")).decode("ascii")
    value = _body_map(
        svg_b64=svg_b64,
        selected=selected or "",
        height=height,
        dual=dual,
        key=key,
        default="",
    )
    if value is None:
        return None
    return str(value)


def render_map_iframe(
    selected: str | None = None,
    *,
    height: int = 1320,
    key: str | None = None,
) -> None:
    """Embed live GitHub map (scrollable, full width). key changes reload the iframe."""
    organ_q = f"?organ={selected}" if selected else ""
    src = f"{GITHUB_MAP}{organ_q}"
    # components.iframe keeps correct sizing on Streamlit Cloud (html+fixed height crops the map).
    components.iframe(src, height=height, scrolling=True)


def render_discovery_embed(*, height: int = 1200) -> None:
    components.iframe(DISCOVERY_URL, height=height, scrolling=True)
