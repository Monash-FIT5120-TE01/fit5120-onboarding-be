from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from models.sensor import Sensor
from db.main import get_session

# init router with config tags and prefixes
router = APIRouter(
    prefix = '/sensor',
    tags = ['Sensors information']
)

@router.get('/', response_model=List[Sensor])
async def getAllSensors(
    session: Session = Depends(get_session),
):
    try:
        statement = select(Sensor)
        results = session.exec(statement)
        return results.all()
    except:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Error"
        )