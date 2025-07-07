from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import declarative_base
from src.config.settings import DATABASE_URL


# creating an async database engine that cat handle operations
engine = create_async_engine(DATABASE_URL, echo = True)

# creating a factory for generating async databse sessions
AsyncSessionLocal = async_sessionmaker(
    bind = engine, expire_on_commit = False)

# base class for ORM
Base = declarative_base()

# TODO: write in explanation name of model
async def init_db():
    """
    Initialize database by creating all tables defined in FILENAME
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

