#!/usr/bin/env python3
"""beforeShellExecution: block destructive commands on data/projects.csv."""
from __future__ import annotations

import json
import re
import sys

CSV = r"projects\.csv"
BLOCK_PATTERNS = [
    re.compile(rf"(del|erase)\s+.*{CSV}", re.I),
    re.compile(rf"Remove-Item\s+.*{CSV}", re.I),
    re.compile(rf"rm\s+.*{CSV}", re.I),
    re.compile(rf"git\s+checkout\s+.*--\s+.*{CSV}", re.I),
    re.compile(rf">\s*.*{CSV}", re.I),
    re.compile(rf"Out-File\s+.*{CSV}", re.I),
    re.compile(rf"Set-Content\s+.*{CSV}", re.I),
    re.compile(rf"shutil\.rmtree|os\.remove.*{CSV}", re.I),
]

ALLOW_HINTS = [
    "run_revisor.py add",
    "load_projects_table",
    "read_text",
    "read_csv",
    "run_discovery",
    "discovery",
]


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError:
        print(json.dumps({"permission": "allow"}))
        return 0

    cmd = str(payload.get("command") or payload.get("cmd") or "")
    if not cmd or CSV.replace("\\", "") not in cmd.lower().replace("\\", "/"):
        print(json.dumps({"permission": "allow"}))
        return 0

    for pat in BLOCK_PATTERNS:
        if pat.search(cmd):
            if any(h.lower() in cmd.lower() for h in ALLOW_HINTS):
                print(json.dumps({"permission": "allow"}))
                return 0
            print(
                json.dumps(
                    {
                        "permission": "deny",
                        "user_message": "Blocked: destructive command on data/projects.csv. Catalog is read-only.",
                        "agent_message": "projects.csv must not be deleted or overwritten. Use run_revisor.py add --apply after user approval.",
                    },
                    ensure_ascii=False,
                )
            )
            return 0

    print(json.dumps({"permission": "allow"}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
