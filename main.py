import logging

from fastapi import FastAPI
from routers import refuge, snapshot, sensor
from contextlib import asynccontextmanager
from db.main import init_db

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

app.include_router(snapshot.router, prefix='/api')
app.include_router(sensor.router, prefix='/api')
app.include_router(refuge.router, prefix='/api')


@app.get("/")
async def root():
    return {"message": "Hello World"}