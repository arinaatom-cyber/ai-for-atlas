"""Centralized evaluation thresholds — single source of truth."""

# LLM / regex scores below this are not shown or used for promotion.
DISPLAY_SCORE_MIN = 0.35

# Literature semantic resolution gates (dataset_resolve.py legacy values).
LITERATURE_SEMANTIC_MIN = 0.55
LITERATURE_RESOLVE_MIN = 0.50

# Catalog deduplication (similarity.py).
SIMILARITY_DEDUP_MIN = 0.18
SIMILARITY_CLOSE_MATCH_MIN = 0.35

# Cohort tiering.
COHORT_LARGE_N = 100
COHORT_TMT_N = 50
