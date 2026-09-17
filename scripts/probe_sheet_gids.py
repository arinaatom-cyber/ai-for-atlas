#!/usr/bin/env python3
from __future__ import annotations

import io
import re
import sys

import requests

SID = "1M6hc3vmk1bNchMvEwXsIyyO5iq3mAzP877HTXzhzg38"


def probe(gid: str) -> str | None:
    url = f"https://docs.google.com/spreadsheets/d/{SID}/export?format=csv&gid={gid}"
    r = requests.get(url, timeout=30)
    if r.status_code != 200:
        return None
    line = r.text.split("\n", 1)[0]
    return line


def main() -> int:
    candidates = [
        "0",
        "1072380314",
        "1418436111",
        "493912572",
        "1844901170",
        "1598805968",
        "1204179297",
        "1877884524",
        "2059888936",
    ]
    if len(sys.argv) > 1:
        candidates = sys.argv[1:]

    html = requests.get(
        f"https://docs.google.com/spreadsheets/d/{SID}/edit",
        timeout=30,
        headers={"User-Agent": "Mozilla/5.0"},
    ).text
    candidates.extend(re.findall(r'"sheetId":(\d+)', html))
    seen: set[str] = set()
    for gid in candidates:
        if gid in seen:
            continue
        seen.add(gid)
        head = probe(gid)
        if not head:
            continue
        label = "General?" if "Identifier" in head else ("TMT?" if "Project ID" in head else "other")
        print(f"gid={gid} [{label}] {head[:120]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
