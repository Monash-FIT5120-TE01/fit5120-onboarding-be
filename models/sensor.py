from sqlmodel import SQLModel, Field

class Sensor(SQLModel, table=True):
    __tablename__ = "sensor"

    sensor_id: int = Field(primary_key=True)
    sensor_desc: str
    sensor_lat: float
    sensor_lon: float
    sensor_isoutdoor: int
    sensor_dir1: str
    sensor_dir2: str
    sensor_note: str

    