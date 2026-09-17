"""Display formatting for Discovery table — titles, labels, sentence starts."""
from __future__ import annotations

import re

_DESIGN_LABELS = {
    "case-control": "Case-control",
    "case_control": "Case-control",
    "cancer-only": "Cancer-only",
    "cancer_only": "Cancer-only",
    "healthy-only": "Healthy-only",
    "healthy_only": "Healthy-only",
    "unknown": "Unknown",
}

_TOKEN_LABELS = {
    "not reported": "Not reported",
    "not applicable": "Not applicable",
    "other": "Other",
    "nos": "NOS",
    "proteome": "Proteome",
}

_ACRONYM = re.compile(r"^[A-Z0-9]{2,}$")
_WORD = re.compile(r"[A-Za-zÀ-ÖØ-öø-ÿ]+|[A-Za-zÀ-ÖØ-öø-ÿ]+(?:[-/][A-Za-zÀ-ÖØ-öø-ÿ]+)*")


def format_design_label(design: object) -> str:
    raw = str(design or "—").strip().replace("_", "-")
    if not raw or raw == "—":
        return "—"
    return _DESIGN_LABELS.get(raw.lower(), raw)


def format_metadata_part(part: str) -> str:
    s = str(part or "").strip()
    if not s:
        return ""
    low = s.lower()
    if low in _TOKEN_LABELS:
        return _TOKEN_LABELS[low]
    if _ACRONYM.match(s):
        return s
    if s.isupper() and len(s) <= 6:
        return s
    return _title_preserve(s)


def format_bullet_text(text: str) -> str:
    t = str(text or "").strip()
    if not t:
        return t
    m = re.match(r"^design:\s*(\S+)\s*$", t, re.I)
    if m:
        return f"Design: {format_design_label(m.group(1))}"
    return sentence_cap(t)


def sentence_cap(text: str) -> str:
    s = str(text or "").strip()
    if not s:
        return s
    i = 0
    while i < len(s) and s[i].isspace():
        i += 1
    if i >= len(s):
        return s
    ch = s[i]
    if ch.isalpha():
        return s[:i] + ch.upper() + s[i + 1 :]
    return s


def _title_preserve(text: str) -> str:
    out: list[str] = []
    pos = 0
    for m in _WORD.finditer(text):
        out.append(text[pos : m.start()])
        word = m.group(0)
        if _ACRONYM.match(word) or word.isupper():
            out.append(word)
        elif "/" in word:
            out.append("/".join(format_metadata_part(p) or p for p in word.split("/")))
        elif "-" in word:
            out.append("-".join(format_metadata_part(p) or p for p in word.split("-")))
        else:
            out.append(word[:1].upper() + word[1:].lower() if word else word)
        pos = m.end()
    out.append(text[pos:])
    return "".join(out)
