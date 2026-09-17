from __future__ import annotations

from typing import Any

CORE10_PEPTIDES = (
    "DSTYSLSSTLTLSK",
    "GPSVFPLAPSSK",
    "AIGYLNTGYQR",
    "ATEHLSTLSEK",
    "GSESGIFTNTK",
    "FDPSLTQR",
    "TPLTATLSK",
    "YAATSQVLLPSK",
    "YEASILTHDSSIR",
    "NFPSPVDAAFR",
)


def core_sequences(peptides: Any) -> list[str]:
    if peptides is None or getattr(peptides, "empty", True):
        return list(CORE10_PEPTIDES)
    have = set(peptides["peptide_sequence"].astype(str))
    found = [seq for seq in CORE10_PEPTIDES if seq in have]
    if found:
        return found
    return list(dict.fromkeys(peptides["peptide_sequence"].astype(str).tolist()))
