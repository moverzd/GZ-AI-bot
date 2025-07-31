import asyncio
import threading
import logging
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.connection import AsyncSessionLocal
from src.database.models import Product, ProductSphere
from .embedding_service import EmbeddingService

logger = logging.getLogger(__name__)


class EmbeddingSyncService:
    """
    Сервис для синхронизации эмбеддингов с базой данных.
    Обрабатывает события создания, обновления и удаления продуктов.
    """
    
    def __init__(self, embedding_service: EmbeddingService):
        self.embedding_service = embedding_service
    
    async def sync_all_embeddings(self) -> None:
        """
        Синхронизирует все эмбеддинги с текущим состоянием БД.
        Используется при первом запуске или для полной пересинхронизации.
        """
        try:
            async with AsyncSessionLocal() as session:
                # Получаем все активные продукты
                result = await session.execute(
                    select(ProductSphere)
                    .join(Product)
                    .where(Product.is_deleted == False)
                )
                product_spheres = result.scalars().all()
                
                logger.info(
                    f"Начинаем синхронизацию {len(product_spheres)} продуктов"
                )
                
                # Создаем эмбеддинги для каждого продукта
                for product_sphere in product_spheres:
                    await self.embedding_service.create_product_embedding(
                        product_id=product_sphere.product_id,
                        product_name=product_sphere.product_name,
                        product_description=""  # Можно добавить описание из product_sphere
                    )
                
                logger.info("Синхронизация эмбеддингов завершена")
                
        except Exception as e:
            logger.error(f"Ошибка при синхронизации всех эмбеддингов: {e}")
            raise
    
    async def handle_product_created(self, product: Product) -> None:
        """
        Обрабатывает создание нового продукта.
        
        Args:
            product: Созданный продукт
        """
        logger.info(f"Обработка создания продукта {product.id}: {product.name}")
        
        try:
            await self.embedding_service.create_product_embedding(
                product_id=product.id,
                product_name=product.name,
                product_description=""
            )
        except Exception as e:
            logger.error(
                f"Ошибка при создании эмбеддинга для продукта {product.id}: {e}"
            )
    
    async def handle_product_updated(self, product: Product) -> None:
        """
        Обрабатывает обновление продукта.
        
        Args:
            product: Обновленный продукт
        """
        logger.info(f"Обработка обновления продукта {product.id}: {product.name}")
        
        try:
            if product.is_deleted:
                # Если продукт помечен как удаленный
                await self.embedding_service.delete_product_embedding(product.id)
            else:
                # Обновляем эмбеддинг
                await self.embedding_service.update_product_embedding(
                    product_id=product.id,
                    product_name=product.name,
                    product_description=""
                )
        except Exception as e:
            logger.error(
                f"Ошибка при обновлении эмбеддинга для продукта {product.id}: {e}"
            )
    
    async def handle_product_deleted(self, product_id: int) -> None:
        """
        Обрабатывает удаление продукта.
        
        Args:
            product_id: ID удаленного продукта
        """
        logger.info(f"Обработка удаления продукта {product_id}")
        
        try:
            await self.embedding_service.delete_product_embedding(product_id)
        except Exception as e:
            logger.error(
                f"Ошибка при удалении эмбеддинга для продукта {product_id}: {e}"
            )


# Функции для асинхронной обработки событий SQLAlchemy
def process_product_event_async(
    sync_service: EmbeddingSyncService,
    event_handler_name: str,
    *args
):
    """
    Выполняет асинхронный обработчик события в отдельном потоке.
    
    Args:
        sync_service: Экземпляр сервиса синхронизации
        event_handler_name: Имя метода обработчика
        args: Аргументы для обработчика
    """
    def run_in_thread():
        try:
            # Создаем новый event loop для потока
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # Получаем обработчик
            handler = getattr(sync_service, event_handler_name)
            
            # Запускаем обработчик
            loop.run_until_complete(handler(*args))
            
        except Exception as e:
            logger.error(
                f"Ошибка в асинхронном обработчике {event_handler_name}: {e}"
            )
        finally:
            loop.close()
    
    # Запускаем в отдельном daemon потоке
    thread = threading.Thread(target=run_in_thread, daemon=True)
    thread.start()


# Глобальный экземпляр сервиса синхронизации (инициализируется при запуске)
_sync_service: Optional[EmbeddingSyncService] = None


def initialize_sync_service(embedding_service: EmbeddingService):
    """
    Инициализирует глобальный сервис синхронизации.
    
    Args:
        embedding_service: Сервис для работы с эмбеддингами
    """
    global _sync_service
    _sync_service = EmbeddingSyncService(embedding_service)
    logger.info("Сервис синхронизации эмбеддингов инициализирован")


# Обработчики событий SQLAlchemy
def on_product_insert(mapper, connection, target):
    """Обработчик события создания продукта."""
    if _sync_service:
        process_product_event_async(
            _sync_service,
            'handle_product_created',
            target
        )


def on_product_update(mapper, connection, target):
    """Обработчик события обновления продукта."""
    if _sync_service:
        process_product_event_async(
            _sync_service,
            'handle_product_updated',
            target
        )


def on_product_delete(mapper, connection, target):
    """Обработчик события удаления продукта."""
    if _sync_service:
        process_product_event_async(
            _sync_service,
            'handle_product_deleted',
            target.id
        )