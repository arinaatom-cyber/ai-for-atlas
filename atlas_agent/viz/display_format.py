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

_JUNK_TAXONOMY = frozenset(
    {
        "other",
        "others",
        "not reported",
        "not applicable",
        "n/a",
        "na",
        "n.a.",
        "unknown",
        "unspecified",
        "unspecified site",
        "not specified",
        "not available",
        "none",
        "nos",
        "proteome",
        "phosphoproteome",
        "nan",
        "null",
        "missing",
    }
)

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
    for i, ch in enumerate(s):
        if ch.isalpha():
            if ch.islower():
                return s[:i] + ch.upper() + s[i + 1 :]
            return s
    return s


def format_title(text: str) -> str:
    """Table title — capitalize first letter (keep original casing elsewhere, e.g. TMT)."""
    return sentence_cap(str(text or "").strip())


_DISEASE_TERMS: list[tuple[str, str]] = [
    ("acute myeloid leukemia", "Acute myeloid leukemia"),
    ("acute lymphoblastic leukemia", "Acute lymphoblastic leukemia"),
    ("colorectal cancer", "Colorectal cancer"),
    ("pancreatic cancer", "Pancreatic cancer"),
    ("glioblastoma", "Glioblastoma"),
    ("glioma", "Glioma"),
    ("breast cancer", "Breast cancer"),
    ("lung cancer", "Lung cancer"),
    ("ovarian cancer", "Ovarian cancer"),
    ("prostate cancer", "Prostate cancer"),
    ("hepatocellular carcinoma", "Hepatocellular carcinoma"),
    ("gastric cancer", "Gastric cancer"),
    ("melanoma", "Melanoma"),
    ("lymphoma", "Lymphoma"),
    ("leukemia", "Leukemia"),
    ("sarcoma", "Sarcoma"),
    ("cervical cancer", "Cervical cancer"),
    ("renal cell carcinoma", "Renal cell carcinoma"),
    ("bladder cancer", "Bladder cancer"),
    ("multiple myeloma", "Multiple myeloma"),
    ("neuroblastoma", "Neuroblastoma"),
    ("medulloblastoma", "Medulloblastoma"),
    ("gallbladder cancer", "Gallbladder cancer"),
    ("endometrial cancer", "Endometrial cancer"),
    ("head and neck cancer", "Head and neck cancer"),
    ("hiv", "HIV"),
    ("diabetes", "Diabetes"),
    ("alzheimer", "Alzheimer disease"),
    ("parkinson", "Parkinson disease"),
]

_ORGAN_TERMS: list[tuple[str, str]] = [
    ("bone marrow", "Bone marrow"),
    ("lymph node", "Lymph node"),
    ("small intestine", "Small intestine"),
    ("large intestine", "Large intestine"),
    ("colorectal", "Colorectal"),
    ("pancreas", "Pancreas"),
    ("pancreatic", "Pancreatic"),
    ("glioblastoma", "Brain"),
    ("glioma", "Brain"),
    ("brain", "Brain"),
    ("liver", "Liver"),
    ("kidney", "Kidney"),
    ("lung", "Lung"),
    ("breast", "Breast"),
    ("colon", "Colon"),
    ("skin", "Skin"),
    ("blood", "Blood"),
    ("plasma", "Plasma"),
    ("serum", "Serum"),
    ("heart", "Heart"),
    ("muscle", "Muscle"),
    ("ovary", "Ovary"),
    ("prostate", "Prostate"),
    ("stomach", "Stomach"),
    ("gallbladder", "Gallbladder"),
    ("melanoma", "Skin"),
]


def _item_text_blob(item: dict) -> str:
    ai = item.get("abstract_ai") or {}
    parts = [
        item.get("title"),
        item.get("description"),
        item.get("abstract"),
        item.get("abstract_snippet"),
        item.get("sample_processing_protocol"),
        ai.get("summary_en"),
        ai.get("disease"),
        ai.get("organ"),
    ]
    return " ".join(str(p or "") for p in parts).lower()


def _match_taxonomy_terms(blob: str, terms: list[tuple[str, str]], profile_terms: list[str] | None) -> list[str]:
    hits: list[str] = []
    seen: set[str] = set()
    for needle, label in terms:
        if needle in blob and label.lower() not in seen:
            hits.append(label)
            seen.add(label.lower())
    for raw in profile_terms or []:
        term = str(raw or "").strip()
        if len(term) < 4 or term.lower() in ("healthy", "other", "nan", "not reported"):
            continue
        low = term.lower()
        if low in blob and low not in seen:
            hits.append(format_metadata_part(term) or term)
            seen.add(low)
    return hits


def _is_junk_taxonomy(token: str) -> bool:
    t = re.sub(r"\s+", " ", str(token or "").strip().lower()).strip(" .,-")
    if not t or t in _JUNK_TAXONOMY:
        return True
    if t.endswith(" proteome") and _is_junk_taxonomy(t[: -len(" proteome")]):
        return True
    return False


def clean_taxonomy_value(raw: object) -> str:
    """Drop PDC placeholders (Other, Not reported, Proteome) from disease/organ strings."""
    text = str(raw or "").strip()
    if not text:
        return ""
    parts: list[str] = []
    seen: set[str] = set()
    for chunk in re.split(r"[;|]|·", text):
        for piece in chunk.split(","):
            token = re.sub(r"\s+", " ", piece).strip(" .")
            if not token or _is_junk_taxonomy(token):
                continue
            key = token.lower()
            if key in seen:
                continue
            seen.add(key)
            parts.append(format_metadata_part(token) or token)
    return "; ".join(parts[:4])


def is_stub_description(text: str) -> bool:
    """True for short metadata stubs like «Other · Proteome», not real abstracts."""
    s = re.sub(r"\s+", " ", str(text or "").strip())
    if not s or s.lower() in ("nan", "none", "—"):
        return True
    if len(s) >= 80:
        return False
    return not clean_taxonomy_value(s)


def infer_disease(item: dict, *, profile: dict | None = None) -> str:
    explicit = clean_taxonomy_value(item.get("disease"))
    if explicit:
        return explicit
    ai = item.get("abstract_ai") or {}
    explicit = clean_taxonomy_value(ai.get("disease"))
    if explicit:
        return explicit
    blob = _item_text_blob(item)
    if not blob:
        return ""
    profile_d = (profile or {}).get("top_diseases") or []
    hits = _match_taxonomy_terms(blob, _DISEASE_TERMS, profile_d)
    return "; ".join(hits[:3])


def infer_organ(item: dict, *, profile: dict | None = None) -> str:
    for key in ("primary_site", "organ", "tissue"):
        cleaned = clean_taxonomy_value(item.get(key))
        if cleaned:
            return cleaned
    ai = item.get("abstract_ai") or {}
    for key in ("organ", "material"):
        val = str(ai.get(key) or "").strip()
        if val.lower() in ("unclear", "unknown", "—"):
            continue
        cleaned = clean_taxonomy_value(val)
        if cleaned:
            return cleaned
        if val and not _is_junk_taxonomy(val):
            return format_metadata_part(val) or val
    blob = _item_text_blob(item)
    if not blob:
        return ""
    profile_o = (profile or {}).get("top_organs") or []
    hits = _match_taxonomy_terms(blob, _ORGAN_TERMS, profile_o)
    return "; ".join(hits[:3])


def disease_filter_slug(disease: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", str(disease or "").lower()).strip("-")
    return slug[:48]


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
