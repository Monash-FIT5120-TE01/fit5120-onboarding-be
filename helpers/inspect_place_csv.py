import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

FILES = [
    ROOT / "data" / "raw_places" / "cafes.csv",
    ROOT / "data" / "raw_places" / "landmarks.csv",
]


for path in FILES:
    print()
    print("=" * 60)
    print("File:", path)

    if not path.exists():
        print("ERROR: file does not exist")
        continue

    with path.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        rows = list(reader)

    print("Row count:", len(rows))
    print("Columns:", reader.fieldnames)

    if rows:
        print("First row:")
        for key, value in rows[0].items():
            print(f"  {key}: {value}")