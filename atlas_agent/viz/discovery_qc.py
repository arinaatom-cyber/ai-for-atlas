from __future__ import annotations

import re
from typing import Any

# PubMed is ~42 million today (8 digits). Floor drops 1–6 digit junk and
# accidental Europe PMC PPR fragments; ceiling is 8 digits so a 9-digit
# test ID like 609300501 is rejected. Raise PMID_MAX to 999_999_999 when
# PubMed crosses 100 million — do not lock the check to a single length.
PMID_MIN = 1_000_000
PMID_MAX = 99_999_999

_WORD_RE = re.compile(r"[A-Za-z]{4,}")
_SHORT_RE = re.compile(r"\b[A-Za-z]{3,4}\b")
_ACRONYM_RE = re.compile(r"\b[A-Z]{2,4}\b")
_STOP = frozenset(
    {
        "that",
        "this",
        "with",
        "from",
        "using",
        "based",
        "study",
        "studies",
        "analysis",
        "analyses",
        "human",
        "cells",
        "cell",
        "protein",
        "proteins",
        "data",
        "after",
        "into",
        "over",
        "under",
        "between",
        "among",
        "their",
        "have",
        "been",
        "were",
        "which",
        "also",
        "than",
        "such",
        "only",
        "more",
        "most",
        "high",
        "level",
        "levels",
        "role",
        "used",
        "via",
        "and",
        "for",
        "the",
        "cancer",
        "cancers",
        "tumor",
        "tumour",
        "tumors",
        "patient",
        "patients",
        "tissue",
        "tissues",
        "proteome",
        "proteomic",
        "proteomics",
        "sample",
        "samples",
        "tandem",
        "mass",
        "compare",
        "compared",
        "effect",
        "effects",
        "group",
        "groups",
        "significant",
        "week",
        "weeks",
        "month",
        "months",
        "treatment",
        "treatments",
        "clinical",
        "response",
        "responses",
        "associated",
        "target",
        "therapy",
        "inhibition",
        "quantitative",
        "global",
        "primary",
        "chronic",
        "serum",
        "culture",
        "cultures",
        "diameter",
        "size",
        "uncovers",
        "serial",
        "duration",
    }
)
# Synonyms only — not stem/prefix. glioma/GBM is a hit; hepatocellular/hepatocyte is not.
_ALIASES = {
    "glioma": "glioma",
    "gliomas": "glioma",
    "glioblastoma": "glioma",
    "gbm": "glioma",
    "crc": "colorectal",
    "colorectal": "colorectal",
    "colon": "colorectal",
    "myeloma": "myeloma",
    "aml": "leukemia",
    "leukemia": "leukemia",
    "leukaemia": "leukemia",
}
# Case-sensitive acronyms. "12 mm" must not become myeloma; "MM cell lines" may.
_ACRONYMS = {
    "MM": "myeloma",
    "CRC": "colorectal",
    "GBM": "glioma",
    "AML": "leukemia",
}
_STRONG = frozenset(_ALIASES.values()) | frozenset(_ACRONYMS.values())


def digits_pmid(raw: object) -> str:
    return re.sub(r"\D", "", str(raw or "").split(".")[0])


def is_plausible_pmid(raw: object) -> bool:
    digits = digits_pmid(raw)
    if not digits.isdigit():
        return False
    n = int(digits)
    return PMID_MIN <= n <= PMID_MAX


def _canonical(word: str) -> str:
    w = word.lower()
    return _ALIASES.get(w, w)


def content_tokens(text: object) -> set[str]:
    blob = str(text or "")
    toks = {
        _canonical(w)
        for w in _WORD_RE.findall(blob)
        if w.lower() not in _STOP
    }
    for w in _ACRONYM_RE.findall(blob):
        canon = _ACRONYMS.get(w)
        if canon:
            toks.add(canon)
    for w in _SHORT_RE.findall(blob):
        key = w.lower()
        if key in _ALIASES:
            toks.add(_ALIASES[key])
    return toks


def abstract_matches_title(title: object, abstract: object, *, min_overlap: int = 2) -> bool:
    """Canonical token overlap, not embeddings and not stem prefixes.

    One shared token is enough only if it is a disease alias (glioma, CRC,
    myeloma, …). Otherwise at least two non-stop tokens must overlap.
    Empty title or abstract is unknown, not a mismatch.
    """
    title_toks = content_tokens(title)
    abs_toks = content_tokens(abstract)
    if not title_toks or not abs_toks:
        return True
    shared = title_toks & abs_toks
    if shared & _STRONG:
        return True
    return len(shared) >= min_overlap


def _clear_publication(item: dict[str, Any], reason: str) -> None:
    item["pmid"] = ""
    item["pubmed_url"] = ""
    item.pop("linked_pmid", None)
    item["publication_qc"] = reason


def sanitize_item_publication(item: dict[str, Any]) -> dict[str, Any]:
    pmid = digits_pmid(item.get("pmid"))
    title = str(item.get("title") or "")
    abstract = " ".join(
        str(item.get(k) or "")
        for k in ("abstract", "abstract_snippet", "article_description", "finding")
    )
    if pmid and not is_plausible_pmid(pmid):
        _clear_publication(item, "pmid_out_of_range")
        pmid = ""
    if pmid and abstract and title and not abstract_matches_title(title, abstract):
        for key in ("abstract", "abstract_snippet", "article_description"):
            if item.get(key) and not abstract_matches_title(title, item.get(key)):
                item[key] = ""
        _clear_publication(item, "abstract_mismatch")
    return item


def _title_key(item: dict[str, Any]) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(item.get("title") or "").lower()).strip()


def dedupe_literature(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen_pmid: set[str] = set()
    seen_title: set[str] = set()
    out: list[dict[str, Any]] = []
    for item in items:
        sanitize_item_publication(item)
        pmid = digits_pmid(item.get("pmid"))
        title_key = _title_key(item)
        if pmid and not is_plausible_pmid(pmid):
            continue
        if pmid and pmid in seen_pmid:
            continue
        if title_key and title_key in seen_title:
            continue
        if pmid:
            seen_pmid.add(pmid)
        if title_key:
            seen_title.add(title_key)
        out.append(item)
    return out
