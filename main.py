import logging
import traceback

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Session
from routers import refuge, snapshot, sensor
from contextlib import asynccontextmanager
from db.main import init_db, get_session
from helpers.sc_ingestion import run_sc_ingestion

@asynccontextmanager
async def life_span(app: FastAPI):
    print(f'Server is starting...')
    await init_db()
    yield
    print(f'Server has been closed')

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("fastapi_logger")

app = FastAPI(
    title='SensoryWay API',
    description='REST API for SensoryWay application'
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(snapshot.router, prefix='/api')
app.include_router(sensor.router, prefix='/api')
app.include_router(refuge.router, prefix='/api')


@app.get("/")
async def root():
    return {"message": "Hello World"}

@app.get("/sc-ingestion-run")
async def sensor_hourly_ingestion(
    session: Session = Depends(get_session)
):
    try:
        return await run_sc_ingestion(session)
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=str(e)
        )