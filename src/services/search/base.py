from abc import ABC, abstractmethod
from typing import List, Optional
from src.database.models import Product


# ABC - Abstract Base Class - не позволяет создать экземпляр напрямую
class BaseSearchService(ABC):
    """
    Базовый абстрактный класс для всех поисковых сервисов.
    Определяет интерфейс для поиска продуктов.
    """
    
    @abstractmethod
    async def find_products_by_query(self, query: str, category_id: Optional[int] = None, user_id: Optional[int] = None, limit: int = 20) -> List[Product]:
        """
        Поиск продуктов по запросу.
        """
        pass # абстрактный метод, то есть у дочерних классов должна быть реализация
    
    def _normalize_search_query(self, query: str) -> str:
        """
        Нормализация поискового запроса.
        Базовая реализация для всех типов поиска.
        """
        if not query:
            return ""
        
        # Приводим к нижнему регистру и убираем лишние пробелы
        return " ".join(query.lower().split())