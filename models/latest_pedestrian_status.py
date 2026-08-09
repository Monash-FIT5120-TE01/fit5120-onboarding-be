from sqlmodel import DateTime, SQLModel, Field, text
from datetime import date, datetime

class LatestPedestrianStatus(SQLModel, table=True):
    __tablename__ = "latest_pedestrian_status"

    sensor_id: int = Field(primary_key=True)
    sc_date: date | None = Field(primary_key=True)
    sc_hour: int | None = Field(primary_key=True)
    sc_dir1: int | None
    sc_dir2: int | None
    sc_totaldirs: int | None
    sc_addedat: datetime | None = Field(sa_type=DateTime(timezone=True))
    cb_dir1: int | None
    cb_dir2: int | None
    cb_totaldirs: int | None
    cb_startdate: date | None
    cb_enddate: date | None
    cb_computedat: datetime | None = Field(sa_type=DateTime(timezone=True))
    ratio: float | None
    band: str | None

