from __future__ import annotations

import json
import re
from pathlib import Path

_REPO_ID = re.compile(r"^(PXD|PDC|MSV|IPX)\d", re.I)

_OFF_ATLAS_MARKERS = (
    "off-atlas disease",
    "off-atlas",
    "ophthalmology",
    "retinal detachment",
    "proliferative vitreoretinopathy",
)


def _acc_from_item(item: dict) -> str:
    for key in ("accession", "project_accession"):
        v = str(item.get(key) or "").strip().upper()
        if v and _REPO_ID.match(v):
            return v
    return ""


def _reasons_text(item: dict) -> str:
    parts: list[str] = []
    for r in item.get("filter_reasons") or []:
        parts.append(str(r))
    parts.append(str(item.get("recommendation") or ""))
    parts.append(str(item.get("verdict") or ""))
    return " ".join(parts).lower()


def _is_persistent_exclude(item: dict) -> bool:
    rec = str(item.get("recommendation") or "")
    if rec in ("rejected", "rejected_previously_removed", "already_have"):
        return True
    if str(item.get("verdict") or "").lower() in ("exclude", "rejected", "already_in_catalog"):
        return True
    blob = _reasons_text(item)
    if any(m in blob for m in _OFF_ATLAS_MARKERS):
        return True
    return False


def load_scan_exclusions(base: Path, *, max_scans: int = 12) -> set[str]:
    hist = base / "data" / "discovery_history"
    if not hist.is_dir():
        return set()

    paths: list[Path] = []
    latest = hist / "latest.json"
    if latest.is_file():
        paths.append(latest)
    paths.extend(sorted(hist.glob("scan_*.json"), reverse=True)[:max_scans])

    seen_files: set[str] = set()
    out: set[str] = set()
    buckets_always = ("rejected_material", "rejected", "already_in_catalog")

    for path in paths:
        key = str(path.resolve())
        if key in seen_files:
            continue
        seen_files.add(key)
        try:
            report = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue

        for bucket in buckets_always:
            for item in report.get(bucket) or []:
                acc = _acc_from_item(item)
                if acc:
                    out.add(acc)

        for bucket in ("filtered_out", "candidates", "new_projects", "manual_check"):
            for item in report.get(bucket) or []:
                if not _is_persistent_exclude(item):
                    continue
                acc = _acc_from_item(item)
                if acc:
                    out.add(acc)

    extra = base / "data" / "discovery_excluded.txt"
    if extra.is_file():
        for line in extra.read_text(encoding="utf-8").splitlines():
            acc = line.strip().upper().split("#", 1)[0].strip()
            if acc and _REPO_ID.match(acc):
                out.add(acc)

    return out
