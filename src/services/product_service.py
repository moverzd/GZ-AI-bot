from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from src.database.repositories import ProductRepository
from src.database.product_file_repositories import ProductFileRepository
from src.database.models import Product, Category, ProductSphere, Sphere
from src.services.search.semantic_search import SemanticSearchService

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
            "name": sphere_product_name if sphere_product_name else product.name,
            "category": category.name if category else None,
            "category_id": product.category_id,
            "main_image": main_image,
            "documents": documents,
            "media_files": media_files,
            "all_files": all_files,
            "spheres": self._format_spheres(spheres),
            "spheres_info": [self._sphere_to_dict(sphere) for sphere in spheres],
            "created_at": product.created_at,
            "updated_at": product.updated_at,
            "is_deleted": product.is_deleted
        }

        return product_info
    
    def _format_spheres(self, spheres: List[ProductSphere]) -> List[Dict[str, Any]]:
        """
        Форматирует список сфер применения для отображения
        """
        formatted_spheres = []
        
        for sphere_link in spheres:
            formatted_sphere = {
                "id": sphere_link.sphere_id,
                "name": sphere_link.sphere_name,
                "product_name": sphere_link.product_name
            }
            formatted_spheres.append(formatted_sphere)
        
        return formatted_spheres
    
    def _sphere_to_dict(self, sphere: ProductSphere) -> Dict[str, Any]:
        """
        Конвертирует объект ProductSphere в словарь
        """
        return {
            "id": sphere.id,
            "sphere_id": sphere.sphere_id,
            "sphere_name": sphere.sphere_name,
            "product_name": sphere.product_name,
            "description": sphere.description,
            "advantages": sphere.advantages,
            "notes": sphere.notes
        }

    async def get_all_products(self) -> List[Dict[str, Any]]:
        """
        Получаем все продукты
        """
        products = await self.product_repo.get_all()
        return [await self._product_to_dict(product) for product in products]

    async def _product_to_dict(self, product: Product) -> Dict[str, Any]:
        """
        Конвертирует объект Product в словарь
        """
        # Получаем категорию
        category_query = select(Category).where(Category.id == product.category_id)
        category_result = await self.session.execute(category_query)
        category = category_result.scalars().first()

        # Получаем основную картинку
        main_image = await self.file_repo.get_main_image(product.id)

        return {
            "id": product.id,
            "name": product.name,
            "category": category.name if category else None,
            "category_id": product.category_id,
            "main_image": main_image,
            "created_at": product.created_at,
            "updated_at": product.updated_at,
            "is_deleted": product.is_deleted
        }

    async def search_products(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Поиск продуктов по названию
        """
        products = await self.product_repo.search_by_name(query, limit)
        return [await self._product_to_dict(product) for product in products]

    async def get_products_by_category(self, category_id: int) -> List[Dict[str, Any]]:
        """
        Получаем продукты по категории
        """
        products = await self.product_repo.get_by_category(category_id)
        return [await self._product_to_dict(product) for product in products]

    async def get_products_by_sphere(self, sphere_id: int) -> List[Dict[str, Any]]:
        """
        Получаем продукты по сфере применения
        """
        # Получаем связи продуктов со сферами
        spheres_query = select(ProductSphere).where(ProductSphere.sphere_id == sphere_id)
        result = await self.session.execute(spheres_query)
        product_spheres = result.scalars().all()

        products_info = []
        for product_sphere in product_spheres:
            product = await self.product_repo.get_by_id(product_sphere.product_id)
            if product and not product.is_deleted:
                product_dict = await self._product_to_dict(product)
                
                # Добавляем информацию из связи со сферой
                product_dict.update({
                    "sphere_id": product_sphere.sphere_id,
                    "sphere_name": product_sphere.sphere_name,
                    "product_name": product_sphere.product_name,
                    "description": product_sphere.description,
                    "advantages": product_sphere.advantages,
                    "notes": product_sphere.notes
                })
                
                products_info.append(product_dict)

        return products_info

    async def update_product_field(self, product_id: int, field: str, value: str) -> bool:
        """
        Обновляет поле продукта в зависимости от типа поля
        """
        try:
            if field == "name":
                # Обновляем название продукта
                success = await self.product_repo.update_product_field(product_id, field, value)
                if not success:
                    return False
                
                # Синхронизируем название в ProductSphere записях
                await self.product_repo.sync_product_name_to_spheres(product_id, value)
            elif field in ["description", "advantages", "notes"]:
                # Обновляем поля в ProductSphere через репозиторий
                success = await self.product_repo.update_product_sphere_field(product_id, field, value)
                if not success:
                    return False
            else:
                return False

            # Обновляем эмбеддинги после успешного изменения
            try:
                from src.services.auto_chunking_service import AutoChunkingService
                
                # Получаем актуальное название продукта
                product_info = await self.get_product_by_id(product_id)
                product_name = product_info.get('name', f'Product_{product_id}') if product_info else f'Product_{product_id}'
                
                auto_chunking = AutoChunkingService()
                await auto_chunking.reindex_product(product_id, product_name, self.session)
                logger.info(f"Эмбеддинги для продукта {product_id} обновлены после изменения поля {field}")
            except Exception as e:
                logger.warning(f"Не удалось обновить эмбеддинги для продукта {product_id}: {e}")
                # Не прерываем выполнение, так как основное обновление уже прошло успешно

            return True
        except Exception as e:
            logger.error(f"Ошибка обновления поля {field} продукта {product_id}: {e}")
            await self.session.rollback()
            return False

    async def get_categories(self) -> List[Dict[str, Any]]:
        """
        Получаем все категории
        """
        query = select(Category)
        result = await self.session.execute(query)
        categories = result.scalars().all()
        
        return [{"id": cat.id, "name": cat.name} for cat in categories]

    async def get_spheres(self) -> List[Dict[str, Any]]:
        """
        Получаем все сферы применения
        """
        query = select(Sphere)
        result = await self.session.execute(query)
        spheres = result.scalars().all()
        
        return [{"id": sphere.id, "name": sphere.name} for sphere in spheres]

    async def get_product_text_for_indexing(self, product_id: int) -> str:
        """
        Получает текстовое представление продукта для индексации в векторной базе
        """
        try:
            # Получаем основную информацию о продукте
            product = await self.product_repo.get_by_id(product_id)
            if not product:
                return ""

            # Получаем категорию
            category_query = select(Category).where(Category.id == product.category_id)
            category_result = await self.session.execute(category_query)
            category = category_result.scalars().first()

            # Получаем сферы применения
            spheres_query = select(ProductSphere).where(ProductSphere.product_id == product_id)
            result = await self.session.execute(spheres_query)
            spheres = result.scalars().all()

            # Формируем текстовое представление
            text_parts = []
            
            # Основная информация
            if spheres and len(spheres) > 0 and spheres[0].product_name is not None and str(spheres[0].product_name).strip():
                text_parts.append(f"Название продукта: {spheres[0].product_name}")
            else:
                text_parts.append(f"Название продукта: {product.name}")
            
            if category:
                text_parts.append(f"Категория: {category.name}")

            # Информация по сферам применения
            for sphere in spheres:
                if sphere.sphere_name is not None and str(sphere.sphere_name).strip():
                    text_parts.append(f"Сфера применения: {sphere.sphere_name}")
                
                if sphere.description is not None and str(sphere.description).strip():
                    text_parts.append(f"Описание: {sphere.description}")
                
                if sphere.advantages is not None and str(sphere.advantages).strip():
                    text_parts.append(f"Преимущества: {sphere.advantages}")
                
                if sphere.notes is not None and str(sphere.notes).strip():
                    text_parts.append(f"Примечания: {sphere.notes}")

            return "\n".join(text_parts)

        except Exception as e:
            logger.error(f"Ошибка получения текста для индексации продукта {product_id}: {e}")
            return ""
