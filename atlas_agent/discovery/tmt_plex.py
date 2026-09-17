from __future__ import annotations

import re

PLEX_WORDS = {
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
    "eleven": 11,
    "twelve": 12,
    "thirteen": 13,
    "fourteen": 14,
    "fifteen": 15,
    "sixteen": 16,
    "seventeen": 17,
    "eighteen": 18,
}

TMT_PLEX_DIGITS = re.compile(
    r"tmtpro\s*[- ]?(\d{1,2})"
    r"|tmt\s*[- ]?(\d{1,2})\s*[- ]?plex"
    r"|tmt[- ]?based\s+(\d{1,2})\s*[- ]?plex"
    r"|tmt(\d{1,2})\b"
    r"|(\d{1,2})\s*[- ]?plex"
    r"|(\d{1,2})\s*[- ]?channel\s+tmt(?:pro)?"
    r"|tmt(?:pro)?\s+(\d{1,2})\s*[- ]?channel",
    re.I,
)
TMT_PLEX_WORDS = re.compile(
    r"\b(" + "|".join(PLEX_WORDS) + r")\s*[- ]?plex\b"
    r"|\b(" + "|".join(PLEX_WORDS) + r")[- ]channel\s+tmt",
    re.I,
)


def infer_tmt_plex(blob: str) -> int | None:
    text = str(blob or "")
    m = TMT_PLEX_DIGITS.search(text)
    if m:
        for g in m.groups():
            if g:
                n = int(g)
                if 2 <= n <= 18:
                    return n
    m = TMT_PLEX_WORDS.search(text)
    if m:
        word = next((g for g in m.groups() if g), "")
        return PLEX_WORDS.get(word.lower())
    return None
