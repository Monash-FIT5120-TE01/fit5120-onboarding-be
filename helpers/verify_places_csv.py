import csv
import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLACES_FILE = ROOT / "data" / "places.csv"


def main() -> None:
    with PLACES_FILE.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as file:
        rows = list(csv.DictReader(file))

    errors: list[str] = []
    categories = Counter()
    source_ids: set[str] = set()
    logical_places: set[tuple] = set()

    for line_number, row in enumerate(rows, start=2):
        category = (row.get("place_cat") or "").strip()
        name = (row.get("place_name") or "").strip()
        address = (row.get("place_address") or "").strip()
        source_id = (row.get("place_srcassetid") or "").strip()

        categories[category] += 1

        if category not in {"food_venue", "museum_gallery"}:
            errors.append(
                f"Line {line_number}: invalid category {category!r}"
            )

        if not name:
            errors.append(f"Line {line_number}: missing name")

        try:
            latitude = float(row["place_lat"])
            longitude = float(row["place_lon"])

            if not -90 <= latitude <= 90:
                errors.append(
                    f"Line {line_number}: invalid latitude {latitude}"
                )

            if not -180 <= longitude <= 180:
                errors.append(
                    f"Line {line_number}: invalid longitude {longitude}"
                )

        except (KeyError, TypeError, ValueError):
            errors.append(f"Line {line_number}: invalid coordinates")
            continue

        if not source_id:
            errors.append(f"Line {line_number}: missing source ID")
        elif source_id in source_ids:
            errors.append(
                f"Line {line_number}: duplicate source ID {source_id}"
            )
        else:
            source_ids.add(source_id)

        logical_key = (
                category,
                name.casefold(),
                address.casefold(),
                round(latitude, 6),
                round(longitude, 6),
            )

        if logical_key in logical_places:
            errors.append(
                f"Line {line_number}: duplicate place {name}"
            )
        else:
            logical_places.add(logical_key)

        try:
            details = json.loads(row["place_detailsjson"])

            if not isinstance(details, dict):
                errors.append(
                    f"Line {line_number}: details JSON is not an object"
                )

        except (KeyError, TypeError, json.JSONDecodeError):
            errors.append(
                f"Line {line_number}: invalid details JSON"
            )

    print(f"Total rows: {len(rows)}")
    print(f"Categories: {dict(categories)}")
    print(f"Unique source IDs: {len(source_ids)}")
    print(f"Validation errors: {len(errors)}")

    if errors:
        print()
        print("First 20 errors:")

        for error in errors[:20]:
            print(error)

        raise SystemExit(1)

    print("Validation passed")


if __name__ == "__main__":
    main()