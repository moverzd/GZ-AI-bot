import re
import logging
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from src.database.models import Product
from .base import BaseSearchService

logger = logging.getLogger(__name__)


class LexicalSearchService(BaseSearchService):
    """
    Сервис для выполнения лексического (текстового) поиска продуктов.
    Ищет совпадения по названию продукта используя SQL LIKE.
    """
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def find_products_by_query(self,query: str,category_id: Optional[int] = None, user_id: Optional[int] = None,limit: int = 20) -> List[Product]:
        """
        Выполняет лексический поиск продуктов по названию.
        """
        try:
            normalized_query = self._prepare_query_for_lexical_search(query)
            
            if not normalized_query:
                logger.warning("Пустой поисковый запрос после нормализации")
                return []
            
            search_conditions = self._build_search_conditions(normalized_query)
            
            if not search_conditions:
                return []
            
            products = await self._execute_search_query(search_conditions, category_id, limit)
            
            logger.info(
                f"Лексический поиск: найдено {len(products)} продуктов "
                f"для запроса '{query}'"
            )
            
            return products
            
        except Exception as e:
            logger.error(f"Ошибка при выполнении лексического поиска: {e}")
            return []
    
    def _prepare_query_for_lexical_search(self, query: str) -> str:
        """
        Подготавливает запрос для лексического поиска.
        Удаляет специальные символы и нормализует текст.
        """

        # Нормализуем базово
        normalized = self._normalize_search_query(query)
        
        # Удаляем все символы кроме букв, цифр и пробелов
        cleaned = re.sub(r'[^\w\s]', '', normalized)
        
        return cleaned.strip()
    
    def _build_search_conditions(self, normalized_query: str) -> List:
        """
        Строит условия поиска для SQL запроса.
        Каждое слово должно присутствовать в названии продукта.
        """
        words = normalized_query.split()
        
        if not words:
            return []
        
        # Создаем условие для каждого слова
        conditions = []
        for word in words:
            conditions.append(func.lower(Product.name).contains(word))
        
        return conditions
    
    async def _execute_search_query(self,search_conditions: List,category_id: Optional[int],limit: int) -> List[Product]:
        """
        Выполняет SQL запрос для поиска продуктов.
        """
        # Базовый запрос с условиями поиска - используем AND вместо OR
        # Все слова должны присутствовать в названии продукта
        query = select(Product).where(*search_conditions,Product.is_deleted == False)
        
        # Добавляем фильтр по категории если указан
        if category_id:
            query = query.where(Product.category_id == category_id)
        
        # Ограничиваем количество результатов
        query = query.limit(limit)
        
        # Выполняем запрос
        result = await self.session.execute(query)
        products = result.scalars().all()
        
        return list(products)