from typing import List, Optional, Dict, Tuple, Any
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.repositories import ProductRepository, ProductFileRepository
from src.database.models import Product, Category,ProductSphere, Sphere
from src.core.utils import split_advantages

class CategoryService:
    """
    Service for working with catogories
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
    Serivce for working with products  
    """
    def __init__(self, session: AsyncSession):
        self.session = session
        self.product_repo = ProductRepository(session)  # ИСПРАВЛЕНО - правильный репозиторий для продуктов
        self.file_repo = ProductFileRepository(session)  # ИСПРАВЛЕНО - правильный репозиторий для файлов
    
    async def get_product_by_id(self, product_id: int) -> Optional[Dict[str, Any]]:
        """
        get product by id with full information
        """
        product = await self.product_repo.get_by_id(product_id)
        if not product:
            return None

        #files 
        main_image = await self.file_repo.get_main_image(product_id)
        documents = await self.file_repo.get_documents(product_id)
        
        # Получаем категорию отдельным запросом
        from sqlalchemy import select
        category_query = select(Category).where(Category.id == product.category_id)
        category_result = await self.session.execute(category_query)
        category = category_result.scalars().first()
        
        #spheres
        spheres_query = select(ProductSphere).where(
            ProductSphere.product_id == product_id
        )
        result = await self.session.execute(spheres_query)
        spheres = result.scalars().all()

        # building object
        #TODO: FIX container
        product_info = {
            "id": product.id,
            "name": product.name,
            "description": None,  # Будем брать из product_sphere.description
            "category": category,  # Используем отдельно загруженную категорию
            "main_image": main_image,
            "documents": documents,
            "spheres": []
        }

        # Собираем все описания из сфер
        descriptions = []
        for sphere in spheres:
            advantages = split_advantages(str(sphere.advantages))
            
            # Добавляем описание из sphere в общий список
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
        
        # Устанавливаем описание продукта из первой сферы
        if descriptions:
            product_info["description"] = descriptions[0]  # Берем первое описание
        return product_info
        
    async def get_products_by_category(self, category_id: int) -> List[Tuple[Product, Optional[str]]]:
        """
        Get prodcuts by category with images
        """
        products = await self.product_repo.get_by_category(category_id)
        results = []
        for product in products:
            main_image = await self.file_repo.get_main_image(getattr(product, 'id'))
            results.append((product,  main_image))
        return results


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
