from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from db.main import get_session
from models.latest_pedestrian_status import LatestPedestrianStatus

# init router with config tags and prefixes
router = APIRouter(
    prefix = '/snapshot',
    tags = ['Sensors snapshot']
)

@router.get('/')
async def getLatestSnapshot(
    session: Session = Depends(get_session) 
):
    try:
        statement = select(LatestPedestrianStatus)
        results = session.exec(statement)
        return results.all()
    except:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Error"
        )