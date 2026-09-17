from __future__ import annotations

from typing import Any

from atlas_agent.discovery.filters import classify_candidate, default_filter_config
from atlas_agent.discovery.id_extract import extract_ids_from_text, extract_loose_pmids
from atlas_agent.discovery.organism_terms import is_human_text, is_non_human_text
from atlas_agent.discovery.tmt_plex import infer_tmt_plex

FILTER_GOLD: list[dict[str, Any]] = [
    {
        "id": "crc_tmt11_tissue",
        "gold": "include",
        "item": {
            "accession": "PXD901001",
            "title": "Human colorectal cancer tumor tissue TMT 11-plex proteomics",
            "description": "Homo sapiens patients, paired tumor tissue, protein groups, TMT labeling.",
            "human": True,
            "inferred_plex": 11,
            "tmt_detected": True,
            "source": "pride_search_v3",
        },
    },
    {
        "id": "gbm_tmt16_tissue",
        "gold": "include",
        "item": {
            "accession": "PXD901002",
            "title": "Glioblastoma surgical specimen TMTpro 16-plex protein groups",
            "description": "Patients with glioblastoma, tumor tissue, Homo sapiens, TMT labeling.",
            "human": True,
            "inferred_plex": 16,
            "tmt_detected": True,
            "source": "pride_search_v3",
        },
    },
    {
        "id": "mouse_liver",
        "gold": "exclude",
        "item": {
            "accession": "PXD901010",
            "title": "Murine liver TMT11 proteomics",
            "description": "Mus musculus tissue TMT 11-plex protein groups.",
            "human": False,
            "inferred_plex": 11,
            "tmt_detected": True,
            "source": "pride_search_v3",
        },
    },
    {
        "id": "rabbit",
        "gold": "exclude",
        "item": {
            "accession": "PXD901011",
            "title": "Rabbit muscle TMT 10-plex proteomics",
            "description": "Oryctolagus cuniculus skeletal muscle TMT labeling.",
            "human": True,
            "inferred_plex": 10,
            "tmt_detected": True,
            "source": "pride_search_v3",
        },
    },
    {
        "id": "tmt6",
        "gold": "exclude",
        "item": {
            "accession": "PXD901012",
            "title": "Human tumor tissue TMT6 proteomics",
            "description": "Homo sapiens patients, tumor tissue, TMT6 protein groups.",
            "human": True,
            "inferred_plex": 6,
            "tmt_detected": True,
            "source": "pride_search_v3",
        },
    },
    {
        "id": "plasma_only",
        "gold": "exclude",
        "item": {
            "accession": "PXD901013",
            "title": "Plasma proteomics from cancer patients TMT10",
            "description": "Homo sapiens patients, plasma samples, TMT 10-plex protein groups.",
            "human": True,
            "inferred_plex": 10,
            "tmt_detected": True,
            "source": "pride_search_v3",
        },
    },
    {
        "id": "phospho_only",
        "gold": "exclude",
        "item": {
            "accession": "PXD901014",
            "title": "Phosphoproteomics of bladder cancer TMT 10-plex",
            "description": "Homo sapiens tumor tissue, phosphoproteome only, no global proteome.",
            "human": True,
            "inferred_plex": 10,
            "tmt_detected": True,
            "source": "pride_search_v3",
        },
    },
    {
        "id": "already_pxd",
        "gold": "exclude",
        "item": {
            "accession": "PXD000001",
            "title": "Human colorectal tumor tissue TMT 11-plex",
            "description": "Homo sapiens patients, tumor tissue, protein groups.",
            "human": True,
            "inferred_plex": 11,
            "tmt_detected": True,
            "source": "pride_search_v3",
        },
        "catalog": {"pmids": set(), "accessions": {"PXD000001"}},
    },
    {
        "id": "date_not_pmid",
        "gold": "review",
        "item": {
            "accession": "PXD901020",
            "title": "Human colorectal tumor tissue TMT 11-plex submitted 20260917",
            "description": "Homo sapiens patients, tumor tissue, protein groups, TMT labeling.",
            "human": True,
            "inferred_plex": 11,
            "tmt_detected": True,
            "source": "pride_search_v3",
        },
        "catalog": {"pmids": {"20260917"}, "accessions": set()},
    },
    {
        "id": "strict_pmid_catalog",
        "gold": "exclude",
        "item": {
            "accession": "PXD901021",
            "title": "Human tumor tissue TMT 11-plex PMID: 38765432",
            "description": "Homo sapiens patients, tumor tissue, protein groups.",
            "human": True,
            "inferred_plex": 11,
            "tmt_detected": True,
            "source": "pride_search_v3",
            "pmid": "38765432",
        },
        "catalog": {"pmids": {"38765432"}, "accessions": set()},
    },
]

PLEX_GOLD = [
    ("sixteen-plex TMT of human tumors", 16),
    ("TMT-based 16plex proteomics", 16),
    ("16-channel TMTpro", 16),
    ("TMTpro 18-channel", 18),
    ("TMT6 plasma", 6),
    ("TMT11-Plex", 11),
]

ORGANISM_GOLD = [
    ("rabbit liver TMT", False),
    ("Drosophila proteomics", False),
    ("C. elegans TMT", False),
    ("Homo sapiens patient tumor tissue", True),
    ("human colorectal tumor tissue TMT 11-plex", True),
]


def _pred_include(out: dict[str, Any]) -> bool:
    return out.get("verdict") == "recommended"


def evaluate_filter_gold(*, cfg: dict | None = None) -> dict[str, Any]:
    cfg = cfg or default_filter_config()
    tp = fp = tn = fn = 0
    review_ok = 0
    review_n = 0
    misses: list[dict[str, str]] = []
    empty = {"pmids": set(), "accessions": set()}
    for case in FILTER_GOLD:
        catalog = case.get("catalog") or empty
        out = classify_candidate(case["item"], catalog, cfg=cfg)
        pred = _pred_include(out)
        gold = case["gold"]
        if gold == "review":
            review_n += 1
            ok = out.get("verdict") != "already_in_catalog"
            if ok:
                review_ok += 1
            else:
                misses.append({"id": case["id"], "gold": "review", "pred": out.get("verdict", "")})
            continue
        gold_inc = gold == "include"
        if gold_inc and pred:
            tp += 1
        elif (not gold_inc) and (not pred):
            tn += 1
        elif pred and not gold_inc:
            fp += 1
            misses.append({"id": case["id"], "gold": "exclude", "pred": out.get("verdict", "")})
        else:
            fn += 1
            misses.append({"id": case["id"], "gold": "include", "pred": out.get("verdict", "")})

    plex_ok = sum(1 for text, n in PLEX_GOLD if infer_tmt_plex(text) == n)
    org_ok = 0
    for text, human in ORGANISM_GOLD:
        got = is_human_text(text) and not is_non_human_text(text)
        if got == human:
            org_ok += 1
    pmid_date_ok = "PMID" not in extract_ids_from_text("submitted 20260917")
    pmid_loose = "20260917" in extract_loose_pmids("submitted 20260917")

    prec = tp / (tp + fp) if (tp + fp) else 0.0
    rec = tp / (tp + fn) if (tp + fn) else 0.0
    n = tp + fp + tn + fn
    return {
        "n": n,
        "tp": tp,
        "fp": fp,
        "tn": tn,
        "fn": fn,
        "precision": round(prec, 3),
        "recall": round(rec, 3),
        "accuracy": round((tp + tn) / n, 3) if n else 0.0,
        "review_ok": review_ok,
        "review_n": review_n,
        "misses": misses,
        "plex_cases_ok": plex_ok,
        "plex_cases_n": len(PLEX_GOLD),
        "organism_cases_ok": org_ok,
        "organism_cases_n": len(ORGANISM_GOLD),
        "pmid_date_not_strict": pmid_date_ok,
        "pmid_date_is_loose": pmid_loose,
        "label_source": "unit_cases",
    }
