from __future__ import annotations

import re

GARBAGE_SUMMARY = re.compile(
    r"json\s*schema|this\s+json\s+schema|reply\s+with\s+only\s+valid\s+json|"
    r"return\s+a\s+json\s+object|this\s+(paper|abstract|json\s+schema|description)\s+describes|"
    r"fits?\s+the\s+human\s+tmt/isobaric",
    re.I,
)

_RU_GLOSS = (
    (re.compile(r"\bпейсаж\b", re.I), "абстракт"),
    (re.compile(r"\bпейдж\b", re.I), "статья"),
    (re.compile(r"\bпэйдж\b", re.I), "статья"),
    (re.compile(r"\bпейс\b", re.I), "статья"),
    (re.compile(r"\bпейсинг\b", re.I), "анализ"),
    (re.compile(r"\bэтот\s+пакет\s+данных\b", re.I), "эта статья"),
    (re.compile(r"\bпакет\s+данных\b", re.I), "статья"),
    (re.compile(r"\bthis\s+page\b", re.I), "This article"),
    (re.compile(r"\bthe\s+page\b", re.I), "The article"),
)
_FFPE_MISREAD = re.compile(
    r"ffpe.*(?:не\s+включает|не\s+содержит).*(?:ткань|опухол)",
    re.I | re.S,
)
_FFPE_MISREAD_FIX = (
    "FFPE ткани опухоли допустимы для атласа; нужна ручная проверка protein table и дизайна."
)


def fix_ru_llm_gloss(text: str) -> str:
    s = str(text or "").strip()
    if not s:
        return s
    for pat, repl in _RU_GLOSS:
        s = pat.sub(repl, s)
    if _FFPE_MISREAD.search(s):
        s = re.sub(
            r"Этот абстракт не полностью соответствует атласу, так как он сосредоточен на анализе FFPE образцов, "
            r"что не включает в себя ткань или клетки опухоли\.",
            _FFPE_MISREAD_FIX,
            s,
            flags=re.I,
        )
    return s


def sanitize_summary(text: object) -> str:
    s = str(text or "").strip()
    if not s or GARBAGE_SUMMARY.search(s):
        return ""
    s = fix_ru_llm_gloss(s)
    return s[:320]
