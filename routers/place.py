from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlmodel import Session, select

from db.main import get_session
from models.place import Place


router = APIRouter(
    prefix="/place",
    tags=["Places information"],
)


@router.get("/", response_model=List[Place])
def get_places(
    category: Optional[str] = None,
    limit: int = Query(default=100, ge=1, le=500),
    session: Session = Depends(get_session),
):
    statement = select(Place).where(Place.place_active == True)  # noqa: E712

    if category is not None:
        statement = statement.where(Place.place_cat == category)

    statement = statement.order_by(Place.place_id).limit(limit)

    return session.exec(statement).all()