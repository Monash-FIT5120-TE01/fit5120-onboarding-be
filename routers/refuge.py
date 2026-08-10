from typing import List, Optional
from math import radians, cos, sin, asin, sqrt
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from models.refuge import Refuge
from db.main import get_session

# init router with config tags and prefixes
router = APIRouter(
    prefix = '/refuge',
    tags = ['Refuge-related API routes']
)

def haversine_distance(lon1, lat1, lon2, lat2):
    """
    Calculate the great circle distance in kilometers between two points
    on the earth (specified in decimal degrees)
    """
    # convert decimal degrees to radians
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])

    # haversine formula
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))
    r = 6378 # Radius of earth in kilometers
    return round(c * r, ndigits=4)  # because distance in other rows are rounded to 4 decimal numbers

@router.get('/', response_model=List[Refuge])
async def getRefuges(
    session: Session = Depends(get_session),
    tier: Optional[int] = None,
    proximity: Optional[int] = None,    # proximity to user's current location
    lat: Optional[float] = None,        # latitude of user's current location
    lon: Optional[float] = None         # longitude of user's current location
):
    try:
        statement = select(Refuge)
        results = session.exec(statement)
        refuges_list = results.all()

        # no proximity option, retrieve all refuge points match requested tier
        if proximity is None:
            return [refuge for refuge in refuges_list if refuge.refuge_tier == tier] if tier is not None else refuges_list
        else:
            # if no lat or lon provided
            if lat is None or lon is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail='Latitude or longitude is not provided'
                )

            # get only refuges within proximity haversine distance
            output = []
            for refuge in refuges_list:
                if haversine_distance(lon, lat, refuge.refuge_lon, refuge.refuge_lat) <= proximity:
                    if (tier is None) | (refuge.refuge_tier == tier):
                        output.append(refuge)
            return output

    except:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Error"
        )
