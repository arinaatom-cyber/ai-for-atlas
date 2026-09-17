from __future__ import annotations

import time
from typing import Any

import requests

from atlas_agent.discovery.organism_terms import is_human_text, is_non_human_text
from atlas_agent.discovery.tmt_plex import infer_tmt_plex

PDC_GRAPHQL = "https://pdc.cancer.gov/graphql"
ATLAS_PLEXES = set(range(7, 19))
REJECT_PLEXES = {2, 6}
MIN_ATLAS_CHANNELS = 7


def _post_graphql(query: str, *, timeout: int = 120, retries: int = 3) -> dict:
    for attempt in range(retries):
        try:
            r = requests.post(PDC_GRAPHQL, json={"query": query}, timeout=timeout)
            if r.status_code == 200:
                body = r.json()
                if not body.get("errors"):
                    return body
            if attempt < retries - 1:
                time.sleep(2 ** attempt)
        except requests.RequestException:
            if attempt < retries - 1:
                time.sleep(2 ** attempt)
    return {}


def fetch_study_summary() -> list[dict[str, Any]]:
    q = """query {
      uiStudySummary {
        pdc_study_id
        submitter_id_name
        experiment_type
        program_name
        project_name
        disease_type
        analytical_fraction
        primary_site
      }
    }"""
    body = _post_graphql(q)
    return body.get("data", {}).get("uiStudySummary") or []


def _infer_plex_from_experiment(experiment_type: str) -> int | None:
    return infer_tmt_plex(experiment_type or "")


def _pdc_human_fields(s: dict[str, Any]) -> tuple[bool, bool]:
    blob = " ".join(
        str(s.get(k) or "")
        for k in (
            "submitter_id_name",
            "project_name",
            "program_name",
            "disease_type",
            "primary_site",
            "experiment_type",
        )
    )
    if is_non_human_text(blob):
        return False, False
    if is_human_text(blob):
        return True, False
    return True, True


def _study_to_record(s: dict[str, Any]) -> dict[str, Any]:
    acc = (s.get("pdc_study_id") or "").upper()
    exp = s.get("experiment_type") or ""
    title_parts = [
        s.get("submitter_id_name") or "",
        s.get("project_name") or "",
        s.get("program_name") or "",
    ]
    title = " — ".join(p for p in title_parts if p) or f"PDC study {acc}"
    plex = _infer_plex_from_experiment(exp)
    human, assumed = _pdc_human_fields(s)
    rec: dict[str, Any] = {
        "accession": acc,
        "title": title[:500],
        "description": f"{s.get('disease_type', '')} · {s.get('analytical_fraction', '')}".strip(" ·"),
        "program": s.get("program_name", ""),
        "disease": s.get("disease_type", ""),
        "experiment_type": exp,
        "analytical_fraction": s.get("analytical_fraction", ""),
        "primary_site": s.get("primary_site", ""),
        "inferred_plex": plex,
        "tmt_detected": bool(plex or (exp and "tmt" in exp.lower())),
        "human": human,
        "source": "pdc_api",
        "consortium": "PDC",
        "url": f"https://proteomic.datacommons.cancer.gov/pdc/study/{acc}",
    }
    if assumed:
        rec["human_assumed"] = True
    if plex is None and rec["tmt_detected"]:
        rec["tmt_plex_unspecified_pdc"] = True
    return rec


def _program_excluded(program_name: str, exclude_patterns: list[str]) -> bool:
    prog = (program_name or "").lower()
    return any(pat.lower() in prog for pat in exclude_patterns if pat)


def search_pdc_tmt_studies(
    *,
    known_accessions: set[str] | None = None,
    allowed_plexes: set[int] | None = None,
    reject_plexes: set[int] | None = None,
    min_channels: int = MIN_ATLAS_CHANNELS,
    max_channels: int = 18,
    programs: list[str] | None = None,
    exclude_programs: list[str] | None = None,
    stats: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    known = {a.upper() for a in (known_accessions or set())}
    program_filter = {p.lower() for p in (programs or [])}
    reject = reject_plexes if reject_plexes is not None else REJECT_PLEXES
    ok_plex = allowed_plexes or ATLAS_PLEXES
    exclude_prog = list(exclude_programs or [])
    out: list[dict[str, Any]] = []
    unspecified = 0

    studies = fetch_study_summary()
    if stats is not None:
        stats["failed_requests"] = 0 if studies else 1

    for s in studies:
        exp = str(s.get("experiment_type") or "")
        if "tmt" not in exp.lower():
            continue
        acc = (s.get("pdc_study_id") or "").upper()
        if not acc or acc in known:
            continue
        if exclude_prog and _program_excluded(str(s.get("program_name") or ""), exclude_prog):
            continue
        plex = _infer_plex_from_experiment(exp)
        if plex is None:
            unspecified += 1
        elif plex in reject or plex < min_channels or plex > max_channels:
            continue
        elif plex not in ok_plex:
            continue
        if program_filter:
            prog = str(s.get("program_name") or "").lower()
            if not any(p in prog for p in program_filter):
                continue
        out.append(_study_to_record(s))
    if stats is not None:
        stats["tmt_plex_unspecified"] = unspecified
    return out
