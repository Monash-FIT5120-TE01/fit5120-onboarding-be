from datetime import date, datetime
from pydantic import BaseModel

import httpx

class SCAPIRecord(BaseModel):
    location_id: int
    sensing_datetime: datetime
    sensing_date: date
    sensing_time: str
    direction_1: int | None
    direction_2: int | None
    total_of_directions: int | None

async def get_sc_data() -> list[SCAPIRecord]:
    transport = httpx.AsyncHTTPTransport(http1=True, http2=False)

    async with httpx.AsyncClient(transport=transport, timeout=30) as client:
        response = await client.get(
            "https://data.melbourne.vic.gov.au/api/explore/v2.1/catalog/datasets/pedestrian-counting-system-past-hour-counts-per-minute/exports/json?where=sensing_datetime%20%3E%3D%20now%28hours%3D-2%29&order_by=location_id%2C%20sensing_datetime&limit=-1&timezone=Australia%2FMelbourne&use_labels=false&compressed=false&epsg=4326"
        )

        response.raise_for_status()

        res = [SCAPIRecord.model_validate(item) for item in response.json()]
        return res