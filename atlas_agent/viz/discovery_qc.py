from __future__ import annotations

import re
from typing import Any

_PMID_RE = re.compile(r"^\d{8}$")
_WORD_RE = re.compile(r"[A-Za-z]{4,}")
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
    }
)


def digits_pmid(raw: object) -> str:
    return re.sub(r"\D", "", str(raw or "").split(".")[0])


def is_plausible_pmid(raw: object) -> bool:
    return bool(_PMID_RE.fullmatch(digits_pmid(raw)))


def content_tokens(text: object) -> set[str]:
    return {w.lower() for w in _WORD_RE.findall(str(text or "")) if w.lower() not in _STOP}


def abstract_matches_title(title: object, abstract: object, *, min_overlap: int = 1) -> bool:
    title_toks = content_tokens(title)
    abs_toks = content_tokens(abstract)
    if not title_toks or not abs_toks:
        return True
    return len(title_toks & abs_toks) >= min_overlap


def _clear_publication(item: dict[str, Any]) -> None:
    item["pmid"] = ""
    item["pubmed_url"] = ""
    item.pop("linked_pmid", None)


def sanitize_item_publication(item: dict[str, Any]) -> dict[str, Any]:
    pmid = digits_pmid(item.get("pmid"))
    title = str(item.get("title") or "")
    abstract = " ".join(
        str(item.get(k) or "")
        for k in ("abstract", "abstract_snippet", "article_description", "finding")
    )
    if pmid and not is_plausible_pmid(pmid):
        _clear_publication(item)
        pmid = ""
    if pmid and abstract and title and not abstract_matches_title(title, abstract):
        for key in ("abstract", "abstract_snippet", "article_description"):
            if item.get(key) and not abstract_matches_title(title, item.get(key)):
                item[key] = ""
        _clear_publication(item)
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
