import re
from typing import List, Optional
from sqlalchemy import select, func, update, or_
from sqlalchemy.ext.asyncio import AsyncSession
from src.database.models import ProductFile, Product, ProductSphere, Category, Sphere

class ProductRepository:
    """
    Репозиторий для работы с продуктами.
    """
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def get_by_id(self, product_id: int) -> Optional[Product]:
        """
        Возвращает продукт по его ID.
        """
        result = await self.session.execute(
            select(Product).where(Product.id == product_id, Product.is_deleted == False)
        )
        return result.scalars().first()
    
    async def get_all(self) -> List[Product]:
        """
        Возвращает все продукты.
        """
        result = await self.session.execute(
            select(Product).where(Product.is_deleted == False)
        )
        return list(result.scalars().all())
    
    async def get_by_category(self, category_id: int) -> List[Product]:
        """
        Поиск продуктов по категории.
        """
        result = await self.session.execute(
            select(Product).where(Product.category_id == category_id, Product.is_deleted == False)
        )
        return list(result.scalars().all())
    
    async def search_by_conditions(self, conditions: List) -> List[Product]:
        """
        Поиск продуктов по заданным условиям.
        """
        result = await self.session.execute(
            select(Product).where(
                or_(*conditions),
                Product.is_deleted == False
            )
        )
        return list(result.scalars().all())
    
    async def soft_delete_product(self, product_id: int) -> None:
        """
        Soft delete продукт - меняем флаг is_deleted на True
        """
        await self.session.execute(
            update(Product)
            .where(Product.id == product_id)
            .values(is_deleted=True)
        )
        await self.session.commit()

    async def update_product_field(self, product_id: int, field: str, value: str) -> bool:
        """
        Обновляет конкретное поле продукта
        """
        try:
            # Проверяем, что продукт существует
            product = await self.get_by_id(product_id)
            if not product:
                return False
            
            # Проверяем, что поле существует в модели Product
            allowed_fields = ['name']  # убрали short_desc - не редактируем
            if field not in allowed_fields:
                return False
            
            # Обновляем поле
            await self.session.execute(
                update(Product)
                .where(Product.id == product_id)
                .values(**{field: value})
            )
            await self.session.commit()
            return True
        except Exception:
            await self.session.rollback()
            return False

    async def get_product_sphere_by_product_id(self, product_id: int) -> Optional[ProductSphere]:
        """
        Возвращает первую запись ProductSphere для продукта.
        """
        result = await self.session.execute(
            select(ProductSphere).where(ProductSphere.product_id == product_id)
        )
        return result.scalars().first()
    
    async def update_product_sphere_field(self, product_id: int, field: str, value: str) -> bool:
        """
        Обновляет конкретное поле ProductSphere
        
        Args:
            product_id: ID продукта
            field: Название поля для обновления
            value: Новое значение
            
        Returns:
            True если обновление прошло успешно, False иначе
        """
        try:
            # Проверяем, что запись существует
            product_sphere = await self.get_product_sphere_by_product_id(product_id)
            
            if not product_sphere:
                # Если записи нет, возвращаем False с логированием
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"Продукт {product_id} не имеет записи в products_sphere для поля {field}")
                return False
            
            # Проверяем, что поле существует в модели ProductSphere
            allowed_fields = ['description', 'advantages', 'notes']
            if field not in allowed_fields:
                return False
            
            # Обновляем поле
            await self.session.execute(
                update(ProductSphere)
                .where(ProductSphere.product_id == product_id)
                .values(**{field: value})
            )
            await self.session.commit()
            return True
        except Exception:
            await self.session.rollback()
            return False


    async def sync_product_name_to_spheres(self, product_id: int, new_name: str) -> bool:
        """
        Синхронизация названия продукта во все связанные product_spheres
        """
        try:
            await self.session.execute(
                update(ProductSphere).where(ProductSphere.product_id == product_id)
                .values(product_name = new_name)
            )
            await self.session.commit()
            return True
        except Exception as e:
            await self.session.rollback()
            return False