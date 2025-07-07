import asyncio
import logging
import sys
import traceback


# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

try:
    from aiogram import Bot, Dispatcher
    from aiogram.client.default import DefaultBotProperties
    from aiogram.enums import ParseMode
    from aiogram.types import Message
    from aiogram.filters import Command
    
    from src.config.settings import settings
    
except Exception as e:
    traceback.print_exc()
    sys.exit(1)

try:
    from src.database.connection import init_db, AsyncSessionLocal
    from src.middlewares.auth import AdminMiddleware, DatabaseSessionMiddleware
    from src.handlers.common import router as common_router
    from src.handlers.catalog import router as catalog_router
    from src.handlers.search import router as search_router
    from src.keyboards.user import get_main_menu_keyboard
    from src.core.utils import esc
    
    
except Exception as e:
    traceback.print_exc()
    sys.exit(1)

async def main():
    """Главная функция запуска бота"""
    
    try:
        # Создаем бота
        bot = Bot(
            token=settings.bot_token,
            default=DefaultBotProperties(parse_mode=ParseMode.HTML)
        )
        
        # Создаем диспетчер
        dp = Dispatcher()
        
        
        # Регистрируем middleware
        dp.message.middleware(AdminMiddleware())
        dp.callback_query.middleware(AdminMiddleware())
        dp.message.middleware(DatabaseSessionMiddleware())
        dp.callback_query.middleware(DatabaseSessionMiddleware())
        
        
        # Регистрируем основные обработчики
        dp.include_router(common_router)
        dp.include_router(catalog_router)
        dp.include_router(search_router)
        
        # Добавляем дополнительные обработчики для демонстрации возможностей
        
        @dp.message(Command('help'))
        async def cmd_help(message: Message):
            """Помощь по командам"""
            help_text = (
                "<b>Доступные команды:</b>\n\n"
                "/start - Запуск бота\n"
                "/help - Эта справка\n"
            )
            await message.answer(help_text, reply_markup=get_main_menu_keyboard())
        
        
        
        # Обработчик для демонстрации админ-функций
        @dp.message(Command('admin'))
        async def cmd_admin(message: Message, is_admin: bool = False):
            """Админ-панель (демонстрация)"""
            if not is_admin:
                await message.answer(
                    "❌ У вас нет прав администратора.\n"
                    f"Ваш ID: {message.from_user.id}\n"
                    f"Админы: {settings.admin_ids}",
                    reply_markup=get_main_menu_keyboard()
                )
                return
            
            admin_text = (
                "👑 <b>Админ-панель</b>\n\n"
                "🔧 <b>Доступные функции:</b>\n"
                "• Управление продуктами\n"
                "• Добавление/удаление категорий\n"
                "• Загрузка файлов\n"
                "• Модерация контента\n"
                "• Статистика системы\n\n"
                "⚠️ <i>Функции в разработке</i>"
            )
            
            await message.answer(admin_text, reply_markup=get_main_menu_keyboard())
        
        logger.info("🗄️ Инициализация базы данных...")
        
        # Инициализируем базу данных
        try:
            await init_db()
            logger.info("✅ База данных инициализирована")
        except Exception as db_error:
            logger.warning(f"⚠️ Ошибка БД (продолжаем работу): {db_error}")
        
        # Проверяем подключение к Telegram
        logger.info("🔄 Проверка подключения к Telegram...")
        bot_info = await bot.get_me()
        logger.info(f"✅ Бот подключен: @{bot_info.username} ({bot_info.first_name})")
        
        # Отправляем уведомление админам о запуске
        if settings.admin_ids:
            for admin_id in settings.admin_ids:
                try:
                    await bot.send_message(
                        admin_id,
                        "Бот запустился⚠️"
                    )
                except Exception:
                    pass  # Игнорируем ошибки отправки админам
        
        # Запускаем polling
        logger.info("🏃 Начинаем polling...")
        logger.info("=" * 50)
        logger.info("🤖 БОТ ГОТОВ К РАБОТЕ!")
        logger.info("📱 Доступные команды:")
        logger.info("   /start - Запуск")
        logger.info("   /help - Справка")
        logger.info("   /status - Статус")
        logger.info("   /categories - Категории")
        logger.info("   /search [запрос] - Поиск")
        logger.info("   /admin - Админ-панель")
        logger.info("💬 Также работает поиск по тексту сообщений")
        logger.info("=" * 50)
        
        await dp.start_polling(bot, skip_updates=True)
        
    except Exception as e:
        logger.error(f"❌ Критическая ошибка при запуске: {e}")
        traceback.print_exc()
    finally:
        try:
            await bot.session.close()
            logger.info("🛑 Бот остановлен")
        except:
            pass

if __name__ == '__main__':
    try:
        print("🎯 Запуск основной функции...")
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⏹️ Бот остановлен пользователем (Ctrl+C)")
    except Exception as e:
        print(f"💥 Критическая ошибка: {e}")
        traceback.print_exc()
    finally:
        print("👋 Завершение работы...")