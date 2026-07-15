"""Gold-standard benchmark for Discovery screening (Nature Methods validation)."""
from __future__ import annotations

from atlas_agent.discovery.confidence import project_confidence
from atlas_agent.discovery.fit_rules import apply_literature_exclusions, is_non_study_literature

BENCHMARK_LITERATURE = [
    {
        "title": "Analysis of isobaric quantitative proteomic data using TMT-Integrator and FragPipe computational platform.",
        "abstract": "",
        "label": "exclude",
    },
    {
        "title": "Phosphoproteomics in Vascular Biology and Disease: Illuminating Signaling in the Vessel.",
        "abstract": "Phosphorylation profiling of endothelial cells.",
        "label": "exclude",
    },
    {
        "title": "Proteomic Analysis of Paired FFPE Tissue and Extracellular Vesicles Reveals Proteins Associated with Recurrence in Stage II Colorectal Cancer.",
        "abstract": "TMT11 quantitative proteomics in 120 patients with colorectal cancer tumor tissue.",
        "label": "watch",
    },
    {
        "title": "Murine tumor proteomics with TMT11 in xenograft models.",
        "abstract": "We studied mice bearing xenografts.",
        "label": "exclude",
    },
]

BENCHMARK_PROJECTS = [
    {
        "data_availability": {"status": "quant_table", "omics_layer": "protein"},
        "sample_design": "case_control",
        "human": True,
        "qc_status": "candidate",
        "inferred_plex": 11,
        "filter_reasons": [],
        "label": "in_atlas",
    },
    {
        "data_availability": {"status": "quant_table", "omics_layer": "mixed"},
        "sample_design": "cancer_only",
        "human": True,
        "qc_status": "candidate",
        "label": "watch",
    },
    {
        "data_availability": {"status": "phospho_table", "omics_layer": "phospho"},
        "label": "exclude",
    },
]


def _tier_to_class(tier: str, label: str) -> bool:
    if label == "in_atlas":
        return tier == "A"
    if label == "watch":
        return tier in ("B", "C")
    if label == "exclude":
        return tier == "D"
    return False


def evaluate_literature_benchmark() -> dict[str, float | int]:
    correct = 0
    for case in BENCHMARK_LITERATURE:
        item = apply_literature_exclusions(
            {"title": case["title"], "abstract": case.get("abstract", ""), "abstract_ai": {}}
        )
        fit = item.get("atlas_fit", "no")
        if case["label"] == "exclude":
            ok = fit == "no" or is_non_study_literature(case["title"], case.get("abstract", ""))
        elif case["label"] == "watch":
            ok = fit in ("yes", "maybe")
        else:
            ok = False
        if ok:
            correct += 1
    n = len(BENCHMARK_LITERATURE)
    return {"accuracy": correct / n if n else 0.0, "n": n, "correct": correct}


def evaluate_project_benchmark() -> dict[str, float | int]:
    correct = 0
    for case in BENCHMARK_PROJECTS:
        item = {k: v for k, v in case.items() if k != "label"}
        tier, _, _ = project_confidence(item)
        if _tier_to_class(tier, case["label"]):
            correct += 1
    n = len(BENCHMARK_PROJECTS)
    return {"accuracy": correct / n if n else 0.0, "n": n, "correct": correct}
