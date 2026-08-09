from sqlmodel import create_engine, text, Session
from config import Config

engine = create_engine(
    url=Config.DATABASE_URL,
    echo=True
)


async def init_db():
    async with engine.begin() as conn:
        statement = text("SELECT 'hello'")
        result = await conn.execute(statement)
        print(result.all())

def get_session():
    with Session(engine) as session:
        yield session