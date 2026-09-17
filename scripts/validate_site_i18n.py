#!/usr/bin/env python3
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def load_i18n_keys() -> set[str]:
    js = (ROOT / "atlas_agent/viz/site_assets/i18n.js").read_text(encoding="utf-8")
    return set(re.findall(r"^\s+(\w+):\s", js, re.M)) | {"brand_title"}


def main() -> int:
    keys = load_i18n_keys()
    missing: dict[str, list[str]] = {}
    empty_nodes: list[str] = []

    for hp in sorted((ROOT / "docs").rglob("*.html")):
        if "cohorts.html" in hp.name and hp.stat().st_size < 600:
            continue
        text = hp.read_text(encoding="utf-8", errors="replace")
        rel = hp.relative_to(ROOT).as_posix()
        for m in re.finditer(r'data-i18n="([^"]+)"', text):
            k = m.group(1)
            if k not in keys:
                missing.setdefault(k, []).append(rel)
        for m in re.finditer(r'data-i18n="([^"]+)"[^>]*>\s*</', text):
            empty_nodes.append(f"{rel}: {m.group(1)}")

    print("Missing keys:", len(missing))
    for k, files in sorted(missing.items())[:40]:
        print(f"  {k}: {files[0]}")

    print("\nEmpty i18n nodes (no fallback text):", len(empty_nodes))
    for x in empty_nodes[:25]:
        print(f"  {x}")
    if len(empty_nodes) > 25:
        print(f"  ... +{len(empty_nodes) - 25} more")

    return 1 if missing or empty_nodes else 0


if __name__ == "__main__":
    raise SystemExit(main())
