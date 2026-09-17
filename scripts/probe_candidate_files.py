#!/usr/bin/env python3
import json
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]


def pride_files(pxd: str) -> dict:
    r = requests.get(
        f"https://www.ebi.ac.uk/pride/ws/archive/v2/projects/{pxd}/files",
        timeout=45,
    )
    if r.status_code != 200:
        return {"error": r.status_code}
    data = r.json()
    files = data if isinstance(data, list) else data.get("_embedded", {}).get("files", [])
    exts: dict[str, int] = {}
    for f in files:
        fn = (f.get("fileName") or f.get("name") or "").lower()
        for ext in (".tsv", ".txt", ".csv", ".xlsx", ".mztab"):
            if fn.endswith(ext):
                exts[ext] = exts.get(ext, 0) + 1
    return {
        "n_files": len(files),
        "table_exts": exts,
        "has_quant_table": bool(exts),
        "sample": [(f.get("fileName") or "")[:55] for f in files[:4]],
    }


def pdc_study(pdc: str) -> dict:
    q = (
        '{ filesPerStudy(pdc_study_id: "'
        + pdc
        + '", offset: 0, limit: 500) { file_name data_category file_type } }'
    )
    r = requests.post("https://pdc.cancer.gov/graphql", json={"query": q}, timeout=45)
    if r.status_code != 200:
        return {"error": r.status_code}
    rows = (r.json().get("data") or {}).get("filesPerStudy") or []
    files = [f for f in rows if f.get("file_name")]
    qf = [
        f
        for f in files
        if any(
            x in (f.get("file_name") or "").lower()
            for x in (".tsv", ".txt", ".csv", "protein", "quant", "abundance")
        )
    ]
    return {
        "n_files": len(files),
        "quant_like": len(qf),
        "has_quant_table": bool(qf),
        "sample": [(f.get("file_name") or "")[:55] for f in qf[:4]],
    }


def main() -> None:
    d = json.loads((ROOT / "data/discovery_history/latest.json").read_text(encoding="utf-8"))
    cands = d.get("candidates") or []
    pride = [x for x in cands if (x.get("accession") or "").upper().startswith("PXD")]
    pdc = [x for x in cands if (x.get("accession") or "").upper().startswith("PDC")]
    print(f"candidates={len(cands)} PRIDE={len(pride)} PDC={len(pdc)}")
    for x in pride[:3]:
        acc = x["accession"]
        print(f"PRIDE {acc}:", pride_files(acc))
    for x in pdc[:3]:
        acc = x["accession"]
        print(f"PDC {acc}:", pdc_study(acc))


if __name__ == "__main__":
    main()
