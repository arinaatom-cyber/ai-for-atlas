#!/usr/bin/env python3
"""Sync organ MAP / ORGAN_EXACT from human-proteome-atlas/app.js → organ_maps.json."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP_JS = ROOT.parent / "лаб иеб" / "human-proteome-atlas" / "app.js"
OUT = ROOT / "atlas_agent" / "catalog" / "organ_maps.json"


def extract_brace_object(js: str, const_name: str) -> str | None:
    m = re.search(rf"const {re.escape(const_name)}=\{{", js)
    if not m:
        return None
    i = m.end() - 1
    depth = 0
    for j in range(i, len(js)):
        if js[j] == "{":
            depth += 1
        elif js[j] == "}":
            depth -= 1
            if depth == 0:
                return js[i : j + 1]
    return None


def js_object_to_dict(block: str) -> dict[str, str]:
    """Parse simple string→string JS object (keys quoted or bare)."""
    inner = block.strip()[1:-1]
    out: dict[str, str] = {}
    # 'key':'Val' or key:'Val' or "key":"Val"
    for m in re.finditer(
        r"(?:'([^']+)'|\"([^\"]+)\"|([a-zA-Z_][\w]*))\s*:\s*'([^']*)'",
        inner,
    ):
        key = m.group(1) or m.group(2) or m.group(3)
        out[key] = m.group(4)
    return out


def main() -> int:
    if not APP_JS.is_file():
        print(f"Missing {APP_JS}", file=sys.stderr)
        return 1
    js = APP_JS.read_text(encoding="utf-8")
    data = {}
    for name in ("MAP", "ORGAN_EXACT"):
        block = extract_brace_object(js, name)
        if not block:
            print(f"Could not find {name}", file=sys.stderr)
            return 1
        data[name] = js_object_to_dict(block)
        print(f"{name}: {len(data[name])} entries")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
