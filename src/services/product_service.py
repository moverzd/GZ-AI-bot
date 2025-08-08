from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from src.database.repositories import ProductRepository
from src.database.product_file_repositories import ProductFileRepository
from src.database.models import Product, Category, ProductSphere, Sphere, ProductPackage
from src.services.search.semantic_search import SemanticSearchService
from src.core.utils import split_advantages

import logging
logger = logging.getLogger(__name__)


def format_package_info(packages: List[ProductPackage]) -> Optional[str]:
    """
    Форматирует информацию об упаковке для отображения в карточке продукта.
    Если хоть одно поле имеет значение 0, информация об упаковке не отображается.
    """
    if not packages:
        return None
    
    # Фильтруем пакеты, где все поля больше 0
    valid_packages = []
    for package in packages:
        try:
            # Получаем значения атрибутов
            weight = getattr(package, 'package_weight', 0)
            pallet_count = getattr(package, 'packages_per_pallet', 0)
            net = getattr(package, 'net_weight', 0)
            
            # Проверяем что все значения больше 0
            if weight and float(weight) > 0 and pallet_count and int(pallet_count) > 0 and net and float(net) > 0:
                valid_packages.append(package)
        except (ValueError, TypeError, AttributeError):
            continue
    
    if not valid_packages:
        return None
    
    # Собираем информацию
    package_types = []
    package_weights = []
    packages_per_pallet = []
    net_weights = []
    
    for package in valid_packages:
        # Экранируем HTML символы в типе упаковки
        from src.core.utils import esc
        package_types.append(esc(str(getattr(package, 'package_type', ''))))
        weight = float(getattr(package, 'package_weight', 0))
        package_weights.append(f"{weight:.1f} кг")
        packages_per_pallet.append(str(getattr(package, 'packages_per_pallet', 0)))
        net = float(getattr(package, 'net_weight', 0))
        net_weights.append(f"{net:.1f} кг")
    
    # Формируем текст
    text = "<b>Информация по упаковке:</b>\n"
    text += f"• Тип упаковки: {', '.join(package_types)}\n"
    text += f"• Вес одного места: {', '.join(package_weights)}\n" 
    text += f"• Количество тары на одном паллете: {', '.join(packages_per_pallet)}\n"
    text += f"• Вес НЕТТО: {', '.join(net_weights)}\n"
    
    return text

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
        
        # Упаковка
        packages_query = select(ProductPackage).where(
            ProductPackage.product_id == product_id,
            ProductPackage.is_active == True
        )
        packages_result = await self.session.execute(packages_query)
        packages = packages_result.scalars().all()
        
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
            "packages": packages,
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
        product_sphere_fields = ['description', 'advantages', 'notes']
        
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
    
    async def get_product_package(self, product_id: int) -> Optional[ProductPackage]:
        """
        Получает информацию об упаковке продукта из таблицы product_package
        """
        from sqlalchemy import select
        
        result = await self.session.execute(
            select(ProductPackage).where(
                ProductPackage.product_id == product_id,
                ProductPackage.is_active == True
            )
        )
        return result.scalars().first()
    
    async def update_or_create_product_package(
        self, 
        product_id: int, 
        package_type: str,
        package_weight: float,
        packages_per_pallet: int,
        net_weight: float
    ) -> bool:
        """
        Обновляет или создает информацию об упаковке продукта
        """
        try:
            from sqlalchemy import select
            
            # Получаем продукт для проверки существования и получения имени
            product_result = await self.session.execute(
                select(Product).where(Product.id == product_id, Product.is_deleted == False)
            )
            product = product_result.scalars().first()
            
            if not product:
                return False
            
            # Проверяем, есть ли уже запись об упаковке для этого продукта
            existing_result = await self.session.execute(
                select(ProductPackage).where(
                    ProductPackage.product_id == product_id,
                    ProductPackage.is_active == True
                )
            )
            existing_package = existing_result.scalars().first()
            
            if existing_package:
                # Обновляем существующую запись
                existing_package.package_type = package_type
                existing_package.package_weight = package_weight
                existing_package.packages_per_pallet = packages_per_pallet
                existing_package.net_weight = net_weight
            else:
                # Создаем новую запись
                new_package = ProductPackage(
                    product_id=product_id,
                    product_name=product.name,
                    package_type=package_type,
                    package_weight=package_weight,
                    packages_per_pallet=packages_per_pallet,
                    net_weight=net_weight,
                    is_active=True
                )
                self.session.add(new_package)
            
            await self.session.commit()
            return True
            
        except Exception as e:
            await self.session.rollback()
            return False
    
    async def get_product_text_for_indexing(self, product_id: int) -> Optional[str]:
        """
        Получает текстовое представление продукта для индексации в векторной БД.
        Включает информацию об упаковке из таблицы product_package.
        """
        product_info = await self.get_product_by_id(product_id)
        if not product_info:
            return None
        
        # Собираем текстовое представление
        text_parts = []
        
        # Базовая информация
        text_parts.append(f"Продукт: {product_info['name']}")
        
        if product_info.get('category'):
            text_parts.append(f"Категория: {product_info['category'].name}")
        
        # Описание
        if product_info.get('description'):
            text_parts.append(f"Описание: {product_info['description']}")
        
        # Сферы применения
        spheres = product_info.get('spheres', [])
        for sphere in spheres:
            if sphere.get('name'):
                text_parts.append(f"Сфера применения: {sphere['name']}")
            
            # Преимущества
            if sphere.get('advantages'):
                advantages_text = " ".join(sphere['advantages'])
                text_parts.append(f"Преимущества: {advantages_text}")
            
            # Расход/примечания
            if sphere.get('notes'):
                text_parts.append(f"Расход: {sphere['notes']}")
        
        # Информация об упаковке из новой таблицы product_package
        packages = product_info.get('packages', [])
        for package in packages:
            try:
                weight = getattr(package, 'package_weight', 0)
                pallet_count = getattr(package, 'packages_per_pallet', 0)
                net = getattr(package, 'net_weight', 0)
                package_type = getattr(package, 'package_type', '')
                
                # Добавляем информацию об упаковке только если все поля заполнены
                if weight and float(weight) > 0 and pallet_count and int(pallet_count) > 0 and net and float(net) > 0:
                    text_parts.append(f"Тип упаковки: {package_type}")
                    text_parts.append(f"Вес одного места: {weight} кг")
                    text_parts.append(f"Количество тары на одном паллете: {pallet_count}")
                    text_parts.append(f"Вес нетто: {net} кг")
            except (ValueError, TypeError, AttributeError):
                continue
        
        return "\n".join(text_parts)

    async def search_products_by_query(self, query: str, category_id: Optional[int] = None, limit: int = 3) -> List[Product]:
        """
        Выполняет семантический поиск продуктов по запросу.
        Создает временный поисковый сервис для выполнения запроса.
        """
        # Создаем поисковый сервис
        search_service = SemanticSearchService(self.session)
        await search_service.embedding_service.initialize()
        
        return await search_service.find_products_by_query(query, category_id, limit=limit)


