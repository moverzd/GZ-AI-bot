from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.product_file_repositories import ProductFileRepository
from src.database.models import ProductFile

class FileService:
    """
    Сервис менеджмента файлов
    """
    def __init__(self, session: AsyncSession):
        self.session = session
        self.file_repo = ProductFileRepository(session)

    async def save_product_image(self, product_id: int, file_id: str, is_main: bool = False) -> ProductFile:
        """
        Сохранить фото продукта
        """
        ordering=0 if is_main else 1
        return await self.file_repo.add_file(
            product_id = product_id,
            file_id = file_id,
            kind = "image",
            ordering = ordering
        )

    async def save_product_document(self, product_id: int, file_id: str, title: Optional[str] = None) -> ProductFile:
        """
        Сохранить документацию для продукта 
        """
        return await self.file_repo.add_file(
            product_id = product_id,
            file_id = file_id,
            kind = "document"
            title = title
        )
    
    async def get_product_files(self, product_id: int, file_type: Optional[str] = None) -> List[ProductFile]:
        """
        получение файлов продуктов
        """
        from sqlalchemy import select
        
        query = select(ProductFile).where(
            ProductFile.product_id == product_id,
            ProductFile.is_deleted == False
        )
        
        if file_type:
            query = query.where(ProductFile.kind == file_type)
        
        result = await self.session.execute(query.order_by(ProductFile.ordering))
        return result.scalars().all()
