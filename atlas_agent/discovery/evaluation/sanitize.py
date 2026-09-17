"""Text sanitization for summaries — shared by evaluation and legacy pipeline."""
from __future__ import annotations

import re

GARBAGE_SUMMARY = re.compile(
    r"json\s*schema|this\s+json\s+schema|reply\s+with\s+only\s+valid\s+json|"
    r"return\s+a\s+json\s+object|this\s+(paper|abstract|json\s+schema|description)\s+describes|"
    r"fits?\s+the\s+human\s+tmt/isobaric",
    re.I,
)


def sanitize_summary(text: object) -> str:
    s = str(text or "").strip()
    if not s or GARBAGE_SUMMARY.search(s):
        return ""
    return s[:320]
