#!/usr/bin/env python3
"""Rename PDFs to PMID_*.pdf or DOI_*.pdf based on DOI sniffing + metadata.csv."""

from __future__ import annotations

import csv
import os
import re
import shutil
from pathlib import Path

import fitz

BASE = Path(__file__).resolve().parent
PDF_DIR = BASE / "TMT_articles" / "PDF"
META_CSV = BASE / "TMT_articles" / "metadata.csv"
DOI_LIST = BASE / "doi_list.txt"
DUP_DIR = PDF_DIR / "_duplicates"
UNMATCHED_DIR = PDF_DIR / "_unmatched"
MAP_CSV = BASE / "TMT_articles" / "pdf_rename_map.csv"


def load_metadata() -> dict[str, dict]:
    meta: dict[str, dict] = {}
    with META_CSV.open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            meta[row["DOI"]] = row
    return meta


def load_dois() -> list[str]:
    return [line.strip() for line in DOI_LIST.read_text(encoding="utf-8").splitlines() if line.strip()]


def sniff_doi(path: Path, dois: list[str]) -> list[str]:
    doc = fitz.open(path)
    text = "".join(doc.load_page(i).get_text() for i in range(min(8, doc.page_count)))
    doc.close()
    text = re.sub(r"\s+", " ", text)

    found: list[str] = []
    for doi in dois:
        if doi in text or doi.replace("/", "") in text.replace("/", ""):
            found.append(doi)

    if not found:
        for match in re.finditer(r"10\.\d{4,9}/[A-Za-z0-9._();:+/-]+", text):
            cand = match.group(0).rstrip(".,;)")
            for doi in dois:
                if cand == doi or cand in doi or doi in cand:
                    found.append(doi)

    return list(dict.fromkeys(found))


def target_name(doi: str, meta: dict[str, dict]) -> str:
    row = meta.get(doi, {})
    pmid = (row.get("PMID") or "").strip()
    if pmid:
        return f"PMID_{pmid}.pdf"
    safe = doi.replace("/", "_")
    return f"DOI_{safe}.pdf"


def main() -> None:
    meta = load_metadata()
    dois = load_dois()
    DUP_DIR.mkdir(exist_ok=True)
    UNMATCHED_DIR.mkdir(exist_ok=True)

    assignments: list[tuple[Path, str, str]] = []
    manual_map = {
        "08_2019_A Review on Quantitative Multiplexed Proteomics.pdf": "10.1002/cbic.201800650",
        "A Review on Quantitative Multiplexed Proteomics.pdf": "10.1002/cbic.201800650",
    }

    for path in sorted(PDF_DIR.glob("*.pdf")):
        if path.parent.name in {"_duplicates", "_unmatched"}:
            continue

        matched = sniff_doi(path, dois)
        if not matched and path.name in manual_map:
            matched = [manual_map[path.name]]

        if not matched:
            dest = UNMATCHED_DIR / path.name
            if path.resolve() != dest.resolve():
                shutil.move(str(path), str(dest))
            assignments.append((path, "", f"UNMATCHED -> {dest.name}"))
            continue

        if len(matched) > 1:
            # Prefer DOI from metadata list order (lower index = higher priority in doi_list)
            idx = {d: i for i, d in enumerate(dois)}
            matched.sort(key=lambda d: idx.get(d, 999))
        doi = matched[0]
        assignments.append((path, doi, target_name(doi, meta)))

    # Resolve duplicates: keep largest file per target name
    by_target: dict[str, list[tuple[Path, int]]] = {}
    for path, doi, name in assignments:
        if not doi:
            continue
        by_target.setdefault(name, []).append((path, path.stat().st_size))

    renames: list[tuple[str, str, str]] = []
    for name, items in by_target.items():
        items.sort(key=lambda x: x[1], reverse=True)
        keep_path = items[0][0]
        target = PDF_DIR / name
        renames.append((keep_path.name, name, keep_path.stat().st_size))

        for dup_path, dup_size in items[1:]:
            dup_dest = DUP_DIR / dup_path.name
            if dup_path.resolve() != dup_dest.resolve():
                shutil.move(str(dup_path), str(dup_dest))
            renames.append((dup_path.name, f"_duplicates/{dup_path.name}", dup_size))

        if keep_path.resolve() != target.resolve():
            if target.exists():
                alt = DUP_DIR / f"{keep_path.stem}__conflict__{name}"
                shutil.move(str(target), str(alt))
            shutil.move(str(keep_path), str(target))

    with MAP_CSV.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["old_name", "new_name", "doi", "bytes"])
        for path, doi, name in assignments:
            if doi:
                size = path.stat().st_size if path.exists() else ""
                w.writerow([path.name, name, doi, size])

    print(f"Renamed/mapped: {len(by_target)} unique articles")
    print(f"Duplicates moved to: {DUP_DIR}")
    print(f"Unmatched moved to: {UNMATCHED_DIR}")
    print(f"Map saved: {MAP_CSV}")
    print()
    for name in sorted(by_target):
        print(name)


if __name__ == "__main__":
    main()
