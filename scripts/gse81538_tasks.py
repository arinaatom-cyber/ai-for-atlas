from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

CSV_PATH = Path(
    r"C:\Users\Arina1996\Desktop\GSE81538_gene_expression_405_transformed.csv"
) / "GSE81538_gene_expression_405_transformed.csv"


def setup_console() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass


def load_table(path: Path) -> pd.DataFrame:
    if not path.is_file():
        raise FileNotFoundError(f"Файл не найден: {path}")

    df = pd.read_csv(path, index_col=0)
    df.index = df.index.astype(str)
    return df.select_dtypes(include="number")


def main() -> None:
    setup_console()

    df = load_table(CSV_PATH)

    print(f"Размер таблицы: {df.shape[0]} строк x {df.shape[1]} столбцов")

    genes = ["TP53", "MDM2", "BRCA1"]
    missing = [gene for gene in genes if gene not in df.index]
    if missing:
        raise ValueError(f"В таблице не найдены строки: {missing}")
    print(f"Найденные строки: {', '.join(genes)}")

    row_avg = df.loc[genes].to_numpy().mean()
    col_indices = [4, 99, 199]
    if max(col_indices) >= df.shape[1]:
        raise IndexError("В таблице недостаточно столбцов для задания 1")
    col_avg = df.iloc[:, col_indices].to_numpy().mean()
    answer1 = round(row_avg - col_avg, 2)

    answer2 = round(df.max(axis=0).mean(), 2)

    mask = df.index.str.contains("AB", regex=False) & ~df.index.str.contains(
        "C", regex=False
    )
    ab_rows = df.loc[mask]
    row_means = ab_rows.mean(axis=1)
    answer3 = round((row_means**2).median(), 2)

    print(f'Строк с "AB", но без "C": {len(ab_rows)}')
    print()
    print(f"Ответ 1: {answer1:.2f}")
    print(f"Ответ 2: {answer2:.2f}")
    print(f"Ответ 3: {answer3:.2f}")


if __name__ == "__main__":
    main()
