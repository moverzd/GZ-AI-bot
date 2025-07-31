"""
Модуль поиска продуктов.

Предоставляет гибридный поиск с fallback механизмом:
1. Лексический поиск по названию
2. Семантический поиск при отсутствии результатов
"""

from .base import BaseSearchService
from .lexical_search import LexicalSearchService
from .semantic_search import SemanticSearchService
from .hybrid_search import HybridSearchService

# При импорте модуля будет доступно то что написано снизу
# Аналог private в методах
__all__ = [
    'BaseSearchService',
    'LexicalSearchService',
    'SemanticSearchService',
    'HybridSearchService',
]