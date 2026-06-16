from pathlib import Path
import csv
import sys

base_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(base_dir.parent))
from solution.pipeline import OUTPUT_FIELDS, run


def write_results(rows, output_path: Path) -> None:
    with output_path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=OUTPUT_FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def main() -> None:
    base_dir = Path(__file__).resolve().parent
    csv_path = base_dir.parent / "data" / "companies.csv"
    json_path = base_dir.parent / "mocks" / "enrichment_responses.json"
    output_path = base_dir.parent / "output" / "results.csv"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    rows = run(csv_path, json_path)
    write_results(rows, output_path)

    print(f"Wrote {len(rows)} rows to {output_path}")
    first_rows = rows[:10]
    for row in first_rows:
        print(row)

    summary = {
        "total_rows_processed": len(rows),
        "VERIFIED": sum(1 for row in rows if row["state"] == "VERIFIED"),
        "LOW_CONFIDENCE": sum(1 for row in rows if row["state"] == "LOW_CONFIDENCE"),
        "NOT_FOUND": sum(1 for row in rows if row["state"] == "NOT_FOUND"),
        "CONFLICTING": sum(1 for row in rows if row["state"] == "CONFLICTING"),
    }
    print("Summary:")
    for key, value in summary.items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    main()
