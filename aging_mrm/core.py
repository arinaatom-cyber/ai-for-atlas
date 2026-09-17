"""Ten fully covered core peptides: the designed 10 × 500 = 5000 values."""

from __future__ import annotations

from typing import Any

CORE10_PEPTIDES = (
    "DSTYSLSSTLTLSK",  # IGKC
    "GPSVFPLAPSSK",  # IGHG1
    "AIGYLNTGYQR",  # A2MG
    "ATEHLSTLSEK",  # APOA1
    "GSESGIFTNTK",  # FIBA
    "FDPSLTQR",  # A2AP
    "TPLTATLSK",  # IGHA1
    "YAATSQVLLPSK",  # IGHM
    "YEASILTHDSSIR",  # FIBG
    "NFPSPVDAAFR",  # HEMO
)


def core_sequences(peptides: Any) -> list[str]:
    """Use all CORE10 if present; otherwise the overlap (tests / partial files)."""
    if peptides is None or getattr(peptides, "empty", True):
        return list(CORE10_PEPTIDES)
    have = set(peptides["peptide_sequence"].astype(str))
    found = [seq for seq in CORE10_PEPTIDES if seq in have]
    if found:
        return found
    return list(dict.fromkeys(peptides["peptide_sequence"].astype(str).tolist()))
