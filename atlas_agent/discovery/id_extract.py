from __future__ import annotations

import re

ID_PATTERNS = {
    "PXD": re.compile(r"\b(PXD\d{6,9})\b", re.I),
    "PDC": re.compile(r"\b(PDC\d{6,9})\b", re.I),
    "MSV": re.compile(r"\b(MSV\d{6,12})\b", re.I),
    "IPX": re.compile(r"\b(IPX\d{6,12})\b", re.I),
    "CPTAC": re.compile(r"\b(CPTAC-[A-Z0-9-]+)\b", re.I),
}

PMID_STRICT = re.compile(
    r"\b(?:PMID|PubMed)(?:\s*ID)?\s*[:#=-]?\s*(\d{7,9})\b",
    re.I,
)
PMID_LOOSE = re.compile(r"\b(\d{7,9})\b")


def extract_ids_from_text(text: str) -> dict[str, list[str]]:
    found: dict[str, list[str]] = {}
    blob = text or ""
    for kind, pat in ID_PATTERNS.items():
        hits = sorted({m.group(1).upper() for m in pat.finditer(blob)})
        if hits:
            found[kind] = hits
    pmids = sorted({m.group(1) for m in PMID_STRICT.finditer(blob)})
    if pmids:
        found["PMID"] = pmids
    return found


def extract_loose_pmids(text: str) -> list[str]:
    blob = text or ""
    strict = set(extract_ids_from_text(blob).get("PMID") or [])
    loose: list[str] = []
    seen: set[str] = set()
    for m in PMID_LOOSE.finditer(blob):
        n = m.group(1)
        if n in strict or n in seen:
            continue
        seen.add(n)
        loose.append(n)
    return loose
