from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from aging_mrm.grid import assemble_observed
from aging_mrm.paths import DEFAULT_CSV_DIR, DEFAULT_OUT_DIR, SHEET_FILES
from aging_mrm.patients import load_all_patients
from aging_mrm.pointcheck import errors_only, mismatches_only, pointcheck
from aging_mrm.qc import qc_report
from aging_mrm.srm import parse_srm_matrix
from aging_mrm.verify_assembly import to_big_table, verify_assembly


@dataclass
class AgingMrmTables:
    patients: pd.DataFrame
    channels: pd.DataFrame
    peptides: pd.DataFrame
    intensities: pd.DataFrame
    annotation: pd.DataFrame
    long_table: pd.DataFrame
    big: pd.DataFrame
    errors: pd.DataFrame
    mismatches: pd.DataFrame
    assembly_check: dict
    qc: dict

    def write(self, out_dir: Path) -> dict[str, Path]:
        out_dir.mkdir(parents=True, exist_ok=True)
        paths = {
            "patients": out_dir / "patients.csv",
            "channels": out_dir / "channels.csv",
            "peptides": out_dir / "peptides.csv",
            "big": out_dir / "channel_patient_intensity.csv",
            "assembly_check": out_dir / "assembly_check.json",
            "qc": out_dir / "qc_report.json",
        }
        self.patients.to_csv(paths["patients"], index=False, encoding="utf-8-sig")
        self.channels.to_csv(paths["channels"], index=False, encoding="utf-8-sig")
        self.peptides.to_csv(paths["peptides"], index=False, encoding="utf-8-sig")
        self.big.to_csv(paths["big"], index=False, encoding="utf-8-sig")
        paths["assembly_check"].write_text(
            json.dumps(self.assembly_check, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )
        paths["qc"].write_text(
            json.dumps(self.qc, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )
        for stale_name in (
            "values_5000.csv",
            "check_5000_values.csv",
            "annotation_channel_patient_age.csv",
            "intensities.csv",
            "patient_channel_intensity.csv",
            "errors_only.csv",
            "pointcheck_channel_patient_age.csv",
            "pointcheck_mismatches.csv",
        ):
            stale = out_dir / stale_name
            if stale.exists():
                stale.unlink()
        return paths


def build_aging_mrm(
    csv_dir: Path | None = None,
    out_dir: Path | None = None,
    *,
    write: bool = True,
) -> AgingMrmTables:
    csv_dir = Path(csv_dir or DEFAULT_CSV_DIR)
    out_dir = Path(out_dir or DEFAULT_OUT_DIR)
    missing = [csv_dir / name for name in SHEET_FILES.values() if name != "summary.csv"]
    missing = [path for path in missing if not path.is_file()]
    if missing:
        names = ", ".join(path.name for path in missing)
        raise FileNotFoundError(f"CSV not found in {csv_dir}: {names}")

    patients = load_all_patients(csv_dir)
    channels, peptides, intensities = parse_srm_matrix(csv_dir / SHEET_FILES["srm"])
    in_srm = set(channels["patient_id"].astype(str))
    patients = patients.copy()
    patients["in_srm"] = patients["patient_id"].astype(str).isin(in_srm).astype(int)
    annotation = pointcheck(patients, channels, intensities)
    long_table = assemble_observed(patients, channels, intensities)
    big = to_big_table(long_table)
    assembly_check = verify_assembly(
        big,
        channels=channels,
        peptides=peptides,
        intensities=intensities,
        patients=patients,
    )
    fails = mismatches_only(annotation)
    only_errors = errors_only(annotation)
    report = qc_report(
        patients,
        channels,
        peptides,
        intensities,
        long_table,
        annotation=annotation,
        pointcheck=annotation,
    )
    report["assembly_ok"] = assembly_check["ok"]
    report["assembly_n_errors"] = assembly_check["n_errors"]
    report["n_big_rows"] = int(len(big))
    tables = AgingMrmTables(
        patients=patients,
        channels=channels,
        peptides=peptides,
        intensities=intensities,
        annotation=annotation,
        long_table=long_table,
        big=big,
        errors=only_errors,
        mismatches=fails,
        assembly_check=assembly_check,
        qc=report,
    )
    if write:
        tables.write(out_dir)
        report["out_dir"] = str(out_dir)
    return tables
