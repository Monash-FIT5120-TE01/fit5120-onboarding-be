from sqlmodel import SQLModel, Field

class Refuge(SQLModel, table=True):
    __tablename__ = "refuge"

    refuge_id: int = Field(primary_key=True)
    refuge_cat: str
    refuge_name: str
    refuge_lat: float
    refuge_lon: float
    refuge_tier: int
    refuge_area: float | None
    refuge_geometryjson: str | None
    refuge_src: str
    refuge_srcassetid: str

    