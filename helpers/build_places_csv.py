import csv
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

CAFE_FILE = ROOT / "data" / "raw_places" / "cafes.csv"
LANDMARK_FILE = ROOT / "data" / "raw_places" / "landmarks.csv"
OUTPUT_FILE = ROOT / "data" / "places.csv"

OUTPUT_FIELDS = [
    "place_cat",
    "place_name",
    "place_address",
    "place_lat",
    "place_lon",
    "place_detailsjson",
    "place_src",
    "place_srcassetid",
]


def clean_text(value: object) -> str:
    return str(value or "").strip()


def parse_int(value: object) -> int:
    try:
        return int(float(clean_text(value)))
    except ValueError:
        return 0


def parse_float(value: object) -> float | None:
    try:
        return float(clean_text(value))
    except ValueError:
        return None


def read_csv(path: Path) -> list[dict]:
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    with path.open("r", encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def make_hash(*values: object) -> str:
    text = "|".join(clean_text(value).casefold() for value in values)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def build_food_venues(rows: list[dict]) -> tuple[list[dict], int, int]:
    years = [
        parse_int(row.get("Census year"))
        for row in rows
        if clean_text(row.get("Census year"))
    ]

    latest_year = max(years)

    latest_rows = [
        row
        for row in rows
        if parse_int(row.get("Census year")) == latest_year
    ]

    grouped: dict[tuple, dict] = {}
    skipped = 0

    for row in latest_rows:
        name = clean_text(row.get("Trading name"))
        address = (
            clean_text(row.get("Business address"))
            or clean_text(row.get("Building address"))
        )
        property_id = clean_text(row.get("Property ID"))

        latitude = parse_float(row.get("Latitude"))
        longitude = parse_float(row.get("Longitude"))

        if not name or latitude is None or longitude is None:
            skipped += 1
            continue

        if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
            skipped += 1
            continue

        group_key = (
            property_id,
            name.casefold(),
            address.casefold(),
            round(latitude, 6),
            round(longitude, 6),
        )

        if group_key not in grouped:
            source_hash = make_hash(property_id, name, address)

            grouped[group_key] = {
                "place_cat": "food_venue",
                "place_name": name,
                "place_address": address,
                "place_lat": latitude,
                "place_lon": longitude,
                "place_src": "City of Melbourne",
                "place_srcassetid": f"com:food:{property_id}:{source_hash}",
                "details": {
                    "census_year": latest_year,
                    "industry_code": clean_text(
                        row.get("Industry (ANZSIC4) code")
                    ),
                    "industry_description": clean_text(
                        row.get("Industry (ANZSIC4) description")
                    ),
                    "seats": {},
                },
            }

        seating_type = clean_text(row.get("Seating type")) or "Unknown"
        seat_count = parse_int(row.get("Number of seats"))

        seats = grouped[group_key]["details"]["seats"]
        seats[seating_type] = seats.get(seating_type, 0) + seat_count

    output: list[dict] = []

    for place in grouped.values():
        seats = place["details"]["seats"]
        place["details"]["total_seats"] = sum(seats.values())

        output.append(
            {
                "place_cat": place["place_cat"],
                "place_name": place["place_name"],
                "place_address": place["place_address"],
                "place_lat": place["place_lat"],
                "place_lon": place["place_lon"],
                "place_detailsjson": json.dumps(
                    place["details"],
                    ensure_ascii=False,
                    separators=(",", ":"),
                ),
                "place_src": place["place_src"],
                "place_srcassetid": place["place_srcassetid"],
            }
        )

    return output, latest_year, skipped


def build_museum_galleries(rows: list[dict]) -> tuple[list[dict], int]:
    output: list[dict] = []
    skipped = 0

    for row in rows:
        sub_theme = clean_text(row.get("Sub Theme"))

        if sub_theme.casefold() != "art gallery/museum".casefold():
            continue

        name = clean_text(row.get("Feature Name"))
        coordinate_text = clean_text(row.get("Co-ordinates"))

        try:
            latitude_text, longitude_text = coordinate_text.split(",", maxsplit=1)
            latitude = float(latitude_text.strip())
            longitude = float(longitude_text.strip())
        except (ValueError, TypeError):
            skipped += 1
            continue

        if not name:
            skipped += 1
            continue

        if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
            skipped += 1
            continue

        source_hash = make_hash(
            name,
            round(latitude, 6),
            round(longitude, 6),
        )

        details = {
            "theme": clean_text(row.get("Theme")),
            "sub_theme": sub_theme,
        }

        output.append(
            {
                "place_cat": "museum_gallery",
                "place_name": name,
                "place_address": "",
                "place_lat": latitude,
                "place_lon": longitude,
                "place_detailsjson": json.dumps(
                    details,
                    ensure_ascii=False,
                    separators=(",", ":"),
                ),
                "place_src": "City of Melbourne",
                "place_srcassetid": f"com:landmark:{source_hash}",
            }
        )

    return output, skipped


def main() -> None:
    cafe_rows = read_csv(CAFE_FILE)
    landmark_rows = read_csv(LANDMARK_FILE)

    food_venues, latest_year, skipped_food = build_food_venues(cafe_rows)
    museums, skipped_museums = build_museum_galleries(landmark_rows)

    places = food_venues + museums
    places.sort(key=lambda row: (row["place_cat"], row["place_name"].casefold()))

    source_ids = [row["place_srcassetid"] for row in places]

    if len(source_ids) != len(set(source_ids)):
        raise ValueError("Duplicate source asset IDs were generated")

    with OUTPUT_FILE.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as file:
        writer = csv.DictWriter(file, fieldnames=OUTPUT_FIELDS)
        writer.writeheader()
        writer.writerows(places)

    print(f"Latest cafe census year: {latest_year}")
    print(f"Food venues created: {len(food_venues)}")
    print(f"Museum/gallery places created: {len(museums)}")
    print(f"Food rows skipped: {skipped_food}")
    print(f"Museum/gallery rows skipped: {skipped_museums}")
    print(f"Total places created: {len(places)}")
    print(f"Output: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()