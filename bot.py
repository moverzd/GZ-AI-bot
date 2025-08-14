import asyncio
import datetime
import logging

from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import Message
from aiogram.filters import Command

from src.config.settings import settings
from src.database.connection import init_db, AsyncSessionLocal
from src.middlewares.auth import AdminMiddleware, DatabaseSessionMiddleware
from src.handlers.common import router as common_router
from src.handlers.catalog import router as catalog_router
from src.handlers.search import router as search_router
from src.handlers.admin import router as admin_router
from src.handlers.edit import router as edit_router
from src.handlers.upload_content import router as upload_content_router
from src.handlers.upload_main_image import router as upload_main_image_router
from src.handlers.delete_files import router as delete_files_router
from src.handlers.rag import router as rag_router
from src.handlers.feedback import router as feedback_router
from src.keyboards.user import get_main_menu_keyboard
from aiogram import Bot, Dispatcher

# Импортируем новые сервисы
from src.services.file_service import FileService
from src.services.embeddings.model_manager import model_manager

"""
bot.py:
Инициализация обычный и векторной базы данных, запуск бота, 
handlers: 
start - запуск
help - все команды
admin - команды админа

уведомления админам что бот поднялся
"""

debug_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
logging.basicConfig(level = logging.INFO, format = debug_format)
logger = logging.getLogger(__name__)

async def check_system_status() -> dict:
    """
    Проверяет статус всех систем бота
    Возвращает словарь со статусами
    """
    status = {
        'database': '🔴 Не подключена',
        'vector_database': '🔴 Не подключена', 
        'rag_system': '🔴 Не готова',
        'embedding_model': '🔴 Не загружена',
        'file_service': '🔴 Не готов',
        'search_system': '🔴 Не готова'
    }
    
    try:
        # Проверяем основную базу данных
        from sqlalchemy import text
        session = AsyncSessionLocal()
        await session.execute(text("SELECT 1"))  # Простой тест запрос
        await session.close()
        status['database'] = '🟢 Подключена'
    except Exception as e:
        status['database'] = f'🔴 Ошибка: {str(e)[:50]}'
    
    try:
        # Проверяем модель эмбеддингов
        # Попробуем предзагрузить модель если она еще не загружена
        model_manager.preload_model()
        status['embedding_model'] = '🟢 Готова к использованию'
    except Exception as e:
        status['embedding_model'] = f'🔴 Ошибка: {str(e)[:50]}'
    
    try:
        # Проверяем векторную базу данных через сервис эмбеддингов
        from src.services.embeddings.unified_embedding_service import UnifiedEmbeddingService
        embedding_service = UnifiedEmbeddingService()
        # Принудительно инициализируем сервис если еще не инициализирован
        if not embedding_service._is_initialized:
            await embedding_service.initialize()
        stats = await embedding_service.get_statistics()
        if 'error' not in stats:
            status['vector_database'] = f'🟢 Подключена ({stats.get("total_embeddings", 0)} записей)'
            status['rag_system'] = '🟢 Готова'
        else:
            status['vector_database'] = '🔴 Ошибка подключения'
            status['rag_system'] = '🔴 Не готова'
    except Exception as e:
        status['vector_database'] = f'🔴 Ошибка: {str(e)[:50]}'
        status['rag_system'] = '🔴 Не готова'
    
    try:
        # Проверяем файловый сервис
        session = AsyncSessionLocal()
        file_service = FileService(session)
        stats = await file_service.get_files_stats()
        await session.close()
        status['file_service'] = f'🟢 Готов ({stats["total_files"]} файлов)'
    except Exception as e:
        status['file_service'] = f'🔴 Ошибка: {str(e)[:50]}'
    
    try:
        # Проверяем поисковую систему
        from src.services.search.hybrid_search import HybridSearchService
        session = AsyncSessionLocal()
        search_service = HybridSearchService(session)
        await session.close()
        # Если сервис создался без ошибок, считаем его готовым
        status['search_system'] = '🟢 Готова'
    except Exception as e:
        status['search_system'] = f'🔴 Ошибка: {str(e)[:50]}'
    
    return status

def format_startup_status_for_telegram(status: dict) -> str:
    """
    Форматирует статус запуска для отправки в Telegram
    """
    now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    message = f"<b>🤖 Бот запущен! {now}</b>\n\n"

    message += f"🔧 <b>Статус систем:</b>\n"
    message += f"Основная БД: {status['database']}\n"
    message += f"Векторная БД: {status['vector_database']}\n"
    message += f"RAG система: {status['rag_system']}\n"
    message += f"Модель эмбеддингов: {status['embedding_model']}\n"
    message += f"Файловый сервис: {status['file_service']}\n"
    message += f"Поисковая система: {status['search_system']}\n\n"
    
    # Проверяем общий статус
    all_ready = all('🟢' in status_text for status_text in status.values())
    if all_ready:
        message += "🟢 <b>Все системы полностью работают!</b>"
    else:
        message += "🟡 <b>Некоторые системы требуют проверки</b>"
    
    return message

def print_startup_status(status: dict):
    """
    Красиво выводит статус запуска бота
    """
    now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    print("\n" + "="*60)
    print(f"🤖 Бот запущен! {now}>\n")
    print(f"🔧 Статус систем:")
    print("-"*60)
    print(f"Основная БД:         {status['database']}")
    print(f"Векторная БД:        {status['vector_database']}")
    print(f"RAG система:         {status['rag_system']}")
    print(f"Модель эмбеддингов:  {status['embedding_model']}")
    print(f"Файловый сервис:     {status['file_service']}")
    print(f"Поисковая система:   {status['search_system']}")
    print("="*60)
    
    # Проверяем общий статус
    all_ready = all('🟢' in status_text for status_text in status.values())
    if all_ready:
        print("ВСЕ СИСТЕМЫ ГОТОВЫ К РАБОТЕ!")
    else:
        print("НЕКОТОРЫЕ СИСТЕМЫ ТРЕБУЮТ ВНИМАНИЯ")
    print("="*60 + "\n")

async def on_startup():
    """
    Функция для инициализации при запуске бота
    """
    # Инициализируем базу данных СНАЧАЛА
    await init_db()
    
    # Предзагружаем модель эмбеддингов при старте бота
    model_manager.preload_model()
    
    # Проверяем статус всех систем (включая инициализацию векторной БД)
    system_status = await check_system_status()
    
    # НЕ выводим статус здесь - он выведется после всех проверок
    
    # Возвращаем статус для дальнейшего использования
    return system_status

async def main():

    # Проверяем наличие токена
    if not settings.bot_token:
        print("🔴 Ошибка: токен бота не найден в настройках!")
        return

    logger.info("Запуск Telegram бота")
    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )

    # создаем объект Dispatcher, который отвечает за обработку входящих запросов       
    dp = Dispatcher()
    
    # Переменная для хранения статуса системы
    system_status = None
    
    # Создаем обертку для on_startup, чтобы получить статус
    async def startup_wrapper():
        nonlocal system_status
        system_status = await on_startup()
        
        # Предзагружаем файлы после инициализации систем
        session = AsyncSessionLocal()
        try:
            file_service = FileService(session)
            
            # Проверяем и скачиваем файлы, которые не скачаны
            download_stats = await file_service.first_files_download()
            
            if download_stats["total"] > 0:
                logger.info(f"Предзагрузка файлов: {download_stats['success']} успешно, {download_stats['failed']} ошибок")
            
            # Получаем общую статистику файлов
            files_stats = await file_service.get_files_stats()
            logger.info(f"Общая статистика файлов: Всего: {files_stats['total_files']}, " +
                        f"Скачано: {files_stats['downloaded_files']}, Не скачано: {files_stats['not_downloaded_files']}")
        
        finally:
            await session.close()
        
        # ТЕПЕРЬ выводим финальный статус в терминале (после всех проверок)
        print_startup_status(system_status)
        
        # Отправляем уведомление админам о запуске с полным статусом
        if settings.admin_ids and system_status:
            startup_message = format_startup_status_for_telegram(system_status)
            for admin_id in settings.admin_ids:
                try:
                    await bot.send_message(
                        admin_id,
                        startup_message,
                        parse_mode='HTML'
                    )
                    logger.info(f"Статус запуска отправлен администратору {admin_id}")
                except Exception as e:
                    logger.error(f"Ошибка отправки статуса админу {admin_id}: {e}")
    
    # Регистрируем функцию startup_wrapper для выполнения при запуске бота
    dp.startup.register(startup_wrapper)

    # middleware - промежуточный код, который выполняется до того, как запрос будет обработан handler'ом
    # в контексте aiogram - компоненты, которые могут изменять, добавлять, проверять данные к каждому апдейту

    # является ли юзер админом? if true добавляем is_admin = True в обработчик
    dp.message.middleware(AdminMiddleware())  # для сообщения от пользователя
    dp.callback_query.middleware(AdminMiddleware()) # для inline кнопок

    # управление бд, каждый раз создает новую сессию с бд и закрывает ее после выполнения запроса
    dp.message.middleware(DatabaseSessionMiddleware()) 
    dp.callback_query.middleware(DatabaseSessionMiddleware())

    # Подключение роутеров(группа обработчиков) к dispatcher        
    dp.include_router(catalog_router) # логика каталога
    dp.include_router(search_router) # поисковик
    dp.include_router(admin_router) # админ-панель
    dp.include_router(edit_router) # редактирование
    dp.include_router(upload_content_router) # загрузка файлов
    dp.include_router(upload_main_image_router) # загрузка главных изображений
    dp.include_router(delete_files_router) # удаление файлов
    dp.include_router(rag_router) # обработчики для RAG
    dp.include_router(feedback_router) # обработчики обратной связи
    dp.include_router(common_router) # NOTE: ВСЕГДА В КОНЦЕ
        
    @dp.message(Command('admin'))
    # Message - класс сообщения, очень много полей у него
    async def cmd_admin(message: Message, is_admin: bool = False):
        if not is_admin:
            await message.answer(
                "🔴 У вас нет прав администратора.\n"
                f"Ваш ID: {message.from_user.id if message.from_user else 'Unknown'}\n\n"
                "💡 Для получения помощи используйте команду /help",
                reply_markup=get_main_menu_keyboard() # появление меню для обычного пользователя
            )
            return
        
        from src.keyboards.admin import get_admin_main_menu_keyboard
        
        admin_text = (
            '<b>🛠️ Панель администратора</b>\n\n'
            '📋 Выберите действие:'
        )

        # Отправляем админ текст и админ панель
        await message.answer(admin_text, reply_markup=get_admin_main_menu_keyboard(), parse_mode='HTML')
    

    await dp.start_polling(bot, skip_updates = True) # не отвечаем на ожидающие ответа сообщения
        

if __name__ == '__main__':
    asyncio.run(main())