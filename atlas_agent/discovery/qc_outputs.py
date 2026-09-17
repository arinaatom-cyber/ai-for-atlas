from __future__ import annotations

import re

from atlas_agent.discovery.filters import get_project_accession, select_new_projects


def _with_accession(items: list[dict], known: set[str] | None = None) -> list[dict]:
    known = {a.upper() for a in (known or set())}
    known_pmids = {re.sub(r"\D", "", x) for x in known if re.sub(r"\D", "", x)}
    out = []
    seen: set[str] = set()
    for item in items:
        if item.get("source") == "literature_semantic_candidate":
            pmid = re.sub(r"\D", "", str(item.get("pmid") or ""))
            if not pmid or pmid in known_pmids:
                continue
            label = f"PMID:{pmid}"
            if label in seen:
                continue
            seen.add(label)
            row = dict(item)
            row["project_accession"] = label
            row["accession"] = label
            out.append(row)
            continue
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
    manual_raw = buckets.get("requires_manual_check", [])
    literature_manual = [
        x for x in manual_raw if x.get("source") == "literature_semantic_candidate"
    ]
    repository_manual = [
        x for x in manual_raw if x.get("source") != "literature_semantic_candidate"
    ]
    manual = _with_accession(literature_manual, known_accessions)
    repo_manual = _with_accession(repository_manual, known_accessions)
    rejected = _with_accession(buckets.get("rejected", []), known_accessions)
    return {
        "candidates": candidates,
        "new_projects": candidates,
        "manual_check": manual,
        "repository_manual": repo_manual,
        "rejected_material": rejected,
    }
