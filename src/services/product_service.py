from typing import List, Optional, Dict, Tuple, Any
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.repositories import ProductRepository
from src.database.product_file_repositories import ProductFileRepository
from src.database.models import Product, Category,ProductSphere, Sphere
from src.core.utils import split_advantages

class CategoryService:
    """
    Сервис категории продукции
    """
    def __init__(self, session: AsyncSession):
        self.session = session
        self.product_repo = ProductRepository(session)  # ИСПРАВЛЕНО - используем правильный репозиторий
        self.file_repo = ProductFileRepository(session)
    
    async def get_all_categories(self) -> List[Category]:
        """
        Getting all products categories
        """
        from sqlalchemy import select
        query = select(Category)
        result = await self.session.execute(query)
        return list(result.scalars().all())


class ProductService:
    """
    Сервис для продукции
    """
    def __init__(self, session: AsyncSession):
        self.session = session
        self.product_repo = ProductRepository(session)  # Используем репозиторий с методом get_by_category
        self.file_repo = ProductFileRepository(session)  # Репозиторий для работы с файлами
    
    async def get_product_by_id(self, product_id: int) -> Optional[Dict[str, Any]]:
        """
        Получаем продукт по его ID с полной информацией
        """
        product = await self.product_repo.get_by_id(product_id)
        if not product:
            return None

        # файлы
        main_image = await self.file_repo.get_main_image(product_id)
        documents = await self.file_repo.get_documents(product_id)
        media_files = await self.file_repo.get_media_files(product_id)
        all_files = await self.file_repo.get_all_files(product_id)
        
        # Получаем категорию
        from sqlalchemy import select
        category_query = select(Category).where(Category.id == product.category_id)
        category_result = await self.session.execute(category_query)
        category = category_result.scalars().first()
        
        # Сферы
        spheres_query = select(ProductSphere).where(ProductSphere.product_id == product_id)
        result = await self.session.execute(spheres_query)
        spheres = result.scalars().all()

        sphere_product_name = None
        if spheres:
            first_sphere = spheres[0]
            if hasattr(first_sphere, 'product_name') and first_sphere.product_name is not None:
                sphere_product_name = str(first_sphere.product_name)

        # Собираем объект
        product_info = {
            "id": product.id,
            "name": sphere_product_name or product.name or "Без Названия",
            "description": None,
            "category": category,
            "main_image": main_image,
            "documents": documents,
            "media_files": media_files,
            "all_files": all_files,
            "spheres": []
        }

        descriptions = []
        for sphere in spheres:
            advantages = split_advantages(str(sphere.advantages))
            sphere_desc = str(sphere.description)
            if sphere_desc and sphere_desc.strip() and sphere_desc.lower() not in ['none', 'null', '-']:
                descriptions.append(sphere_desc)
            
            product_info["spheres"].append({
                "id": sphere.id,
                "name": sphere.sphere_name,
                "description": sphere.description,
                "advantages": advantages,
                "notes": sphere.notes,
                "package": sphere.package,
            })

        if descriptions:
            product_info["description"] = descriptions[0]
        
        return product_info
        
    async def get_products_by_category(self, category_id: int) -> List[Tuple[Product, Optional[str]]]:
        """
        Получаем продукты по категории с изображениями
        """
        # Вызов метода get_by_category из ProductRepository
        products = await self.product_repo.get_by_category(category_id)
        results = []
        
        # Добавляем изображения для каждого продукта
        for product in products:
            main_image = await self.file_repo.get_main_image(getattr(product, 'id'))
            results.append((product, main_image))
        
        return results

    async def update_product_field(self, product_id: int, field: str, value: str) -> bool:
        """
        Обновляет конкретное поле продукта
        
        Args:
            product_id: ID продукта
            field: Название поля для обновления  
            value: Новое значение
            
        Returns:
            True если обновление прошло успешно, False иначе
        """
        # Поля из таблицы Product  
        product_fields = ['name']  # убрали short_desc - не редактируем
        # Поля из таблицы ProductSphere
        product_sphere_fields = ['description', 'advantages', 'notes', 'package']
        
        if field in product_fields:
            return await self.product_repo.update_product_field(product_id, field, value)
        elif field in product_sphere_fields:
            return await self.product_repo.update_product_sphere_field(product_id, field, value)
        else:
            return False

class SphereService:
    """
    Service for working with spheres
    """
    def __init__(self, session: AsyncSession):
        self.session = session
        self.product_repo = ProductRepository(session)
        self.file_repo = ProductFileRepository(session)
    
    async def get_all_spheres(self) -> List[Sphere]:
        """
        Getting all spheres
        """
        from sqlalchemy import select
        query = select(Sphere)
        result = await self.session.execute(query)
        return list(result.scalars().all())
    
    async def get_products_by_sphere(self, sphere_id: int) -> List[Tuple[Product, Optional[str]]]:
        """
        Get products by sphere with images
        """
        from sqlalchemy import select
        
        # Пробуем JOIN запрос
        query = select(Product).join(ProductSphere).where(
            ProductSphere.sphere_id == sphere_id,
            Product.is_deleted == False
        )
        result = await self.session.execute(query)
        products = result.scalars().all()
        
        # Если JOIN не дал результатов, пробуем альтернативный метод
        if not products:
            return await self.get_products_by_sphere_alternative(sphere_id)
        
        results = []
        for product in products:
            main_image = await self.file_repo.get_main_image(getattr(product, 'id'))
            results.append((product, main_image))
        
        return results
    
    async def get_products_by_sphere_alternative(self, sphere_id: int) -> List[Tuple[Product, Optional[str]]]:
        """
        Alternative method to get products by sphere (without JOIN)
        """
        from sqlalchemy import select
        
        # Сначала получаем все ProductSphere для данной сферы
        sphere_query = select(ProductSphere).where(ProductSphere.sphere_id == sphere_id)
        result = await self.session.execute(sphere_query)
        product_spheres = result.scalars().all()
        
        results = []
        for product_sphere in product_spheres:
            # Получаем продукт по ID
            product = await self.product_repo.get_by_id(getattr(product_sphere, 'product_id'))
            if product and not getattr(product, 'is_deleted', True):
                main_image = await self.file_repo.get_main_image(getattr(product, 'id'))
                results.append((product, main_image))
        
        return results
