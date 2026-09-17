"""Single organism / cell-line vocabulary for Discovery (human-only atlas)."""
from __future__ import annotations

import re

NON_HUMAN_PATTERN = (
    r"\b("
    r"mouse|mice|murine|mus\s+musculus|"
    r"rat\b|rattus|rodent|"
    r"rabbit|oryctolagus|hamster|cricetulus|"
    r"guinea\s+pig|cavia|"
    r"sheep\b|ovine|lamb\b|goat\b|caprine|"
    r"porcine|pig\b|swine|"
    r"bovine|cattle|cow\b|"
    r"canine|dog\b|feline|\bcats\b|"
    r"equine|horse\b|"
    r"macaque|macaca|rhesus|primate|"
    r"chicken|gallus|"
    r"zebrafish|danio|medaka|xenopus|frog\b|teleost|oryzias|"
    r"drosophila|fruit\s+fly|"
    r"caenorhabditis|\bc\.\s*elegans\b|"
    r"chlamydomonas|arabidopsis|yeast|saccharomyces|"
    r"maize|plant\b|protist|"
    r"salmonella|escherichia|bacterial|"
    r"xenograft\s+in\s+mouse|nude\s+mice|mc38|\bb16\b|"
    r"animal\s+tissue|non[- ]?human"
    r")\b"
)

HUMAN_PATTERN = (
    r"\b(human|homo\s+sapiens|patients?|clinical|donor|"
    r"human\s+subjects?|homo\s+sapien)\b"
)

HUMAN_CANCER_CELL_LINE_PATTERN = (
    r"\b((human|cancer|tumou?r)\s+cell\s+lines?|"
    r"cell\s+lines?\s+from\s+(human|patient)|"
    r"hela|mcf[- ]?7|mcf7|a549|hct116|u2os|pc[- ]?3|du145|t47d|"
    r"mda[- ]?mb|ccle|depmap)\b"
)

NON_HUMAN = re.compile(NON_HUMAN_PATTERN, re.I)
HUMAN = re.compile(HUMAN_PATTERN, re.I)
HUMAN_CANCER_CELL_LINE = re.compile(HUMAN_CANCER_CELL_LINE_PATTERN, re.I)


def is_non_human_text(text: str) -> bool:
    return bool(NON_HUMAN.search(text or ""))


def is_human_text(text: str) -> bool:
    return bool(HUMAN.search(text or "") or HUMAN_CANCER_CELL_LINE.search(text or ""))
