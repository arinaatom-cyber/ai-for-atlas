"""Flatten Discovery candidates to CSV columns matching the public table."""
from __future__ import annotations

import csv
from pathlib import Path
from typing import Any, Iterable

from atlas_agent.viz.discovery_table_shared import flatten_candidate_row

FLAT_COLUMNS = [
    "accession",
    "source",
    "year",
    "title",
    "organ",
    "disease",
    "finding",
    "tmt_label",
    "verdict",
    "pmid",
    "url",
]


def iter_flat_candidates(
    items: Iterable[dict[str, Any]],
    *,
    profile: dict | None = None,
) -> list[dict[str, str]]:
    return [flatten_candidate_row(it, profile=profile) for it in items]


def write_candidates_csv(
    items: Iterable[dict[str, Any]],
    path: str | Path,
    *,
    profile: dict | None = None,
) -> int:
    rows = iter_flat_candidates(items, profile=profile)
    dest = Path(path)
    dest.parent.mkdir(parents=True, exist_ok=True)
    with dest.open("w", encoding="utf-8-sig", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=FLAT_COLUMNS, delimiter=";")
        w.writeheader()
        w.writerows(rows)
    return len(rows)
