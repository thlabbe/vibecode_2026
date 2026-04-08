import argparse
import csv
from pathlib import Path
from typing import List

import pdfplumber


def clean_cell(value: object) -> str:
    """Normalize a table cell value for CSV export."""
    if value is None:
        return ""
    text = str(value).replace("\r", " ").replace("\n", " ").strip()
    return " ".join(text.split())


def normalize_rows(rows: List[List[object]]) -> List[List[str]]:
    """Ensure all rows have the same number of columns and remove empty rows."""
    if not rows:
        return []

    max_cols = max((len(row) for row in rows if row), default=0)
    normalized: List[List[str]] = []

    for row in rows:
        if row is None:
            continue
        cleaned = [clean_cell(cell) for cell in row]
        if max_cols and len(cleaned) < max_cols:
            cleaned.extend([""] * (max_cols - len(cleaned)))
        if any(cell != "" for cell in cleaned):
            normalized.append(cleaned)

    return normalized


def extract_tables(pdf_path: Path) -> List[dict]:
    """Extract tables from all PDF pages using pdfplumber."""
    extracted = []

    with pdfplumber.open(pdf_path) as pdf:
        for page_index, page in enumerate(pdf.pages, start=1):
            tables = page.extract_tables()
            for table_index, table in enumerate(tables, start=1):
                rows = normalize_rows(table)
                if rows:
                    extracted.append(
                        {
                            "page": page_index,
                            "table": table_index,
                            "rows": rows,
                        }
                    )

    return extracted


def write_single_csv(tables: List[dict], output_csv: Path, delimiter: str) -> None:
    """Write all extracted tables into a single CSV file with metadata columns."""
    max_cols = max((len(row) for t in tables for row in t["rows"]), default=0)

    output_csv.parent.mkdir(parents=True, exist_ok=True)
    with output_csv.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f, delimiter=delimiter)
        writer.writerow(["page", "table", "row_in_table"] + [f"col_{i}" for i in range(1, max_cols + 1)])

        for table in tables:
            for row_idx, row in enumerate(table["rows"], start=1):
                padded = row + [""] * (max_cols - len(row))
                writer.writerow([table["page"], table["table"], row_idx] + padded)


def write_one_csv_per_table(tables: List[dict], output_dir: Path, delimiter: str) -> None:
    """Write each extracted table to its own CSV file."""
    output_dir.mkdir(parents=True, exist_ok=True)

    for t in tables:
        file_name = f"page_{t['page']:03d}_table_{t['table']:02d}.csv"
        csv_path = output_dir / file_name

        max_cols = max((len(row) for row in t["rows"]), default=0)
        with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f, delimiter=delimiter)
            writer.writerow([f"col_{i}" for i in range(1, max_cols + 1)])
            for row in t["rows"]:
                writer.writerow(row + [""] * (max_cols - len(row)))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extract tables from a PDF file and export them to CSV."
    )
    parser.add_argument("pdf", type=Path, help="Input PDF file")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=Path("output.csv"),
        help="Output CSV file (single mode) or output folder (split mode)",
    )
    parser.add_argument(
        "--split",
        action="store_true",
        help="Export one CSV per table instead of a single CSV",
    )
    parser.add_argument(
        "--delimiter",
        default=";",
        help="CSV delimiter (default: ';')",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if not args.pdf.exists():
        raise FileNotFoundError(f"PDF file not found: {args.pdf}")

    tables = extract_tables(args.pdf)
    if not tables:
        print("No tables detected in the PDF.")
        return

    if args.split:
        write_one_csv_per_table(tables, args.output, args.delimiter)
        print(f"Done: {len(tables)} table(s) exported to folder '{args.output}'.")
    else:
        write_single_csv(tables, args.output, args.delimiter)
        print(f"Done: {len(tables)} table(s) exported to '{args.output}'.")


if __name__ == "__main__":
    main()
