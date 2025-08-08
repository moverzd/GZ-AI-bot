import re
import logging
from typing import List, Tuple, Dict, Any, Optional

import chromadb
from .model_manager import model_manager

logger = logging.getLogger(__name__)


class UnifiedEmbeddingService:
    """
    Объединенный сервис для работы с векторными представлениями (embeddings).
    Поддерживает как простые эмбеддинги, так и чанкинг документов.
    Использует ChromaDB для хранения и поиска векторов.
    """
    
    def __init__(self, 
                 model_name: str = 'deepvk/USER-bge-m3',
                 chroma_path: str = "./chroma_db",
                 chunk_size: int = 400,  # Увеличиваем до 400 слов для лучшего контекста
                 chunk_overlap: int = 100,  # Увеличиваем перекрытие до 100 слов
                 enable_chunking: bool = True,
                 collection_name: Optional[str] = None):
        
        self.model_name = model_name
        self.chroma_path = chroma_path
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.enable_chunking = enable_chunking
        
        # Определяем имя коллекции
        if collection_name:
            self.collection_name = collection_name
        else:
            self.collection_name = "product_chunks_embeddings" if enable_chunking else "product_embeddings"
        
        self.model = None
        self.client = None
        self.collection = None
        self._is_initialized = False
    
    async def initialize(self):
        """
        Инициализирует векторную БД и загружает модель.
        """
        if self._is_initialized:
            logger.info("Объединенный сервис эмбеддингов уже инициализирован")
            return
        
        try:
            # Получаем модель через менеджер (загружается только один раз)
            self.model = model_manager.get_model(self.model_name)
            
            # Инициализируем ChromaDB
            self.client = chromadb.PersistentClient(path=self.chroma_path)
            
            # Используем заданное имя коллекции
            self.collection = self.client.get_or_create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"}
            )
            
            self._is_initialized = True
            logger.info(
                f"Объединенный сервис эмбеддингов инициализирован успешно. "
                f"Модель: {self.model_name}, Чанкинг: {self.enable_chunking}"
            )
            
        except Exception as e:
            logger.error(f"Ошибка инициализации объединенного сервиса эмбеддингов: {e}")
            raise
    
    def _check_initialization(self):
        """Проверяет, что сервис инициализирован."""
        if not self._is_initialized:
            raise RuntimeError(
                "Объединенный сервис эмбеддингов не инициализирован. "
                "Вызовите initialize() перед использованием."
            )
    
    def normalize_text_for_embedding(self, text: str) -> str:
        """
        Нормализует текст для создания эмбеддинга.
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
    
    def _simple_chunk_text(self, text: str, product_id: int) -> List[Dict[str, Any]]:
        """
        Простая реализация чанкинга текста.
        """
        words = text.split()
        chunks = []
        
        if len(words) <= self.chunk_size:
            # Если текст короткий, возвращаем как один чанк
            return [{
                "chunk_id": f"{product_id}_chunk_0",
                "text": text,
                "chunk_index": 0,
                "start_word": 0,
                "end_word": len(words)
            }]
        
        chunk_index = 0
        start_word = 0
        
        while start_word < len(words):
            end_word = min(start_word + self.chunk_size, len(words))
            
            # Берем слова для чанка
            chunk_words = words[start_word:end_word]
            chunk_text = " ".join(chunk_words)
            
            chunks.append({
                "chunk_id": f"{product_id}_chunk_{chunk_index}",
                "text": chunk_text,
                "chunk_index": chunk_index,
                "start_word": start_word,
                "end_word": end_word
            })
            
            # Сдвигаем окно с учетом перекрытия
            # Если это последний чанк, выходим
            if end_word >= len(words):
                break
                
            start_word = end_word - self.chunk_overlap
            chunk_index += 1
            
            # Дополнительная защита от бесконечного цикла
            if start_word <= 0:
                start_word = end_word
        
        return chunks
    
    async def create_product_embeddings(self, 
                                       product_id: int, 
                                       product_name: str, 
                                       full_text: str,
                                       file_path: Optional[str] = None,
                                       description: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Создает эмбеддинги для продукта.
        В зависимости от настроек может создавать один эмбеддинг или множество чанков.
        """
        self._check_initialization()
        
        try:
            logger.info(f"Создаем эмбеддинги для продукта {product_id}: '{product_name}'")
            
            # Подготавливаем базовые метаданные
            base_metadata = {
                "product_id": product_id,
                "product_name": product_name,
                "text_length": len(full_text)
            }
            
            if file_path:
                base_metadata["file_path"] = file_path
            if description:
                base_metadata["description"] = description
            
            results = []
            
            if self.enable_chunking:
                # Проверяем количество слов, а не символов
                word_count = len(full_text.split())
                if word_count > self.chunk_size:
                    # Разбиваем на чанки
                    chunks = self._simple_chunk_text(full_text, product_id)
                    logger.info(f"Разбили документ на {len(chunks)} чанков (слов в документе: {word_count})")
                else:
                    # Создаем один чанк для короткого документа
                    chunks = [{
                        "chunk_id": f"product_{product_id}_chunk_1",
                        "chunk_index": 1,
                        "text": full_text
                    }]
                    logger.info(f"Документ короткий ({word_count} слов), создаем один чанк")
                
                # Создаем эмбеддинги для каждого чанка
                chunk_ids = []
                chunk_embeddings = []
                chunk_metadatas = []
                chunk_documents = []
                
                for chunk in chunks:
                    normalized_text = self.normalize_text_for_embedding(chunk["text"])
                    
                    if not normalized_text:
                        continue
                    
                    # Создаем эмбеддинг
                    embedding = self.model.encode(normalized_text).tolist()
                    
                    # Метаданные для чанка
                    chunk_metadata = base_metadata.copy()
                    chunk_metadata.update({
                        "chunk_index": chunk["chunk_index"],
                        "section_type": "content",
                        "chunk_text_length": len(chunk["text"]),
                        "processed_text": normalized_text[:500]
                    })
                    
                    chunk_ids.append(chunk["chunk_id"])
                    chunk_embeddings.append(embedding)
                    chunk_metadatas.append(chunk_metadata)
                    chunk_documents.append(chunk["text"])
                    
                    results.append({
                        "chunk_id": chunk["chunk_id"],
                        "metadata": chunk_metadata,
                        "text": chunk["text"]
                    })
                
                # Сохраняем все чанки одним запросом
                if chunk_ids:
                    self.collection.upsert(
                        ids=chunk_ids,
                        embeddings=chunk_embeddings,
                        metadatas=chunk_metadatas,
                        documents=chunk_documents
                    )
                    
                    logger.info(f"Создано {len(chunk_ids)} эмбеддингов-чанков для продукта {product_id}")
                
                else:
                    # Создаем один эмбеддинг для всего документа (если чанкинг включен, но документ слишком короткий)
                    normalized_text = self.normalize_text_for_embedding(full_text)
                    
                    if normalized_text:
                        embedding = self.model.encode(normalized_text).tolist()
                        
                        metadata = base_metadata.copy()
                        metadata.update({
                            "section_type": "full_document",
                            "processed_text": normalized_text[:500],
                            "chunk_index": 0
                        })
                        
                        doc_id = f"{product_id}_chunk_0"
                        
                        self.collection.upsert(
                            ids=[doc_id],
                            embeddings=[embedding],
                            metadatas=[metadata],
                            documents=[full_text]
                        )
                        
                        logger.info(f"Создан 1 эмбеддинг для продукта {product_id} (документ слишком короткий для чанкинга)")
                        
                        results.append({
                            "chunk_id": doc_id,
                            "metadata": metadata,
                            "text": full_text
                        })
            
            else:
                # Чанкинг отключен - создаем один эмбеддинг для всего документа
                normalized_text = self.normalize_text_for_embedding(full_text)
                
                if normalized_text:
                    embedding = self.model.encode(normalized_text).tolist()
                    
                    metadata = base_metadata.copy()
                    metadata.update({
                        "section_type": "full_document",
                        "processed_text": normalized_text[:500]
                    })
                    
                    doc_id = str(product_id)
                    
                    self.collection.upsert(
                        ids=[doc_id],
                        embeddings=[embedding],
                        metadatas=[metadata],
                        documents=[full_text]
                    )
                    
                    logger.info(f"Создан 1 эмбеддинг для продукта {product_id}")
                    
                    results.append({
                        "chunk_id": doc_id,
                        "metadata": metadata,
                        "text": full_text
                    })
            
            return results
            
        except Exception as e:
            logger.error(f"Ошибка при создании эмбеддингов для продукта {product_id}: {e}")
            raise
    
    async def delete_product_embeddings(self, product_id: int) -> None:
        """
        Удаляет все эмбеддинги продукта из векторной БД.
        """
        self._check_initialization()
        
        try:
            # Получаем все эмбеддинги продукта
            results = self.collection.get(
                where={"product_id": product_id}
            )
            
            if results['ids']:
                self.collection.delete(ids=results['ids'])
                logger.info(f"Удалено {len(results['ids'])} эмбеддингов для продукта {product_id}")
            else:
                logger.info(f"Эмбеддинги для продукта {product_id} не найдены")
                
        except Exception as e:
            logger.error(f"Ошибка при удалении эмбеддингов для продукта {product_id}: {e}")
            raise
    
    async def delete_file_embeddings(self, file_path: str) -> int:
        """
        Удаляет эмбеддинги конкретного файла из векторной БД.
        
        Args:
            file_path: Путь к файлу
            
        Returns:
            Количество удаленных эмбеддингов
        """
        self._check_initialization()
        
        try:
            # Получаем все эмбеддинги файла
            results = self.collection.get(
                where={"file_path": file_path}
            )
            
            deleted_count = 0
            if results['ids']:
                self.collection.delete(ids=results['ids'])
                deleted_count = len(results['ids'])
                logger.info(f"Удалено {deleted_count} эмбеддингов для файла {file_path}")
            else:
                logger.info(f"Эмбеддинги для файла {file_path} не найдены")
                
            return deleted_count
                
        except Exception as e:
            logger.error(f"Ошибка при удалении эмбеддингов для файла {file_path}: {e}")
            raise
    
    async def search_similar(self, 
                            query: str, 
                            result_limit: int = 5, 
                            min_similarity_threshold: float = 0.3) -> List[Dict[str, Any]]:
        """
        Поиск похожих документов или чанков по текстовому запросу.
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
                n_results=result_limit,
                include=["metadatas", "documents", "distances"]
            )
            
            # Обрабатываем результаты
            enhanced_results = []
            
            if results['ids'] and results['distances']:
                for i, (doc_id, distance) in enumerate(zip(results['ids'][0], results['distances'][0])):
                    # Преобразуем distance в similarity
                    similarity = 1 - distance
                    
                    if similarity >= min_similarity_threshold:
                        metadata = results['metadatas'][0][i] if results['metadatas'] else {}
                        document = results['documents'][0][i] if results['documents'] else ""
                        
                        result_data = {
                            "id": doc_id,
                            "product_id": metadata.get("product_id"),
                            "product_name": metadata.get("product_name"),
                            "similarity": similarity,
                            "text": document,
                            "metadata": metadata
                        }
                        
                        # Добавляем информацию о чанке, если это чанк
                        if "chunk_index" in metadata:
                            result_data["chunk_index"] = metadata["chunk_index"]
                            result_data["is_chunk"] = True
                        else:
                            result_data["is_chunk"] = False
                        
                        enhanced_results.append(result_data)
            
            logger.info(f"Поиск для '{query}': найдено {len(enhanced_results)} результатов")
            
            return enhanced_results
            
        except Exception as e:
            logger.error(f"Ошибка при поиске: {e}")
            return []
    
    async def get_statistics(self) -> Dict[str, Any]:
        """
        Получает статистику по векторной БД.
        """
        self._check_initialization()
        
        try:
            count = self.collection.count()
            
            # Получаем дополнительную статистику
            results = self.collection.get(include=["metadatas"])
            
            product_counts = {}
            chunk_counts = 0
            full_doc_counts = 0
            
            if results['metadatas']:
                for metadata in results['metadatas']:
                    product_id = metadata.get('product_id')
                    if product_id:
                        product_counts[product_id] = product_counts.get(product_id, 0) + 1
                    
                    if "chunk_index" in metadata:
                        chunk_counts += 1
                    else:
                        full_doc_counts += 1
            
            return {
                "total_embeddings": count,
                "collection_name": self.collection.name,
                "model_name": self.model_name,
                "chunking_enabled": self.enable_chunking,
                "chunk_size": self.chunk_size,
                "chunk_overlap": self.chunk_overlap,
                "unique_products": len(product_counts),
                "chunk_embeddings": chunk_counts,
                "full_document_embeddings": full_doc_counts,
                "avg_embeddings_per_product": sum(product_counts.values()) / len(product_counts) if product_counts else 0,
                "is_initialized": self._is_initialized
            }
            
        except Exception as e:
            logger.error(f"Ошибка получения статистики: {e}")
            return {
                "error": str(e),
                "is_initialized": self._is_initialized
            }
    
    # Методы для совместимости со старым API
    async def create_product_embedding(self, product_id: int, product_name: str, product_description: str = "") -> None:
        """
        Метод для совместимости со старым API.
        """
        await self.create_product_embeddings(
            product_id=product_id,
            product_name=product_name,
            full_text=f"{product_name}. {product_description}"
        )
    
    async def search_similar_products(self, query: str, result_limit: int = 3, min_similarity_threshold: float = 0.3) -> List[Tuple[int, float]]:
        """
        Метод для совместимости со старым API.
        Возвращает результаты в старом формате (product_id, similarity).
        """
        results = await self.search_similar(
            query=query,
            result_limit=result_limit,
            min_similarity_threshold=min_similarity_threshold
        )
        
        # Группируем по продуктам и берем лучший результат для каждого
        product_results = {}
        for result in results:
            product_id = result["product_id"]
            similarity = result["similarity"]
            
            if product_id not in product_results or similarity > product_results[product_id]:
                product_results[product_id] = similarity
        
        # Конвертируем в старый формат
        return [(product_id, similarity) for product_id, similarity in product_results.items()]
