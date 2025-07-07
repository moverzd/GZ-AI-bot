from typing import List, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.repositories import ProductRepository, ProductFileRepository
from src.database.models import Product


class SearchService:
    """
    Service for searching products
    """
    def __init__(self, session: AsyncSession):
        self.session = session
        self.product_repo = ProductRepository(session)
        self.file_repo = ProductFileRepository(session)
    
    async def search_products(self, query: str) -> List[Tuple[Product, Optional[str]]]:
        """
        Searching products by query with images
        Улучшенный поиск с поддержкой различных форматов запросов:
        - Поиск по названию продукта с учетом разных разделителей
        - Поиск по частичным совпадениям
        - Поиск по разделенным словам (например "брит а" для поиска "БРИТ А")
        - Игнорирование регистра и лишних пробелов
        """
        # Очищаем запрос от лишних пробелов
        query = query.strip()
        if not query:
            return []
        
        # Выполняем поиск через репозиторий с улучшенной логикой
        products = await self.product_repo.search(query)
        results = []

        # Добавляем изображения к результатам поиска
        for product in products:
            # Используем getattr для получения id, как в других сервисах
            product_id = getattr(product, 'id')
            main_image = await self.file_repo.get_main_image(product_id)
            results.append((product, main_image))
        
        return results

