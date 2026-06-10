"""Сборка candidate / manual-check / rejected списков (без изменения CSV)."""
from __future__ import annotations

from atlas_agent.discovery.filters import get_project_accession, select_new_projects


def _with_accession(items: list[dict], known: set[str] | None = None) -> list[dict]:
    known = {a.upper() for a in (known or set())}
    out = []
    seen: set[str] = set()
    for item in items:
        acc = get_project_accession(item)
        if not acc or acc in seen or acc in known:
            continue
        seen.add(acc)
        row = dict(item)
        row["project_accession"] = acc
        row["accession"] = acc
        out.append(row)
    return out


def build_qc_outputs(
    buckets: dict,
    known_accessions: set[str],
) -> dict:
    candidates = select_new_projects(
        buckets.get("recommended", []),
        known_accessions,
        verdict="recommended",
        qc_status="candidate",
    )
    manual = _with_accession(buckets.get("requires_manual_check", []), known_accessions)
    rejected = _with_accession(buckets.get("rejected", []), known_accessions)
    return {
        "candidates": candidates,
        "new_projects": candidates,
        "manual_check": manual,
        "rejected_material": rejected,
    }
