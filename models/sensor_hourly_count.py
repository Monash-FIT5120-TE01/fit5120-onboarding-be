from datetime import date, datetime
from sqlmodel import DateTime, SQLModel, Field, UniqueConstraint

class SensorHourlyCount(SQLModel, table=True):
    __tablename__ = "sensor_hourly_count"
    __table_args__ = (
        UniqueConstraint(
            "sensor_id",
            "sc_date",
            "sc_hour",
            name='uq_sc'
        ),
    )

    sc_id: int = Field(primary_key=True)
    sensor_id: int
    sc_date: date
    sc_hour: int
    sc_dir1: int | None
    sc_dir2: int | None
    sc_totaldirs: int | None
    sc_addedat: datetime = Field(sa_type=DateTime(timezone=True))

    