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
        Получить все категории, исключая скрытые для пользователей
        """
        # Список названий категорий, которые нужно скрыть от пользователей
        hidden_categories = [
            "Материалы рулонные", 
            "Праймеры «БРИТ»", 
            "Промышленно-гражданские мастики"
        ]
        
        result = await self.session.execute(
            select(Category).where(
                ~Category.name.in_(hidden_categories)
            )
        )
        return list(result.scalars().all())