from typing import List, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.repositories import ProductRepository
from src.database.product_file_repositories import ProductFileRepository
from src.database.models import Product

import re

class SearchService:
    """
    Сервис для поиска продуктов
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
        query = query.strip()
        if not query:
            return []
        
        # Нормализация поискового запроса
        normalized_query = query.lower()
        search_variants = [normalized_query]  # Список вариантов для поиска
        
        # Убираем пробелы и дефисы для создания сжатой версии запроса
        condensed_query = re.sub(r'[\s\-]+', '', normalized_query)
        if condensed_query != normalized_query:
            search_variants.append(condensed_query)

        # Обработка разделённых слов и букв
        if ' ' in normalized_query or '-' in normalized_query:
            parts = re.split(r'[\s\-]+', normalized_query)
            joined_parts = ''.join(parts)
            if joined_parts not in search_variants:
                search_variants.append(joined_parts)

            for i in range(len(parts) - 1):
                combined_parts = parts.copy()
                combined_parts[i] = parts[i] + parts[i + 1]
                combined_parts.pop(i + 1)
                
                search_variants.append(' '.join(combined_parts))
                search_variants.append('-'.join(combined_parts))

        # Формируем условия для поиска продуктов в базе
        or_conditions = [Product.name.ilike(f"%{variant}%") for variant in search_variants]

        # Выполняем поиск через репозиторий с улучшенной логикой
        products = await self.product_repo.search_by_conditions(or_conditions)
        results = []

        # Добавляем изображения к результатам поиска
        for product in products:
            product_id = getattr(product, 'id')
            main_image = await self.file_repo.get_main_image(product_id)
            results.append((product, main_image))
        
        return results
