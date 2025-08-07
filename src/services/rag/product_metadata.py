import os
import logging
from typing import Dict, Any, Optional

from src.services.rag.pdf_extractor import extract_text_from_pdf

logger = logging.getLogger(__name__)

async def get_product_metadata(embedding_service, product_id: int) -> Dict[str, Any]:
    """
    Получение метаданных для продукта из ChromaDB или базы данных.
    """
    metadata = {
        "product_id": product_id,
        "name": f"Продукт {product_id}",
        "text": "",
        "file_path": None
    }
    
    try:
        # Сначала проверяем наличие документа в ChromaDB
        if hasattr(embedding_service, 'collection') and embedding_service.collection is not None:
            try:
                entries = embedding_service.collection.get(
                    ids=[str(product_id)],
                    include=["metadatas", "documents"]
                )
                
                if entries and 'documents' in entries and entries['documents']:
                    metadata["text"] = entries['documents'][0]
                    
                    # Если у нас есть метаданные в ChromaDB, используем их
                    if entries and 'metadatas' in entries and entries['metadatas']:
                        chroma_metadata = entries['metadatas'][0]
                        if chroma_metadata:
                            if 'product_name' in chroma_metadata:
                                metadata["name"] = chroma_metadata['product_name']
                            if 'file_path' in chroma_metadata:
                                metadata["file_path"] = chroma_metadata['file_path']
                            if 'description' in chroma_metadata:
                                metadata["description"] = chroma_metadata['description']
            except Exception as e:
                logger.warning(f"Не удалось получить данные из ChromaDB для продукта {product_id}: {e}")

        # Если текст не был получен из ChromaDB или мы хотим дополнительные метаданные из БД
        if not metadata["text"] or metadata["name"] == f"Продукт {product_id}":
            try:
                # Получаем данные о продукте из базы данных
                from sqlalchemy import select
                from sqlalchemy.ext.asyncio import AsyncSession
                from sqlalchemy.ext.asyncio import create_async_engine
                from src.database.models import Product, ProductFile
                from src.config.settings import settings
                
                # Создаем временное соединение с БД для получения информации о продукте
                engine = create_async_engine(settings.database_url)
                async with AsyncSession(engine) as session:
                    # Запрос на получение названия продукта
                    query = select(Product).where(Product.id == product_id)
                    result = await session.execute(query)
                    product = result.scalar_one_or_none()
                    
                    if product:
                        metadata["name"] = getattr(product, 'name', f"Продукт {product_id}")
                        metadata["description"] = getattr(product, 'description', "")
                        
                        # Получаем информацию о PDF файлах продукта
                        if not metadata["file_path"]:
                            query = select(ProductFile).where(
                                ProductFile.product_id == product_id,
                                ProductFile.kind == 'pdf',
                                ProductFile.is_deleted == False
                            )
                            result = await session.execute(query)
                            product_file = result.scalar_one_or_none()
                            
                            if product_file:
                                local_path = getattr(product_file, 'local_path', None)
                                if local_path and isinstance(local_path, str):
                                    metadata["file_path"] = local_path
                                    
                                    # Если у нас нет текста из ChromaDB, но есть путь к файлу,
                                    # можем попытаться извлечь текст прямо из PDF
                                    if not metadata["text"] and os.path.exists(local_path):
                                        try:
                                            extracted_text = await extract_text_from_pdf(
                                                local_path,
                                                max_pages=5,
                                                max_length=10000
                                            )
                                            if extracted_text:
                                                metadata["text"] = extracted_text
                                                logger.info(f"Извлечен текст из PDF для продукта {product_id}")
                                        except Exception as e:
                                            logger.warning(f"Ошибка при извлечении текста из PDF: {e}")
            except Exception as e:
                logger.warning(f"Ошибка при получении данных о продукте из БД: {e}")
    
    except Exception as e:
        logger.error(f"Ошибка при получении метаданных для продукта {product_id}: {e}")
    
    return metadata
