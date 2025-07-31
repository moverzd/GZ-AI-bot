import logging
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import Product
from .base import BaseSearchService
from .lexical_search import LexicalSearchService
from .semantic_search import SemanticSearchService

logger = logging.getLogger(__name__)


class HybridSearchService(BaseSearchService):
    """
    Гибридный поисковый сервис с fallback механизмом.
    
    Алгоритм работы:
    1. Сначала выполняется лексический поиск
    2. Если лексический поиск не дал результатов, выполняется семантический поиск
    """
    
    def __init__(
        self,
        session: AsyncSession,
        lexical_search: LexicalSearchService,
        vector_search: SemanticSearchService  # Изменено с VectorSearchService
    ):
        self.session = session
        self.lexical_search = lexical_search
        self.vector_search = vector_search
    
    async def find_products_by_query(
        self,
        query: str,
        category_id: Optional[int] = None,
        user_id: Optional[int] = None,
        limit: int = 20
    ) -> List[Product]:
        """
        Выполняет гибридный поиск продуктов.
        
        Args:
            query: Поисковый запрос
            category_id: ID категории для фильтрации
            user_id: ID пользователя
            limit: Максимальное количество результатов
            
        Returns:
            Список найденных продуктов
        """
        if not query or not query.strip():
            logger.warning("Получен пустой поисковый запрос")
            return []
        
        # Шаг 1: Пробуем лексический поиск
        products = await self._try_lexical_search(
            query, 
            category_id, 
            user_id, 
            limit
        )
        
        if products:
            logger.info(
                f"Гибридный поиск: использован лексический поиск, "
                f"найдено {len(products)} результатов"
            )
            return products
        
        # Шаг 2: Если лексический не дал результатов, используем семантический
        logger.info(
            f"Гибридный поиск: лексический поиск не дал результатов для '{query}', "
            f"переключаемся на семантический поиск"
        )
        
        products = await self._try_vector_search(
            query,
            category_id,
            user_id,
            limit=3  # Для семантического поиска используем меньший лимит
        )
        
        if products:
            logger.info(
                f"Гибридный поиск: использован семантический поиск, "
                f"найдено {len(products)} результатов"
            )
        else:
            logger.info(
                f"Гибридный поиск: не найдено результатов для запроса '{query}'"
            )
        
        return products
    
    async def _try_lexical_search(
        self,
        query: str,
        category_id: Optional[int],
        user_id: Optional[int],
        limit: int
    ) -> List[Product]:
        """
        Выполняет попытку лексического поиска.
        
        Args:
            query: Поисковый запрос
            category_id: ID категории
            user_id: ID пользователя
            limit: Максимальное количество результатов
            
        Returns:
            Список найденных продуктов или пустой список
        """
        try:
            return await self.lexical_search.find_products_by_query(
                query=query,
                category_id=category_id,
                user_id=user_id,
                limit=limit
            )
        except Exception as e:
            logger.error(f"Ошибка в лексическом поиске: {e}")
            return []
    
    async def _try_vector_search(
        self,
        query: str,
        category_id: Optional[int],
        user_id: Optional[int],
        limit: int
    ) -> List[Product]:
        """
        Выполняет попытку семантического поиска.
        
        Args:
            query: Поисковый запрос
            category_id: ID категории
            user_id: ID пользователя
            limit: Максимальное количество результатов
            
        Returns:
            Список найденных продуктов или пустой список
        """
        try:
            return await self.vector_search.find_products_by_query(
                query=query,
                category_id=category_id,
                user_id=user_id,
                limit=limit
            )
        except Exception as e:
            logger.error(f"Ошибка в семантическом поиске: {e}")
            return []