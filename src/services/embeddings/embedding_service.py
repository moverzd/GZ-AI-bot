import re
import logging
from typing import List, Tuple, Dict, Any

import chromadb
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)


class EmbeddingService:
    """
    Сервис для работы с векторными представлениями (embeddings) продуктов.
    Использует ChromaDB для хранения и поиска векторов.
    """
    
    def __init__(
        self,
        model_name: str = 'deepvk/USER-bge-m3',
        chroma_path: str = "./chroma_db"
    ):
        self.model_name = model_name
        self.chroma_path = chroma_path
        self.model = None
        self.client = None
        self.collection = None
        self._is_initialized = False
    
    async def initialize(self):
        """
        Инициализирует векторную БД и загружает модель.
        """
        if self._is_initialized:
            logger.info("Сервис эмбеддингов уже инициализирован")
            return
        
        try:
            # Загружаем модель для создания эмбеддингов
            self.model = SentenceTransformer(self.model_name)
            
            # Инициализируем ChromaDB
            self.client = chromadb.PersistentClient(path=self.chroma_path)
            
            # Создаем или получаем коллекцию
            self.collection = self.client.get_or_create_collection(
                name="product_embeddings",
                metadata={"hnsw:space": "cosine"}
            )
            
            self._is_initialized = True
            logger.info(
                f"Сервис эмбеддингов инициализирован успешно. "
                f"Модель: {self.model_name}"
            )
            
        except Exception as e:
            logger.error(f"Ошибка инициализации сервиса эмбеддингов: {e}")
            raise
    
    def _check_initialization(self):
        """
        Проверяет, что сервис инициализирован.
        
        Raises:
            RuntimeError: Если сервис не инициализирован
        """
        if not self._is_initialized:
            raise RuntimeError(
                "Сервис эмбеддингов не инициализирован. "
                "Вызовите initialize() перед использованием."
            )
    
    def normalize_text_for_embedding(self, text: str) -> str:
        """
        Нормализует текст для создания эмбеддинга.
        
        Args:
            text: Исходный текст
            
        Returns:
            Нормализованный текст
        """
        if not text:
            return ""
        
        # Приводим к нижнему регистру
        text = text.lower()
        
        # Заменяем специальные символы на пробелы
        text = re.sub(r"[«»\"\'\-,.\(\)]", " ", text)
        
        # Убираем множественные пробелы
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text
    
    async def create_product_embedding(
        self,
        product_id: int,
        product_name: str,
        product_description: str = ""
    ) -> None:
        """
        Создает и сохраняет эмбеддинг для продукта.
        
        Args:
            product_id: ID продукта
            product_name: Название продукта
            product_description: Описание продукта (опционально)
        """
        self._check_initialization()
        
        try:
            # Объединяем название и описание
            full_text = f"{product_name} {product_description}".strip()
            
            # Нормализуем текст
            normalized_text = self.normalize_text_for_embedding(full_text)
            
            if not normalized_text:
                logger.warning(
                    f"Пустой текст после нормализации для продукта {product_id}"
                )
                return
            
            # Создаем эмбеддинг
            embedding = self.model.encode(normalized_text).tolist()
            
            # Сохраняем в ChromaDB
            self.collection.upsert(
                ids=[str(product_id)],
                embeddings=[embedding],
                metadatas=[{
                    "product_id": product_id,
                    "name": product_name,
                    "processed_text": normalized_text
                }],
                documents=[normalized_text]
            )
            
            logger.info(
                f"Эмбеддинг создан для продукта {product_id}: '{product_name}'"
            )
            
        except Exception as e:
            logger.error(
                f"Ошибка при создании эмбеддинга для продукта {product_id}: {e}"
            )
            raise
    
    async def update_product_embedding(
        self,
        product_id: int,
        product_name: str,
        product_description: str = ""
    ) -> None:
        """
        Обновляет эмбеддинг продукта.
        Псевдоним для create_product_embedding (upsert операция).
        
        Args:
            product_id: ID продукта
            product_name: Название продукта
            product_description: Описание продукта
        """
        await self.create_product_embedding(
            product_id, 
            product_name, 
            product_description
        )
    
    async def delete_product_embedding(self, product_id: int) -> None:
        """
        Удаляет эмбеддинг продукта из векторной БД.
        
        Args:
            product_id: ID продукта для удаления
        """
        self._check_initialization()
        
        try:
            self.collection.delete(ids=[str(product_id)])
            logger.info(f"Эмбеддинг для продукта {product_id} удален")
            
        except Exception as e:
            logger.error(
                f"Ошибка при удалении эмбеддинга для продукта {product_id}: {e}"
            )
            raise
    
    async def search_similar_products(
        self,
        query: str,
        limit: int = 3,
        min_similarity_threshold: float = 0.3
    ) -> List[Tuple[int, float]]:
        """
        Поиск похожих продуктов по текстовому запросу.
        
        Args:
            query: Поисковый запрос
            limit: Максимальное количество результатов
            min_similarity_threshold: Минимальный порог схожести (0-1)
            
        Returns:
            Список кортежей (product_id, similarity_score)
        """
        self._check_initialization()
        
        try:
            # Нормализуем запрос
            normalized_query = self.normalize_text_for_embedding(query)
            
            if not normalized_query:
                logger.warning("Пустой поисковый запрос после нормализации")
                return []
            
            # Создаем эмбеддинг для запроса
            query_embedding = self.model.encode(normalized_query).tolist()
            
            # Выполняем поиск
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=limit
            )
            
            # Фильтруем результаты по порогу схожести
            filtered_results = []
            
            if results['ids'] and results['distances']:
                for product_id, distance in zip(
                    results['ids'][0], 
                    results['distances'][0]
                ):
                    # Преобразуем distance в similarity (1 - distance для косинусной метрики)
                    similarity = 1 - distance
                    
                    if similarity >= min_similarity_threshold:
                        filtered_results.append((int(product_id), similarity))
            
            logger.info(
                f"Поиск эмбеддингов для '{query}': "
                f"найдено {len(filtered_results)} результатов"
            )
            
            return filtered_results
            
        except Exception as e:
            logger.error(f"Ошибка при поиске похожих продуктов: {e}")
            return []
    
    async def get_statistics(self) -> Dict[str, Any]:
        """
        Получает статистику по векторной БД.
        
        Returns:
            Словарь со статистикой
        """
        self._check_initialization()
        
        try:
            count = self.collection.count()
            
            return {
                "total_embeddings": count,
                "collection_name": "product_embeddings",
                "model_name": self.model_name,
                "is_initialized": self._is_initialized
            }
            
        except Exception as e:
            logger.error(f"Ошибка получения статистики: {e}")
            return {
                "error": str(e),
                "is_initialized": self._is_initialized
            }