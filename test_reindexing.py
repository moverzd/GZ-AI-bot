#!/usr/bin/env python3
"""
Тест реиндексации продукта после редактирования полей
"""
import asyncio
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from src.database.connection import AsyncSessionLocal, init_db
from src.services.product_service import ProductService
from src.services.auto_chunking_service import AutoChunkingService

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_product_edit_reindexing():
    """Тестируем реиндексацию продукта после редактирования"""
    
    # Инициализируем базу данных
    await init_db()
    
    session = AsyncSessionLocal()
    try:
        product_service = ProductService(session)
        
        # Выберем первый доступный продукт для тестирования
        products = await product_service.get_all_products()
        if not products:
            print("❌ Нет продуктов для тестирования")
            return
            
        test_product = products[0]
        product_id = test_product['id']
        print(f"🧪 Тестируем продукт ID: {product_id}, название: {test_product['name']}")
        
        # Получаем детальную информацию о продукте
        product_info = await product_service.get_product_by_id(product_id)
        if not product_info:
            print(f"❌ Не удалось получить информацию о продукте {product_id}")
            return
            
        print(f"📦 Информация о продукте:")
        print(f"   ID: {product_info['id']}")
        print(f"   Название: {product_info['name']}")
        print(f"   Категория: {product_info.get('category', 'Не указана')}")
        
        spheres_info = product_info.get('spheres_info', [])
        if spheres_info:
            sphere = spheres_info[0]
            print(f"   Описание: {sphere.get('description', 'Не указано')}")
            print(f"   Преимущества: {sphere.get('advantages', 'Не указаны')}")
            print(f"   Расход: {sphere.get('notes', 'Не указан')}")
        
        # Проверяем текущие эмбеддинги
        auto_chunking = AutoChunkingService()
        await auto_chunking.initialize()
        
        stats_before = await auto_chunking.get_statistics()
        print(f"\n📊 Статистика эмбеддингов до изменения:")
        print(f"   Всего эмбеддингов: {stats_before.get('total_embeddings', 0)}")
        
        # Получаем эмбеддинги конкретно этого продукта
        from src.services.embeddings.unified_embedding_service import UnifiedEmbeddingService
        embedding_service = UnifiedEmbeddingService()
        await embedding_service.initialize()
        
        if embedding_service.collection:
            results_before = embedding_service.collection.get(
                where={"product_id": product_id}
            )
            print(f"   Эмбеддингов продукта {product_id}: {len(results_before['ids']) if results_before['ids'] else 0}")
            
            if results_before['ids']:
                print(f"   ID эмбеддингов: {results_before['ids'][:3]}..." if len(results_before['ids']) > 3 else f"   ID эмбеддингов: {results_before['ids']}")
        else:
            print("❌ Не удалось подключиться к коллекции эмбеддингов")
            results_before = {'ids': [], 'documents': [], 'metadatas': []}
        
        # Теперь изменим поле продукта (например, описание)
        old_description = ""
        if spheres_info:
            old_description = spheres_info[0].get('description', '')
        
        new_description = f"Обновленное описание продукта (тест {asyncio.get_event_loop().time()})"
        print(f"\n🔄 Обновляем описание продукта...")
        print(f"   Было: '{old_description[:50]}...'" if len(old_description) > 50 else f"   Было: '{old_description}'")
        print(f"   Стало: '{new_description}'")
        
        # Выполняем обновление через ProductService (это должно вызвать реиндексацию)
        success = await product_service.update_product_field(product_id, "description", new_description)
        
        if success:
            print("✅ Поле успешно обновлено")
            
            # Ждем немного для завершения асинхронных операций
            await asyncio.sleep(2)
            
            # Проверяем эмбеддинги после изменения
            stats_after = await auto_chunking.get_statistics()
            print(f"\n📊 Статистика эмбеддингов после изменения:")
            print(f"   Всего эмбеддингов: {stats_after.get('total_embeddings', 0)}")
            
            if embedding_service.collection:
                results_after = embedding_service.collection.get(
                    where={"product_id": product_id}
                )
                print(f"   Эмбеддингов продукта {product_id}: {len(results_after['ids']) if results_after['ids'] else 0}")
                
                if results_after['ids']:
                    print(f"   ID эмбеддингов: {results_after['ids'][:3]}..." if len(results_after['ids']) > 3 else f"   ID эмбеддингов: {results_after['ids']}")
                    
                    # Проверяем метаданные одного из эмбеддингов
                    if results_after['metadatas']:
                        sample_metadata = results_after['metadatas'][0]
                        print(f"   Пример метаданных: {sample_metadata}")
                    
                    # Проверяем содержимое документов
                    if results_after['documents']:
                        sample_doc = results_after['documents'][0]
                        print(f"   Пример документа: '{sample_doc[:100]}...'" if len(sample_doc) > 100 else f"   Пример документа: '{sample_doc}'")
                        
                        # Проверяем, содержит ли документ новое описание
                        if new_description in sample_doc:
                            print("✅ Новое описание найдено в эмбеддингах!")
                        else:
                            print("⚠️  Новое описание НЕ найдено в эмбеддингах")
                            print("🔍 Проверим все документы...")
                            found_in_any = any(new_description in doc for doc in results_after['documents'])
                            if found_in_any:
                                print("✅ Новое описание найдено в одном из эмбеддингов!")
                            else:
                                print("❌ Новое описание НЕ найдено ни в одном эмбеддинге!")
                
                # Проверяем, изменились ли ID эмбеддингов (должны, если была переиндексация)
                old_ids = set(results_before['ids']) if results_before['ids'] else set()
                new_ids = set(results_after['ids']) if results_after['ids'] else set()
                
                if old_ids != new_ids:
                    print("✅ ID эмбеддингов изменились - переиндексация прошла!")
                    print(f"   Удалено: {len(old_ids - new_ids)} эмбеддингов")
                    print(f"   Добавлено: {len(new_ids - old_ids)} эмбеддингов")
                else:
                    print("⚠️  ID эмбеддингов НЕ изменились")
            else:
                print("❌ Не удалось подключиться к коллекции для проверки результатов")
                results_after = {'ids': [], 'documents': [], 'metadatas': []}
                
        else:
            print("❌ Ошибка обновления поля")
            
        # Восстанавливаем старое описание
        if old_description:
            print(f"\n🔄 Восстанавливаем старое описание...")
            await product_service.update_product_field(product_id, "description", old_description)
            print("✅ Старое описание восстановлено")
            
    except Exception as e:
        print(f"❌ Ошибка в тесте: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        await session.close()

if __name__ == "__main__":
    asyncio.run(test_product_edit_reindexing())
