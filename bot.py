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
from src.keyboards.user import get_main_menu_keyboard
from aiogram import Bot, Dispatcher

# Импортируем новые сервисы
from src.services.embeddings.embedding_service import EmbeddingService
from src.services.embeddings.sync_service import initialize_sync_service

"""
bot.py:
Инициализация обычный и векторной базы данных, запуск бота, 
handlers: 
help - все команды
admin - команды админа

уведомления админам что бот поднялся
"""

debug_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
logging.basicConfig(level = logging.INFO, format = debug_format)
logger = logging.getLogger(__name__)

# Создаем глобальный экземпляр сервиса эмбеддингов
embedding_service = EmbeddingService()

async def main():

    logger.info("Запуск Telegram бота")
    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )

    # создаем объект Dispatcher, который отвечает за обработку входящих запросов       
    dp = Dispatcher()
    

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
    dp.include_router(common_router) # NOTE: ВСЕГДА В КОНЦЕ
        
    @dp.message(Command('admin'))
    # Message - класс сообщения, очень много полей у него
    async def cmd_admin(message: Message, is_admin: bool = False):
        if not is_admin:
            await message.answer(
                "У вас нет прав администратора.\n"
                f"Ваш ID: {message.from_user.id if message.from_user else 'Unknown'}\n",
                reply_markup=get_main_menu_keyboard() # появление меню для обычного пользователя
            )
            return
        
        from src.keyboards.admin import get_admin_main_menu_keyboard
        
        admin_text = (
            '<b>🛠️ Панель администратора</b>\n\n'
            'Выберите действие:'
        )

        # Отправляем админ текст и админ панель
        await message.answer(admin_text, reply_markup=get_admin_main_menu_keyboard(), parse_mode='HTML')
    
    # Инициализируем базу данных с характеристиками
    await init_db()
    
    # Инициализируем векторный поиск с новой архитектурой
    try:
        # Инициализируем сервис эмбеддингов
        await embedding_service.initialize()
        logger.info("✅ Сервис эмбеддингов инициализирован")
        
        # Инициализируем сервис синхронизации для автообновления
        initialize_sync_service(embedding_service)
        logger.info("✅ Сервис синхронизации эмбеддингов активирован")
        
        # Получаем и выводим статистику
        stats = await embedding_service.get_statistics()
        logger.info(f"📊 Статистика векторной БД: {stats}")
        
        # Опционально: синхронизируем все эмбеддинги при первом запуске
        # from src.services.embeddings.sync_service import EmbeddingSyncService
        # sync_service = EmbeddingSyncService(embedding_service)
        # await sync_service.sync_all_embeddings()
        # logger.info("✅ Синхронизация эмбеддингов завершена")
    
    except Exception as e:
        logger.error(f"❌ Не удалось инициализировать векторный поиск: {e}")
        logger.warning("⚠️ Бот будет работать только с лексическим поиском")
    
    # Делаем сервис эмбеддингов доступным глобально для handlers
    # Вместо bot['embedding_service'] используем модуль для хранения
    import src.handlers.search as search_handler
    search_handler.embedding_service = embedding_service
        
    # Отправляем уведомление админам о запуске
    if settings.admin_ids:
        for admin_id in settings.admin_ids:
            try:
                now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                await bot.send_message(
                    admin_id,
                    f"🛠️ Бот онлайн! {now}"
                )
            except Exception:
                pass 
        
    
    await dp.start_polling(bot, skip_updates = True) # не отвечаем на ожидающие ответа сообщения
        

if __name__ == '__main__':
    asyncio.run(main())