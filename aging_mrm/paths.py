"""Default locations for the aging MRM-SIS workbook and CSV export."""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

DEFAULT_XLSX = Path(r"C:\Users\Arina1996\Desktop\MRM_SIS_Summary_28072026.xlsx")
DEFAULT_CSV_DIR = Path(r"C:\Users\Arina1996\Desktop\MRM_SIS_Summary_28072026_csv")
DEFAULT_OUT_DIR = Path(r"C:\Users\Arina1996\Desktop\MRM_SIS_Summary_28072026_csv\tidy")

SHEET_FILES = {
    "patients_100": "100 samples 2024.csv",
    "patients_50": "50 samples 2025.csv",
    "patients_350": "350 samples 2025.csv",
    "srm": "SRM data.csv",
    "summary": "summary.csv",
}

COHORT_100 = "100_2024"
COHORT_50 = "50_2025"
COHORT_350 = "350_2025"
