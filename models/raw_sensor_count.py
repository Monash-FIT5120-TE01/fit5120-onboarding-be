from datetime import date, datetime
from sqlmodel import DateTime, SQLModel, Field, UniqueConstraint

class RawSensorCount(SQLModel, table=True):
    __tablename__ = "raw_sensor_count"
    __table_args__ = (
        UniqueConstraint(
            "location_id",
            "sensing_datetime",
            name='uq_rsc'
        ),
    )

    id: int = Field(primary_key=True)
    location_id: int
    sensing_datetime: datetime = Field(sa_type=DateTime(timezone=True))
    sensing_date: date
    sensing_time: str
    direction_1: int | None
    direction_2: int | None
    total_of_directions: int | None
    retrieved_at: datetime = Field(sa_type=DateTime(timezone=True))

class SCIngestionRun(SQLModel, table=True):
    __tablename__ = "sc_ingestion_run"

    id: int | None = Field(primary_key=True)
    last_successful_retrieval: datetime = Field(sa_type=DateTime(timezone=True))
    last_processed_hour: datetime | None = Field(default=None, sa_type=DateTime(timezone=True))
    