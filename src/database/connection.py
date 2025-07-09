from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import declarative_base
from src.config.settings import DATABASE_URL

"""
Установка и инициализация подключения к бд с использованием SQLAlchemy 
"""

# создание асинхронного движка для работы с бд
engine = create_async_engine(DATABASE_URL, echo = True)

# фабрика генерации асинхронных сессий
AsyncSessionLocal = async_sessionmaker(
    bind = engine, expire_on_commit = False)

# Базовый класс для ORM модели
Base = declarative_base()

async def init_db():
    """
    Инициализация бд, создание таблиц, определенных в models.py
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

