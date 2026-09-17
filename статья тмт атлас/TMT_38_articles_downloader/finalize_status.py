#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Finalize: sync metadata with disk, write Russian status report."""

from __future__ import annotations

import csv
from pathlib import Path

BASE = Path(__file__).resolve().parent
OUTPUT = BASE / "TMT_articles"
PDF_DIR = OUTPUT / "PDF"
METADATA = OUTPUT / "metadata.csv"
STATUS = OUTPUT / "STATUS_RU.txt"
MIN_SIZE = 200_000


def is_valid_pdf(path: Path) -> bool:
    try:
        return path.exists() and path.stat().st_size >= MIN_SIZE and path.read_bytes()[:4] == b"%PDF"
    except OSError:
        return False


def main() -> None:
    with METADATA.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))

    downloaded = []
    missing = []

    for row in rows:
        index = int(row["№"])
        prefix = f"{index:02d}_"
        match = None
        for pdf in PDF_DIR.glob("*.pdf"):
            if pdf.name.startswith(prefix) and is_valid_pdf(pdf):
                match = pdf
                break
        if match:
            row["PDF status"] = "downloaded"
            row["Local PDF"] = str(match)
            downloaded.append(row)
        else:
            row["PDF status"] = "not downloaded"
            row["PDF source"] = ""
            row["PDF URL"] = ""
            row["Local PDF"] = ""
            missing.append(row)

    with METADATA.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    unresolved = OUTPUT / "unresolved.csv"
    with unresolved.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["№", "DOI", "Title", "DOI link", "Europe PMC", "PMCID", "Причина"],
        )
        writer.writeheader()
        for row in missing:
            writer.writerow({
                "№": row["№"],
                "DOI": row["DOI"],
                "Title": row["Title"],
                "DOI link": row["DOI link"],
                "Europe PMC": row.get("Europe PMC", ""),
                "PMCID": row.get("PMCID", ""),
                "Причина": "Закрытый доступ или блокировка автоматической загрузки",
            })

    lines = [
        "СТАТУС ЗАГРУЗКИ СТАТЕЙ TMT",
        "=" * 40,
        f"Скачано полных PDF: {len(downloaded)} из {len(rows)}",
        f"Папка с PDF: {PDF_DIR}",
        "",
        "УСПЕШНО СКАЧАНО:",
    ]
    for row in downloaded:
        lines.append(f"  [{row['№']}] {row['Title'][:90]}")

    lines.extend(["", "НЕ СКАЧАНО АВТОМАТИЧЕСКИ:", ""])
    for row in missing:
        lines.append(f"  [{row['№']}] {row['DOI']}")
        lines.append(f"       {row['Title'][:100]}")
        if row.get("PMCID"):
            lines.append(f"       PMC: https://pmc.ncbi.nlm.nih.gov/articles/{row['PMCID']}/")
        lines.append(f"       DOI: {row['DOI link']}")
        lines.append("")

    lines.extend([
        "КАК ДОСКАЧАТЬ ОСТАЛЬНЫЕ БЫСТРО:",
        "1. Откройте all_38_articles_links.html в браузере (двойной клик).",
        "2. Подключите VPN/прокси университета или библиотеки.",
        "3. Для статей с PMCID откройте PMC-ссылку и нажмите Download PDF.",
        "4. Для Cell/Nature/ACS — откройте DOI через подписку института.",
        "5. Сохраняйте файлы в TMT_articles/PDF с номером в начале имени, например:",
        "   18_2020_Proteogenomic Landscape of Breast Cancer....pdf",
        "",
        "Повторный автозапуск всех этапов:",
        "   RUN_ALL_DOWNLOADS.bat",
    ])

    STATUS.write_text("\n".join(lines), encoding="utf-8")
    print(f"Downloaded: {len(downloaded)}/{len(rows)}")
    print(f"Status: {STATUS}")


if __name__ == "__main__":
    main()
