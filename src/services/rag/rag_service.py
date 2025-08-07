import asyncio
import logging
from typing import List, Dict, Any, Optional

from src.services.embeddings.unified_embedding_service import UnifiedEmbeddingService
from src.services.rag.query_processor import QueryProcessor
from src.services.rag.llm_generator import LLMResponseGenerator
from src.services.rag.product_metadata import get_product_metadata

logger = logging.getLogger(__name__)

class RagService:
    """
    Основной сервис для работы с RAG (Retrieval Augmented Generation).
    Объединяет поиск по эмбеддингам и генерацию ответов с помощью LLM.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        # Векторное представление с поддержкой чанкинга
        # Используем одну базу данных с коллекцией для чанков
        self.embedding_service = UnifiedEmbeddingService(
            enable_chunking=True,
            chunk_size=200,  # 200 слов вместо 800
            chunk_overlap=50,  # 50 слов вместо 150
            chroma_path="./chroma_db",  # Используем общую базу
            collection_name="product_chunks_embeddings"  # Явно указываем коллекцию для чанков
        )
        # Обработка запросов
        self.query_processor = QueryProcessor()
        # Генерация ответов от LLM
        self.llm_generator = LLMResponseGenerator(api_key)
        self._is_initialized = False
    
    async def initialize(self):
        """
        Инициализация эмбеддингов и меняем флаг
        """
        if self._is_initialized:
            logger.info("RAG-сервис уже инициализирован")
            return
        
        try:
            # Инициализируем сервис эмбеддингов
            await self.embedding_service.initialize()
            self._is_initialized = True
            logger.info("RAG-сервис успешно инициализирован")
        except Exception as e:
            logger.error(f"Ошибка инициализации RAG-сервиса: {e}")
            raise
    
    async def search_and_answer(self, query: str, top_k: int = 7, threshold: float = 0.3, generate_answer: bool = True) -> Dict[str, Any]:
        """
        Поиск по запросу и генерация ответа
        """
        # Для подсчета времени генерации
        start_time = asyncio.get_event_loop().time()
        
        if not self._is_initialized:
            await self.initialize()
        
        logger.info(f"[RAG] Обрабатываем запрос: '{query}'")
        
        # Очищаем запрос
        processed_query = self.query_processor.clean_query(query)
        logger.info(f"[RAG] Обработанный запрос: '{processed_query}'")
        
        # Запускаем поиск по эмбеддингам
        logger.info(f"[RAG] Поиск документов (top_k={top_k}, threshold={threshold})")
        # Используем новый API поиска
        raw_results = await self.embedding_service.search_similar(
            query=processed_query, 
            result_limit=top_k, 
            min_similarity_threshold=threshold
        )
        
        logger.info(f"[RAG] Найдено {len(raw_results)} документов")
        
        # Шаг 3: Обработка результатов поиска
        logger.info(f"[RAG] Найдено {len(raw_results)} документов/чанков")
        detailed_results = self._process_search_results(raw_results)
        
        result = {
            "query": query,
            "processed_query": processed_query,
            "search_results": detailed_results,
            "total_found": len(detailed_results)
        }

        #TODO: проверить
        print(f"Полученный результат: {result}")
        
        # Генерация ответа, если был запрос
        if generate_answer and detailed_results:
            logger.info(f"[RAG] Генерация ответа с помощью LLM")
            try:
                #? Что выдает за answer и за result?
                answer = await self.llm_generator.generate_response(query, detailed_results)
                result["llm_answer"] = answer
                logger.info(f"[RAG] Ответ сгенерирован успешно")
                print(result["llm_answer"])
            except Exception as e:
                logger.error(f"Ошибка генерации ответа: {e}")
                result["llm_answer"] = f"Ошибка при генерации ответа: {str(e)}"
        
        # Добавляем время выполнения
        end_time = asyncio.get_event_loop().time()
        execution_time = end_time - start_time
        result["execution_time"] = execution_time
        
        logger.info(f"[RAG] Обработка завершена за {execution_time:.2f} секунд")
        
        return result
    
    def _process_search_results(self, search_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Обрабатывает результаты поиска из нового объединенного сервиса.
        """
        detailed_results = []
        
        for result in search_results:
            try:
                product_id = result.get("product_id")
                similarity = result.get("similarity", 0)
                text = result.get("text", "")
                metadata = result.get("metadata", {})
                
                product_name = metadata.get("product_name", f"Продукт {product_id}")
                
                # Формируем результат
                detailed_result = {
                    "product_id": product_id,
                    "product_name": product_name,
                    "similarity": similarity,
                    "text": text,
                    "text_preview": text[:300] + "..." if len(text) > 300 else text,
                    "file_path": metadata.get("file_path"),
                    "is_chunk": result.get("is_chunk", False),
                    "chunk_index": result.get("chunk_index")
                }
                
                # Добавляем дополнительные метаданные
                if "description" in metadata:
                    detailed_result["description"] = metadata["description"]
                
                detailed_results.append(detailed_result)
                
                chunk_info = f" (чанк #{result.get('chunk_index', 0)})" if result.get("is_chunk") else ""
                logger.info(f"Документ: '{product_name}'{chunk_info} (ID: {product_id}, сходство: {similarity:.4f})")
                
            except Exception as e:
                logger.error(f"Ошибка при обработке результата поиска: {e}")
                continue
        
        return detailed_results
    
    async def get_statistics(self) -> Dict[str, Any]:
        """
        Получает статистику по RAG-системе.
        """
        if not self._is_initialized:
            await self.initialize()
        
        # Получаем статистику от сервиса эмбеддингов
        embedding_stats = await self.embedding_service.get_statistics()
        
        return {
            "embedding_service": embedding_stats,
            "rag_service_initialized": self._is_initialized
        }
    
    async def close(self):
        """
        Закрывает все соединения и освобождает ресурсы.
        """
        try:
            await self.llm_generator.close()
            self._is_initialized = False
            logger.info("RAG-сервис закрыт")
        except Exception as e:
            logger.error(f"Ошибка при закрытии RAG-сервиса: {e}")
    
    def extract_product_names(self, query: str) -> List[str]:
        """
        Извлекает названия продуктов из запроса.
        """
        return self.query_processor.extract_product_names(query)
