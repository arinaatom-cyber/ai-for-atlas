from __future__ import annotations

import argparse
from pathlib import Path

from aging_mrm.paths import DEFAULT_CSV_DIR, DEFAULT_OUT_DIR
from aging_mrm.pipeline import build_aging_mrm


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Точечная проверка: пациент, канал, возраст, интенсивность."
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    build = sub.add_parser("build", help="Прочитать CSV и записать tidy-таблицы")
    build.add_argument("--csv-dir", type=Path, default=DEFAULT_CSV_DIR)
    build.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    build.add_argument("--no-write", action="store_true")

    args = parser.parse_args(argv)
    if args.cmd == "build":
        tables = build_aging_mrm(
            csv_dir=args.csv_dir,
            out_dir=args.out_dir,
            write=not args.no_write,
        )
        qc = tables.qc
        print(f"patients: {qc['n_patients']}")
        print(f"channels: {qc['n_channels']}")
        print(f"peptides: {qc['n_peptides']}")
        print(f"big CSV: {qc.get('n_big_rows')} rows  (channel, patient, peptide, intensity)")
        print(f"assembly: {'OK' if qc.get('assembly_ok') else 'ERRORS ' + str(qc.get('assembly_n_errors'))}")
        print(f"age bins: {qc['n_patients_by_age_bin']}")
        if not args.no_write:
            print(f"wrote: {Path(args.out_dir) / 'channel_patient_intensity.csv'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
