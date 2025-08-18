import logging
from typing import List, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.database.models import Product
from src.services.embeddings.unified_embedding_service import UnifiedEmbeddingService
from .base import BaseSearchService

logger = logging.getLogger(__name__)


class SemanticSearchService(BaseSearchService):
    """
    Сервис для выполнения семантического поиска продуктов.
    Использует embeddings и косинусное сходство для поиска похожих продуктов.
    """
    
    def __init__(self, session: AsyncSession):
        self.session = session
        # Используем унифицированный сервис для поиска по продуктам
        # ВАЖНО: Используем ту же коллекцию, что и AutoChunkingService для синхронизации
        self.embedding_service = UnifiedEmbeddingService(
            enable_chunking=True,  # Включаем чанкинг для совместимости с AutoChunkingService
            chroma_path="./chroma_db",
            collection_name="product_chunks_embeddings"  # Та же коллекция, что использует AutoChunkingService
        )
        # Инициализируем сервис эмбеддингов
        import asyncio
        if hasattr(asyncio, '_get_running_loop') and asyncio._get_running_loop() is not None:
            # Если мы уже в async контексте, планируем инициализацию
            asyncio.create_task(self.embedding_service.initialize())
        else:
            # Если не в async контексте, инициализация будет выполнена при первом вызове
            pass
    
    async def find_products_by_query(self,query: str,category_id: Optional[int] = None,user_id: Optional[int] = None,limit: int = 3) -> List[Product]:
        """
        Выполняет семантический поиск продуктов по смысловому сходству.
        """
        try:
            # Убеждаемся, что сервис эмбеддингов инициализирован
            if not self.embedding_service._is_initialized:
                await self.embedding_service.initialize()
            
            # Получаем похожие продукты через семантический поиск
            similar_products = await self._find_similar_products_by_embedding(
                query, 
                limit
            )
            
            if not similar_products:
                logger.info(f"Семантический поиск: результатов не найдено для '{query}'")
                return []
            
            # Получаем полные данные продуктов из БД
            products = await self._fetch_products_by_similarity_results(similar_products, category_id)
            
            # Сортируем по релевантности
            sorted_products = self._sort_products_by_relevance(products, similar_products)
            
            logger.info(
                f"Семантический поиск: найдено {len(sorted_products)} продуктов "
                f"для запроса '{query}'"
            )
            
            return sorted_products
            
        except Exception as e:
            logger.error(f"Ошибка при выполнении семантического поиска: {e}")
            return []
    
    async def _find_similar_products_by_embedding(self, query: str, limit: int) -> List[Tuple[int, float]]:
        """
        Находит похожие продукты используя векторные представления.
        """
        return await self.embedding_service.search_similar_products(query=query,result_limit=limit,min_similarity_threshold=0.3)
    
    async def _fetch_products_by_similarity_results(self,similar_products: List[Tuple[int, float]],category_id: Optional[int]) -> List[Product]:
        """
        Получает полные данные продуктов из БД по результатам семантического поиска.
        """
        # Извлекаем ID продуктов
        product_ids = [product_id for product_id, _ in similar_products]
        
        # Строим запрос
        query = select(Product).where(
            Product.id.in_(product_ids),
            Product.is_deleted == False
        )
        
        # Добавляем фильтр по категории если указан
        if category_id:
            query = query.where(Product.category_id == category_id)
        
        # Выполняем запрос
        result = await self.session.execute(query)
        products = result.scalars().all()
        
        return list(products)
    
    def _sort_products_by_relevance(self,products: List[Product],similar_products: List[Tuple[int, float]]) -> List[Product]:
        """
        Сортирует продукты по релевантности на основе similarity score.
        """

        # Создаем словарь для быстрого доступа к оценкам
        relevance_scores = {product_id: score for product_id, score in similar_products}
        
        # Сортируем по убыванию релевантности
        return sorted(products, key=lambda p: relevance_scores.get(getattr(p, 'id', 0), 0), reverse=True)