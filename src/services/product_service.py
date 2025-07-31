from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from src.database.repositories import ProductRepository
from src.database.product_file_repositories import ProductFileRepository
from src.database.models import Product, Category, ProductSphere, Sphere
from src.services.search.semantic_search import SemanticSearchService
from src.core.utils import split_advantages
from src.services.embeddings.embedding_service import EmbeddingService
from src.services.search.base import BaseSearchService


class ProductService:
    """
    Сервис для продукции
    """
    def __init__(self, session: AsyncSession, embedding_service: EmbeddingService):
        self.session = session
        self.product_repo = ProductRepository(session)  # Репозиторий для работы с продуктами
        self.file_repo = ProductFileRepository(session)  # Репозиторий для работы с файлами
        
        # Инициализация SemanticSearchService
        self.semantic_search_service = SemanticSearchService(session, embedding_service)
    
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
        Обновляет конкретное поле продукта
        """
        product_fields = ['name']
        product_sphere_fields = ['description', 'advantages', 'notes', 'package']
        
        if field in product_fields:
            result = await self.product_repo.update_product_field(product_id, field, value)
            if field == 'name' and result:
                await self.product_repo.sync_product_name_to_spheres(product_id, value)
            
            # Обновление эмбеддинга продукта
            product = await self.product_repo.get_by_id(product_id)
            if product:
                # Добавляем или обновляем эмбеддинг
                self.semantic_search_service.embedding_service.add_or_update_product_embedding(product.id, value)

            return result
        elif field in product_sphere_fields:
            return await self.product_repo.update_product_sphere_field(product_id, field, value)
        else:
            return False
    
    async def search_products_by_query(self, query: str, category_id: Optional[int] = None, limit: int = 3) -> List[Product]:
        """
        Выполняет семантический поиск продуктов по запросу.
        """
        return await self.semantic_search_service.find_products_by_query(query, category_id, limit)


class SemanticSearchService(BaseSearchService):
    """
    Сервис для выполнения семантического поиска продуктов.
    Использует embeddings и косинусное сходство для поиска похожих продуктов.
    """
    
    def __init__(self, session: AsyncSession, embedding_service: EmbeddingService):
        self.session = session
        self.embedding_service = embedding_service
    
    async def find_products_by_query(
        self,
        query: str,
        category_id: Optional[int] = None,
        user_id: Optional[int] = None,
        limit: int = 3
    ) -> List[Product]:
        """
        Выполняет семантический поиск продуктов по смысловому сходству.
        """
        try:
            # Получаем похожие продукты через семантический поиск
            similar_products = await self._find_similar_products_by_embedding(
                query, 
                limit
            )
            
            if not similar_products:
                logger.info(f"Семантический поиск: результатов не найдено для '{query}'")
                return []
            
            # Получаем полные данные продуктов из БД
            products = await self._fetch_products_by_similarity_results(
                similar_products,
                category_id
            )
            
            # Сортируем по релевантности
            sorted_products = self._sort_products_by_relevance(
                products, 
                similar_products
            )
            
            logger.info(
                f"Семантический поиск: найдено {len(sorted_products)} продуктов "
                f"для запроса '{query}'"
            )
            
            return sorted_products
            
        except Exception as e:
            logger.error(f"Ошибка при выполнении семантического поиска: {e}")
            return []
    
    async def _find_similar_products_by_embedding(
        self, 
        query: str, 
        limit: int
    ) -> List[Tuple[int, float]]:
        """
        Находит похожие продукты используя векторные представления.
        """
        return await self.embedding_service.search_similar_products(
            query=query,
            limit=limit,
            min_similarity_threshold=0.3
        )
    
    async def _fetch_products_by_similarity_results(
        self,
        similar_products: List[Tuple[int, float]],
        category_id: Optional[int]
    ) -> List[Product]:
        """
        Получает полные данные продуктов из БД по результатам семантического поиска.
        """
        product_ids = [product_id for product_id, _ in similar_products]
        
        # Строим запрос
        query = select(Product).where(
            Product.id.in_(product_ids),
            Product.is_deleted == False
        )
        
        # Добавляем фильтр по категории если указан
        if category_id:
            query = query.where(Product.category_id == category_id)
        
        # Выполняем запрос
        result = await self.session.execute(query)
        products = result.scalars().all()
        
        return list(products)
    
    def _sort_products_by_relevance(
        self,
        products: List[Product],
        similar_products: List[Tuple[int, float]]
    ) -> List[Product]:
        """
        Сортирует продукты по релевантности на основе similarity score.
        """
        relevance_scores = {
            product_id: score 
            for product_id, score in similar_products
        }
        
        return sorted(
            products,
            key=lambda p: relevance_scores.get(p.id, 0),
            reverse=True
        )
