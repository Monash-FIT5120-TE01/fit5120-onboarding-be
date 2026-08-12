from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLACES_FILE = ROOT / "data" / "places.csv"

ALLOWED_CATEGORIES = {
    "food_venue",
    "museum_gallery",
}

REQUIRED_COLUMNS = {
    "place_cat",
    "place_name",
    "place_address",
    "place_lat",
    "place_lon",
    "place_detailsjson",
    "place_src",
    "place_srcassetid",
}


def clean_text(value: object) -> str:
    return str(value or "").strip()


def load_places() -> list[dict]:
    if not PLACES_FILE.exists():
        raise FileNotFoundError(f"File not found: {PLACES_FILE}")

    with PLACES_FILE.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as file:
        reader = csv.DictReader(file)

        columns = set(reader.fieldnames or [])
        missing_columns = REQUIRED_COLUMNS - columns

        if missing_columns:
            raise ValueError(
                f"Missing columns: {sorted(missing_columns)}"
            )

        rows = list(reader)

    places: list[dict] = []
    source_keys: set[tuple[str, str]] = set()

    for line_number, row in enumerate(rows, start=2):
        category = clean_text(row.get("place_cat"))
        name = clean_text(row.get("place_name"))
        address = clean_text(row.get("place_address")) or None
        source = clean_text(row.get("place_src"))
        source_asset_id = clean_text(row.get("place_srcassetid"))
        details_json = clean_text(row.get("place_detailsjson"))

        if category not in ALLOWED_CATEGORIES:
            raise ValueError(
                f"Line {line_number}: invalid category {category!r}"
            )

        if not name:
            raise ValueError(
                f"Line {line_number}: missing place name"
            )

        if not source or not source_asset_id:
            raise ValueError(
                f"Line {line_number}: missing source information"
            )

        try:
            latitude = float(row["place_lat"])
            longitude = float(row["place_lon"])
        except (KeyError, TypeError, ValueError) as error:
            raise ValueError(
                f"Line {line_number}: invalid coordinates"
            ) from error

        if not -90 <= latitude <= 90:
            raise ValueError(
                f"Line {line_number}: invalid latitude"
            )

        if not -180 <= longitude <= 180:
            raise ValueError(
                f"Line {line_number}: invalid longitude"
            )

        try:
            details = json.loads(details_json)
        except json.JSONDecodeError as error:
            raise ValueError(
                f"Line {line_number}: invalid details JSON"
            ) from error

        if not isinstance(details, dict):
            raise ValueError(
                f"Line {line_number}: details must be an object"
            )

        source_key = (source, source_asset_id)

        if source_key in source_keys:
            raise ValueError(
                f"Line {line_number}: duplicate source key"
            )

        source_keys.add(source_key)

        places.append(
            {
                "place_cat": category,
                "place_name": name,
                "place_address": address,
                "place_lat": latitude,
                "place_lon": longitude,
                "place_detailsjson": json.dumps(
                    details,
                    ensure_ascii=False,
                    separators=(",", ":"),
                ),
                "place_src": source,
                "place_srcassetid": source_asset_id,
                "place_active": True,
            }
        )

    return places


def apply_import(places: list[dict]) -> None:
    try:
        from sqlalchemy.dialects.postgresql import insert
        from sqlmodel import Session, create_engine, select

        from config import Config
        from models.place import Place
    except ImportError as error:
        raise RuntimeError(
            "Project dependencies are not installed"
        ) from error

    engine = create_engine(Config.DATABASE_URL, echo=False)
    imported_at = datetime.now(timezone.utc)

    database_rows = [
        {
            **place,
            "place_importedat": imported_at,
        }
        for place in places
    ]

    with Session(engine) as session:
        existing_rows = session.exec(
            select(
                Place.place_src,
                Place.place_srcassetid,
            )
        ).all()

        existing_keys = {
            (row[0], row[1])
            for row in existing_rows
        }

        incoming_keys = {
            (
                str(row["place_src"]),
                str(row["place_srcassetid"]),
            )
            for row in database_rows
        }

        inserted_count = len(incoming_keys - existing_keys)
        updated_count = len(incoming_keys & existing_keys)

        batch_size = 500

        for start in range(0, len(database_rows), batch_size):
            batch = database_rows[start:start + batch_size]

            statement = insert(Place).values(batch)

            statement = statement.on_conflict_do_update(
                index_elements=[
                    "place_src",
                    "place_srcassetid",
                ],
                set_={
                    "place_cat": statement.excluded.place_cat,
                    "place_name": statement.excluded.place_name,
                    "place_address": statement.excluded.place_address,
                    "place_lat": statement.excluded.place_lat,
                    "place_lon": statement.excluded.place_lon,
                    "place_detailsjson": (
                        statement.excluded.place_detailsjson
                    ),
                    "place_active": True,
                    "place_importedat": imported_at,
                },
            )

            session.exec(statement)

        session.commit()

    print(f"Inserted: {inserted_count}")
    print(f"Updated: {updated_count}")
    print(f"Imported: {len(database_rows)}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Import places.csv into PostgreSQL"
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Write records to the configured database",
    )
    arguments = parser.parse_args()

    places = load_places()
    categories = Counter(
        str(place["place_cat"])
        for place in places
    )

    print(f"Validated records: {len(places)}")
    print(f"Categories: {dict(categories)}")

    if not arguments.apply:
        print("Dry run only: database was not changed")
        print(
            "Use --apply only after checking DATABASE_URL "
            "and creating the place table"
        )
        return

    apply_import(places)


if __name__ == "__main__":
    main()