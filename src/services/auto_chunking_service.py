import asyncio
import logging
import os
from typing import Optional, Dict, Any, List
from datetime import datetime

from src.services.embeddings.unified_embedding_service import UnifiedEmbeddingService
from src.database.models import ProductFile
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

logger = logging.getLogger(__name__)

class AutoChunkingService:
    """
    Автоматизированный сервис для чанкинга и индексации файлов.
    Интегрируется с существующей системой загрузки файлов.
    """
    
    def __init__(self, 
                 chunk_size: int = 200,  # 200 слов вместо 800
                 chunk_overlap: int = 50,  # 50 слов вместо 150
                 chroma_path: str = "./chroma_db"):  # Используем общую базу
        """
        Инициализация сервиса автоматического чанкинга
        """
        self.embedding_service = UnifiedEmbeddingService(
            enable_chunking=True,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            chroma_path=chroma_path,
            collection_name="product_chunks_embeddings"  # Явно указываем коллекцию для чанков
        )
        self._is_initialized = False
        
    async def initialize(self):
        """Инициализация сервиса"""
        if not self._is_initialized:
            await self.embedding_service.initialize()
            self._is_initialized = True
            logger.info("AutoChunkingService инициализирован")
    
    async def process_uploaded_file(self, 
                                  product_id: int, 
                                  product_name: str, 
                                  file_path: str,
                                  file_title: Optional[str] = None) -> Dict[str, Any]:
        """
        Обрабатывает загруженный файл: извлекает текст и создает эмбеддинги с чанкингом
        
        Args:
            product_id: ID продукта
            product_name: Название продукта  
            file_path: Путь к загруженному файлу
            file_title: Название файла (опционально)
            
        Returns:
            Словарь с результатами обработки
        """
        await self.initialize()
        
        result = {
            "success": False,
            "product_id": product_id,
            "file_path": file_path,
            "chunks_created": 0,
            "error": None,
            "processing_time": 0
        }
        
        start_time = datetime.now()
        
        try:
            # Проверяем, что файл существует
            if not os.path.exists(file_path):
                result["error"] = f"Файл не найден: {file_path}"
                return result
            
            # Извлекаем текст из файла
            full_text = await self._extract_text_from_file(file_path)
            
            if not full_text or len(full_text) < 100:
                result["error"] = f"Недостаточно текста для индексации (длина: {len(full_text) if full_text else 0})"
                return result
            
            logger.info(f"[AutoChunking] Обрабатываем файл {file_path} (продукт {product_id})")
            logger.info(f"[AutoChunking] Извлечено {len(full_text)} символов текста")
            
            # Создаем эмбеддинги с чанкингом
            chunks = await self.embedding_service.create_product_embeddings(
                product_id=product_id,
                product_name=product_name,
                full_text=full_text,
                file_path=file_path,
                description=file_title  # Используем description вместо file_title
            )
            
            result["success"] = True
            result["chunks_created"] = len(chunks)
            
            logger.info(f"[AutoChunking] Создано {len(chunks)} эмбеддингов для продукта {product_id}")
            
        except Exception as e:
            logger.error(f"[AutoChunking] Ошибка при обработке файла {file_path}: {e}")
            result["error"] = str(e)
        
        finally:
            end_time = datetime.now()
            result["processing_time"] = (end_time - start_time).total_seconds()
        
        return result
    
    async def reindex_product(self, 
                            product_id: int, 
                            product_name: str,
                            session: AsyncSession) -> Dict[str, Any]:
        """
        Переиндексирует все файлы продукта
        
        Args:
            product_id: ID продукта
            product_name: Название продукта
            session: Сессия базы данных
            
        Returns:
            Результаты переиндексации
        """
        await self.initialize()
        
        result = {
            "success": False,
            "product_id": product_id,
            "files_processed": 0,
            "total_chunks": 0,
            "errors": [],
            "processing_time": 0
        }
        
        start_time = datetime.now()
        
        try:
            # Удаляем старые эмбеддинги продукта
            await self.embedding_service.delete_product_embeddings(product_id)
            logger.info(f"[AutoChunking] Удалены старые эмбеддинги для продукта {product_id}")
            
            # Получаем все файлы продукта
            query = select(ProductFile).where(
                (ProductFile.product_id == product_id) &
                (ProductFile.local_path.isnot(None))
            )
            result_files = await session.execute(query)
            files = result_files.scalars().all()
            
            if not files:
                result["error"] = f"У продукта {product_id} нет файлов для индексации"
                return result
            
            logger.info(f"[AutoChunking] Найдено {len(files)} файлов для переиндексации продукта {product_id}")
            
            # Обрабатываем каждый файл
            for file_record in files:
                file_path = self._get_absolute_file_path(str(file_record.local_path))
                
                if not os.path.exists(file_path):
                    result["errors"].append(f"Файл не найден: {file_path}")
                    continue
                
                # Обрабатываем файл
                file_title = getattr(file_record, 'title', None)
                file_result = await self.process_uploaded_file(
                    product_id=product_id,
                    product_name=product_name,
                    file_path=file_path,
                    file_title=str(file_title) if file_title else None
                )
                
                if file_result["success"]:
                    result["files_processed"] += 1
                    result["total_chunks"] += file_result["chunks_created"]
                else:
                    result["errors"].append(f"Файл {file_path}: {file_result.get('error', 'Неизвестная ошибка')}")
            
            result["success"] = result["files_processed"] > 0
            
        except Exception as e:
            logger.error(f"[AutoChunking] Ошибка при переиндексации продукта {product_id}: {e}")
            result["errors"].append(str(e))
        
        finally:
            end_time = datetime.now()
            result["processing_time"] = (end_time - start_time).total_seconds()
        
        return result
    
    async def mass_reindex_all_products(self, session: AsyncSession) -> Dict[str, Any]:
        """
        Массовая переиндексация всех продуктов
        """
        await self.initialize()
        
        result = {
            "success": False,
            "products_processed": 0,
            "total_files": 0,
            "total_chunks": 0,
            "errors": [],
            "processing_time": 0
        }
        
        start_time = datetime.now()
        
        try:
            # Получаем все продукты с файлами для очистки старых эмбеддингов
            from src.database.models import Product
            query_clear = select(Product.id).distinct()
            result_clear = await session.execute(query_clear)
            product_ids_to_clear = [row[0] for row in result_clear.all()]
            
            # Удаляем старые эмбеддинги всех продуктов
            for pid in product_ids_to_clear:
                await self.embedding_service.delete_product_embeddings(pid)
            
            logger.info(f"[AutoChunking] Очищены эмбеддинги для {len(product_ids_to_clear)} продуктов")
            
            # Получаем все продукты с файлами
            query = select(Product.id, Product.name).distinct()
            result_products = await session.execute(query)
            products = result_products.all()
            
            logger.info(f"[AutoChunking] Начинаем массовую переиндексацию {len(products)} продуктов")
            
            for product_id, product_name in products:
                logger.info(f"[AutoChunking] Обрабатываем продукт {product_id}: {product_name}")
                
                product_result = await self.reindex_product(
                    product_id=product_id,
                    product_name=product_name,
                    session=session
                )
                
                if product_result["success"]:
                    result["products_processed"] += 1
                    result["total_files"] += product_result["files_processed"]
                    result["total_chunks"] += product_result["total_chunks"]
                else:
                    result["errors"].extend(product_result.get("errors", []))
            
            result["success"] = result["products_processed"] > 0
            
        except Exception as e:
            logger.error(f"[AutoChunking] Ошибка при массовой переиндексации: {e}")
            result["errors"].append(str(e))
        
        finally:
            end_time = datetime.now()
            result["processing_time"] = (end_time - start_time).total_seconds()
        
        return result
    
    async def _extract_text_from_file(self, file_path: str, max_pages: int = 15) -> str:
        """Извлечение текста из PDF файла"""
        try:
            import pdfplumber
            with pdfplumber.open(file_path) as pdf:
                pages_text = []
                
                pages_to_process = pdf.pages[:max_pages] if max_pages else pdf.pages
                
                for page in pages_to_process:
                    page_text = page.extract_text()
                    if page_text:
                        pages_text.append(page_text)
                
                return '\n\n'.join(pages_text)
        except Exception as e:
            logger.error(f"Ошибка при извлечении текста из {file_path}: {e}")
            return ""
    
    def _get_absolute_file_path(self, relative_path: str) -> str:
        """Преобразует относительный путь в абсолютный"""
        from src.config.settings import DOWNLOAD_FOLDER
        if os.path.isabs(relative_path):
            return relative_path
        return os.path.join(DOWNLOAD_FOLDER, relative_path)
    
    async def get_statistics(self) -> Dict[str, Any]:
        """Получить статистику по индексации"""
        await self.initialize()
        return await self.embedding_service.get_statistics()
