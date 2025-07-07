from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession

from src.services.file_service import FileService
from src.database.models import ProductFile

class MediaService:
    """
    Расширенный сервис для работы с медиа-файлами продуктов
    """
    def __init__(self, session: AsyncSession):
        self.session = session
        self.file_service = FileService(session)
    
    async def get_product_media(self, product_id: int) -> Dict[str, Any]:
        """
        Получение всех медиа-файлов продукта
        
        Args:
            product_id: ID продукта
            
        Returns:
            Словарь с информацией о медиа-файлах
        """
        # Получаем все файлы продукта
        files = await self.file_service.get_product_files(product_id)
        
        # Разделяем по типам
        images = []
        documents = []
        videos = []
        
        for file in files:
            if file.kind == 'image':
                images.append({
                    'id': file.id,
                    'file_id': file.file_id,
                    'ordering': file.ordering
                })
            elif file.kind == 'document':
                documents.append({
                    'id': file.id,
                    'file_id': file.file_id,
                    'title': file.title,
                    'ordering': file.ordering
                })
            elif file.kind == 'video':
                videos.append({
                    'id': file.id,
                    'file_id': file.file_id,
                    'title': file.title,
                    'ordering': file.ordering
                })
        
        # Сортируем по ordering
        images.sort(key=lambda x: x['ordering'])
        documents.sort(key=lambda x: x['ordering'])
        videos.sort(key=lambda x: x['ordering'])
        
        return {
            'images': images,
            'documents': documents,
            'videos': videos,
            'main_image': images[0]['file_id'] if images else None
        }
    
    async def set_main_image(self, product_id: int, file_id: str) -> bool:
        """
        Установка основного изображения продукта
        
        Args:
            product_id: ID продукта
            file_id: ID файла в Telegram
            
        Returns:
            True в случае успеха, иначе False
        """
        # Находим все текущие изображения продукта
        from sqlalchemy import select, update
        
        # Сбрасываем ordering для всех изображений
        await self.session.execute(
            update(ProductFile)
            .where(
                ProductFile.product_id == product_id,
                ProductFile.kind == 'image',
                ProductFile.is_deleted == False
            )
            .values(ordering=1)
        )
        
        # Находим нужное изображение и делаем его основным
        await self.session.execute(
            update(ProductFile)
            .where(
                ProductFile.product_id == product_id,
                ProductFile.file_id == file_id,
                ProductFile.kind == 'image',
                ProductFile.is_deleted == False
            )
            .values(ordering=0)
        )
        
        await self.session.commit()
        return True