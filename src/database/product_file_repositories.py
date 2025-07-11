from typing import Optional, List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.database.models import ProductFile, Product, ProductSphere, Category, Sphere

class ProductFileRepository:
    """
    Репозиторий для работы с файлами продуктов
    """
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_main_image(self, product_id: int) -> Optional[str]:
        """
        Получение главного изображения для продукта.
        Возвращает только изображения с ordering = 0 (специально помеченные как главные)
        """
        result = await self.session.execute(
            select(ProductFile.file_id)
            .where(
                ProductFile.product_id == product_id, 
                ProductFile.kind == "image", 
                ProductFile.is_deleted == False,
                ProductFile.ordering == 0,
                ProductFile.title.is_(None)  # Главные изображения не имеют title
            )
            .limit(1)
        )
        return result.scalar()

    async def get_documents(self, product_id: int) -> List[ProductFile]:
        """
        Получение всех документов, связанных с продуктом.
        """
        # Типы документов
        doc_types = ['document', 'pdf', 'word', 'excel', 'presentation', 'archive', 'other']
        
        result = await self.session.execute(
            select(ProductFile)
            .where(
                ProductFile.product_id == product_id, 
                ProductFile.kind.in_(doc_types), 
                ProductFile.is_deleted == False
            )
            .order_by(ProductFile.ordering)
        )
        return list(result.scalars().all())

    async def get_media_files(self, product_id: int) -> List[ProductFile]:
        """
        Получение всех медиа файлов (изображения и видео), связанных с продуктом.
        Исключает главные изображения (те которые без title).
        """
        # Типы медиа файлов
        media_types = ['image', 'video']
        
        result = await self.session.execute(
            select(ProductFile)
            .where(
                ProductFile.product_id == product_id, 
                ProductFile.kind.in_(media_types), 
                ProductFile.is_deleted == False,
                ProductFile.title.is_not(None)  # Только файлы с названием
            )
            .order_by(ProductFile.ordering)
        )
        return list(result.scalars().all())

    async def get_all_files(self, product_id: int) -> List[ProductFile]:
        """
        Получение всех файлов продукта, которые имеют названия (исключая главные изображения).
        """
        result = await self.session.execute(
            select(ProductFile)
            .where(
                ProductFile.product_id == product_id, 
                ProductFile.is_deleted == False,
                ProductFile.title.is_not(None)  # Только файлы с названием
            )
            .order_by(ProductFile.ordering)
        )
        return list(result.scalars().all())

    async def add_file(self, product_id: int, file_id: str, kind: str, ordering: int = 0, 
                      title: Optional[str] = None, file_size: Optional[int] = None, mime_type: Optional[str] = None, 
                      original_filename: Optional[str] = None, uploaded_by: Optional[int] = None) -> ProductFile:
        """Добавление файла к продукту"""
        from datetime import datetime
        
        product_file = ProductFile(
            product_id=product_id,
            file_id=file_id,
            kind=kind,
            ordering=ordering,
            title=title,
            file_size=file_size,
            mime_type=mime_type,
            original_filename=original_filename,
            uploaded_by=uploaded_by,
            uploaded_at=datetime.now()
        )
        self.session.add(product_file)
        await self.session.commit()
        await self.session.refresh(product_file)
        return product_file
