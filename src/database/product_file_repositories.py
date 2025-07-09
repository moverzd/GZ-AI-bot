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
        """
        result = await self.session.execute(
            select(ProductFile.file_id)
            .where(ProductFile.product_id == product_id, ProductFile.kind == "image", ProductFile.is_deleted == False)
            .order_by(ProductFile.ordering)  # Первое изображение = главное
            .limit(1)
        )
        return result.scalar()

    async def get_documents(self, product_id: int) -> List[ProductFile]:
        """
        Получение всех документов, связанных с продуктом.
        """
        result = await self.session.execute(
            select(ProductFile)
            .where(ProductFile.product_id == product_id, ProductFile.kind == "doc", ProductFile.is_deleted == False)
            .order_by(ProductFile.ordering)
        )
        return result.scalars().all()

    async def add_file(self, product_id: int, file_id: str, kind: str, ordering: int = 0) -> ProductFile:
        """Добавление файла к продукту"""
        product_file = ProductFile(
            product_id=product_id,
            file_id=file_id,
            kind=kind,
            ordering=ordering
        )
        self.session.add(product_file)
        await self.session.commit()
        await self.session.refresh(product_file)
        return product_file
