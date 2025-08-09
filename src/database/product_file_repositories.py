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
        Возвращает изображение с флагом is_main_image = True
        """
        result = await self.session.execute(
            select(ProductFile.file_id)
            .where(
                ProductFile.product_id == product_id, 
                ProductFile.kind == "image", 
                ProductFile.is_deleted == False,
                ProductFile.is_main_image == True
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
        Исключает главные изображения.
        """
        # Типы медиа файлов
        media_types = ['image', 'video']
        
        result = await self.session.execute(
            select(ProductFile)
            .where(
                ProductFile.product_id == product_id, 
                ProductFile.kind.in_(media_types), 
                ProductFile.is_deleted == False,
                ProductFile.is_main_image == False  # Исключаем главные изображения
            )
            .order_by(ProductFile.ordering)
        )
        return list(result.scalars().all())

    async def get_all_files(self, product_id: int) -> List[ProductFile]:
        """
        Получение всех файлов продукта, исключая главные изображения.
        """
        result = await self.session.execute(
            select(ProductFile)
            .where(
                ProductFile.product_id == product_id, 
                ProductFile.is_deleted == False,
                ProductFile.is_main_image == False  # Исключаем главные изображения
            )
            .order_by(ProductFile.ordering)
        )
        return list(result.scalars().all())

    async def add_file(self, product_id: int, file_id: str, kind: str, ordering: int = 0, 
                      title: Optional[str] = None, file_size: Optional[int] = None, mime_type: Optional[str] = None, 
                      original_filename: Optional[str] = None, uploaded_by: Optional[int] = None, 
                      local_path: Optional[str] = None, is_main_image: bool = False) -> ProductFile:
        """Добавление файла к продукту"""
        from datetime import datetime
        from sqlalchemy import func
        
        # Если ordering не задан явно или равен 0, автоматически определяем следующий доступный номер
        if ordering <= 0:
            # Находим максимальный ordering для данного продукта и типа файла
            result = await self.session.execute(
                select(func.max(ProductFile.ordering))
                .where(
                    ProductFile.product_id == product_id,
                    ProductFile.kind == kind,
                    ProductFile.is_deleted == False
                )
            )
            max_ordering = result.scalar()
            ordering = (max_ordering + 1) if max_ordering is not None else 0
        
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
            local_path=local_path,
            is_main_image=is_main_image,
            uploaded_at=datetime.now()
        )
        self.session.add(product_file)
        await self.session.commit()
        await self.session.refresh(product_file)
        return product_file
