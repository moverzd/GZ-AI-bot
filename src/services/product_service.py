from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from src.database.repositories import ProductRepository
from src.database.product_file_repositories import ProductFileRepository
from src.database.models import Product, Category, ProductSphere, Sphere
from src.services.search.semantic_search import SemanticSearchService
from src.core.utils import split_advantages

import logging
logger = logging.getLogger(__name__)

class ProductService:
    """
    Сервис для продукции
    """
    def __init__(self, session: AsyncSession):
        self.session = session
        self.product_repo = ProductRepository(session)  # Репозиторий для работы с продуктами
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
            "spheres": [],
            "spheres_info": []  # Добавляем для совместимости с handler
        }

        descriptions = []
        for sphere in spheres:
            advantages = split_advantages(str(sphere.advantages))
            sphere_desc = str(sphere.description)
            if sphere_desc and sphere_desc.strip() and sphere_desc.lower() not in ['none', 'null', '-']:
                descriptions.append(sphere_desc)
            
            sphere_data = {
                "id": sphere.id,
                "name": sphere.sphere_name,
                "description": sphere.description,
                "advantages": advantages,
                "notes": sphere.notes,
                "package": sphere.package,
            }
            
            product_info["spheres"].append(sphere_data)
            product_info["spheres_info"].append(sphere_data)  # Дублируем для совместимости

        if descriptions:
            product_info["description"] = descriptions[0]
        
        return product_info
        
    async def get_products_by_category(self, category_id: int) -> List[Tuple[Product, Optional[str]]]:
        """
        Получаем продукты по категории с изображениями
        """
        products = await self.product_repo.get_by_category(category_id)
        results = []
        
        # Добавляем изображения для каждого продукта
        for product in products:
            main_image = await self.file_repo.get_main_image(getattr(product, 'id'))
            results.append((product, main_image))
        
        return results

    async def update_product_field(self, product_id: int, field: str, value: str) -> bool:
        """
        Обновляет конкретное поле продукта и автоматически переиндексирует его
        """
        import logging
        logger = logging.getLogger(__name__)
        
        product_fields = ['name']
        product_sphere_fields = ['description', 'advantages', 'notes', 'package']
        
        result = False
        
        if field in product_fields:
            result = await self.product_repo.update_product_field(product_id, field, value)
            if field == 'name' and result:
                await self.product_repo.sync_product_name_to_spheres(product_id, value)
        elif field in product_sphere_fields:
            result = await self.product_repo.update_product_sphere_field(product_id, field, value)
        else:
            return False
        
        # Автоматическая переиндексация при успешном обновлении любого поля
        if result:
            try:
                from src.services.auto_chunking_service import AutoChunkingService
                from src.database.connection import AsyncSessionLocal
                
                logger.info(f"[ProductService] Запуск автоматической переиндексации продукта {product_id} после изменения поля '{field}'")
                
                auto_chunking = AutoChunkingService()
                session = AsyncSessionLocal()
                
                try:
                    # Получаем информацию о продукте для переиндексации
                    product_info = await self.get_product_by_id(product_id)
                    if product_info:
                        reindex_result = await auto_chunking.reindex_product(
                            product_id=product_id,
                            product_name=product_info['name'],
                            session=session
                        )
                        if reindex_result["success"]:
                            logger.info(f"[ProductService] Автоматическая переиндексация продукта {product_id} завершена успешно: {reindex_result['total_chunks']} чанков")
                        else:
                            logger.warning(f"[ProductService] Ошибка автоматической переиндексации продукта {product_id}: {reindex_result.get('error', 'Неизвестная ошибка')}")
                    else:
                        logger.warning(f"[ProductService] Продукт {product_id} не найден для переиндексации")
                finally:
                    await session.close()
                    
            except Exception as e:
                logger.error(f"[ProductService] Ошибка при автоматической переиндексации продукта {product_id}: {e}")
                # Не прерываем выполнение, если переиндексация не удалась
        
        return result
    
    async def search_products_by_query(self, query: str, category_id: Optional[int] = None, limit: int = 3) -> List[Product]:
        """
        Выполняет семантический поиск продуктов по запросу.
        Создает временный поисковый сервис для выполнения запроса.
        """
        # Создаем поисковый сервис
        search_service = SemanticSearchService(self.session)
        await search_service.embedding_service.initialize()
        
        return await search_service.find_products_by_query(query, category_id, limit=limit)


