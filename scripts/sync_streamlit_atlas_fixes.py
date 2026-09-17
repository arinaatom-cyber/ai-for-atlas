#!/usr/bin/env python3
"""Copy Streamlit atlas fixes + catalog CSV into arinaatom-cyber/tmt-projects."""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATCH = ROOT / "_tmt_projects_streamlit"
TARGET = ROOT.parent / "tmt-projects"
CATALOG = ROOT / "data" / "projects.csv"

FILES = [
    "streamlit_app.py",
    "streamlit_theme.py",
    "organ_atlas.py",
    "body_map_component/__init__.py",
    "body_map_component/frontend/index.html",
    "body_map_html.py",
    ".streamlit/config.toml",
]


def main() -> int:
    if not PATCH.is_dir():
        print(f"Missing patch dir: {PATCH}")
        return 1
    if not TARGET.is_dir():
        print(f"Clone tmt-projects first: git clone https://github.com/arinaatom-cyber/tmt-projects.git")
        print(f"Expected: {TARGET}")
        return 1

    for rel in FILES:
        src = PATCH / rel
        dst = TARGET / rel
        if not src.is_file():
            print(f"Skip missing patch file: {rel}")
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        print(f"copied {rel}")

    if CATALOG.is_file():
        dst_csv = TARGET / "data" / "projects.csv"
        dst_csv.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(CATALOG, dst_csv)
        print(f"copied data/projects.csv ({CATALOG.stat().st_size} bytes)")

    print("\nNext (from tmt-projects folder):")
    print("  git add streamlit_app.py organ_atlas.py body_map_component data/projects.csv")
    print("  git commit -m \"Fix body map component and Database-column repository filter\"")
    print("  git push")
    print("Then redeploy Streamlit Cloud (human-cancser-tmt-proteome-atlas).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
