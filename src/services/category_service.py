from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from src.database.models import Category

class CategoryService:
    """
    Сервис для работы с категорями продуктов
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_all_categories(self) -> List[Category]:
        """
        Вернуть все категории
        """
        result = await self.session.execute(select(Category))
        return list(result.scalars().all())