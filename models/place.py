from datetime import datetime, timezone

from sqlmodel import Field, SQLModel


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Place(SQLModel, table=True):
    __tablename__ = "place"

    place_id: int | None = Field(default=None, primary_key=True)
    place_cat: str = Field(max_length=30)
    place_name: str
    place_address: str | None = None
    place_lat: float
    place_lon: float
    place_detailsjson: str | None = None
    place_src: str = Field(max_length=50)
    place_srcassetid: str
    place_active: bool = True
    place_importedat: datetime = Field(default_factory=utc_now)