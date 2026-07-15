"""PDC GraphQL — профессиональный поиск TMT-исследований (read-only)."""
from __future__ import annotations

import re
import time
from typing import Any

import requests

PDC_GRAPHQL = "https://pdc.cancer.gov/graphql"
TMT_TYPE_RE = re.compile(r"tmtpro\s*(\d{1,2})|tmt\s*[- ]?(\d{1,2})\b", re.I)
ATLAS_PLEXES = {10, 11, 12, 16}
REJECT_PLEXES = {6, 7, 8, 9, 18}  # TMT6 и прочие <10ch / TMT18 — не атлас
MIN_ATLAS_CHANNELS = 10


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
    """Все исследования PDC с метаданными (uiStudySummary)."""
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
    m = TMT_TYPE_RE.search(experiment_type or "")
    if m:
        for g in m.groups():
            if g:
                return int(g)
    return None


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
    return {
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
        "human": True,
        "source": "pdc_api",
        "consortium": "PDC",
        "url": f"https://proteomic.datacommons.cancer.gov/pdc/study/{acc}",
    }


def _program_excluded(program_name: str, exclude_patterns: list[str]) -> bool:
    prog = (program_name or "").lower()
    return any(pat.lower() in prog for pat in exclude_patterns if pat)


def search_pdc_tmt_studies(
    *,
    known_accessions: set[str] | None = None,
    allowed_plexes: set[int] | None = None,
    reject_plexes: set[int] | None = None,
    min_channels: int = MIN_ATLAS_CHANNELS,
    max_channels: int = 16,
    programs: list[str] | None = None,
    exclude_programs: list[str] | None = None,
) -> list[dict[str, Any]]:
    """
    TMT-исследования PDC: только >6 каналов (10/11/12/16), без TMT6/TMT18.
    Исключает ID из TMT ATLAS + CPTAC + exclude_programs (напр. CPTAC program).
    """
    known = {a.upper() for a in (known_accessions or set())}
    program_filter = {p.lower() for p in (programs or [])}
    reject = reject_plexes if reject_plexes is not None else REJECT_PLEXES
    ok_plex = allowed_plexes or ATLAS_PLEXES
    exclude_prog = list(exclude_programs or [])
    out: list[dict[str, Any]] = []

    for s in fetch_study_summary():
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
            continue
        if plex in reject or plex < min_channels or plex > max_channels:
            continue
        if plex not in ok_plex:
            continue
        if program_filter:
            prog = str(s.get("program_name") or "").lower()
            if not any(p in prog for p in program_filter):
                continue
        out.append(_study_to_record(s))
    return out
