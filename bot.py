import asyncio
import logging
import sys
import traceback

print("🚀 Запуск бота GZ (Битумные материалы)...")

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
    print("✅ Конфигурация загружена")
    print(f"🔑 Токен бота: {'✅ Загружен' if settings.bot_token else '❌ Отсутствует'}")
    print(f"🗄️ База данных: {settings.database_url}")
    print(f"👑 ID админов: {settings.admin_ids}")
    
except Exception as e:
    print(f"❌ Ошибка импорта конфигурации: {e}")
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
    
    print("✅ Все модули загружены успешно")
    
except Exception as e:
    print(f"❌ Ошибка импорта модулей: {e}")
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
        
        logger.info("🔧 Регистрация middleware...")
        
        # Регистрируем middleware
        dp.message.middleware(AdminMiddleware())
        dp.callback_query.middleware(AdminMiddleware())
        dp.message.middleware(DatabaseSessionMiddleware())
        dp.callback_query.middleware(DatabaseSessionMiddleware())
        
        logger.info("📋 Регистрация обработчиков...")
        
        # Регистрируем основные обработчики
        dp.include_router(common_router)
        dp.include_router(catalog_router)
        dp.include_router(search_router)
        
        # Добавляем дополнительные обработчики для демонстрации возможностей
        
        @dp.message(Command('help'))
        async def cmd_help(message: Message):
            """Помощь по командам"""
            help_text = (
                "🤖 <b>Доступные команды:</b>\n\n"
                "/start - Запуск бота\n"
                "/help - Эта справка\n"
                "/status - Статус системы\n"
                "/categories - Список категорий\n"
                "/search [запрос] - Поиск продукта\n\n"
                "📱 <b>Возможности бота:</b>\n"
                "• Каталог битумных продуктов\n"
                "• Поиск по названию\n"
                "• Просмотр характеристик\n"
                "• Скачивание документации\n"
                "• Контактная информация\n\n"
                "Просто введите название продукта для поиска!"
            )
            await message.answer(help_text, reply_markup=get_main_menu_keyboard())
        
        @dp.message(Command('status'))
        async def cmd_status(message: Message, session):
            """Статус системы"""
            try:
                # Проверяем подключение к БД
                from sqlalchemy import text
                await session.execute(text("SELECT 1"))
                db_status = "✅ Подключена"
            except Exception:
                db_status = "❌ Ошибка подключения"
            
            try:
                # Считаем продукты
                from sqlalchemy import select, func
                from src.database.models import Product, Category
                
                product_count = await session.scalar(
                    select(func.count(Product.id)).where(Product.is_deleted == False)
                )
                category_count = await session.scalar(select(func.count(Category.id)))
                
                status_text = (
                    "📊 <b>Статус системы:</b>\n\n"
                    f"🗄️ База данных: {db_status}\n"
                    f"📦 Продуктов: {product_count or 0}\n"
                    f"📂 Категорий: {category_count or 0}\n"
                    f"👤 Ваш ID: {message.from_user.id}\n"
                    f"� Время: {asyncio.get_event_loop().time():.0f}s"
                )
                
            except Exception as e:
                status_text = (
                    "📊 <b>Статус системы:</b>\n\n"
                    f"🗄️ База данных: {db_status}\n"
                    f"❌ Ошибка получения статистики: {str(e)[:50]}..."
                )
            
            await message.answer(status_text, reply_markup=get_main_menu_keyboard())
        
        @dp.message(Command('categories'))
        async def cmd_categories(message: Message, session):
            """Список всех категорий"""
            try:
                from sqlalchemy import select
                from src.database.models import Category
                
                result = await session.execute(select(Category))
                categories = result.scalars().all()
                
                if categories:
                    text = "📂 <b>Доступные категории:</b>\n\n"
                    for i, category in enumerate(categories, 1):
                        text += f"{i}. {esc(category.name)}\n"
                    text += "\n💡 Используйте меню ниже для навигации"
                else:
                    text = "📂 Категории пока не добавлены"
                
            except Exception as e:
                text = f"❌ Ошибка загрузки категорий: {str(e)[:50]}..."
            
            await message.answer(text, reply_markup=get_main_menu_keyboard())
        
        @dp.message(Command('search'))
        async def cmd_search(message: Message, session):
            """Поиск через команду"""
            query = message.text[8:].strip()  # Убираем "/search "
            
            if not query:
                await message.answer(
                    "🔍 Использование: /search [запрос]\n"
                    "Пример: /search битум\n\n"
                    "Или просто введите название продукта без команды!",
                    reply_markup=get_main_menu_keyboard()
                )
                return
            
            try:
                from src.services.search_service import SearchService
                
                search_service = SearchService(session)
                results = await search_service.search_products(query)
                
                if not results:
                    await message.answer(
                        f"🔍 По запросу '{esc(query)}' ничего не найдено.\n"
                        "Попробуйте другие ключевые слова.",
                        reply_markup=get_main_menu_keyboard()
                    )
                    return
                
                text = f"🔍 <b>Результаты поиска '{esc(query)}':</b>\n\n"
                
                for i, (product, main_image) in enumerate(results[:5], 1):
                    text += f"{i}. <b>{esc(product.name)}</b>\n"
                    if product.short_desc:
                        desc = product.short_desc[:100]
                        text += f"   {esc(desc)}{'...' if len(product.short_desc) > 100 else ''}\n"
                    text += "\n"
                
                if len(results) > 5:
                    text += f"... и еще {len(results) - 5} результатов\n\n"
                
                text += "💡 Используйте каталог для подробного просмотра"
                
            except Exception as e:
                text = f"❌ Ошибка поиска: {str(e)[:50]}..."
            
            await message.answer(text, reply_markup=get_main_menu_keyboard())
        
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
                        "🚀 <b>Бот запущен!</b>\n"
                        f"🤖 @{bot_info.username}\n"
                        f"🕐 {asyncio.get_event_loop().time():.0f}s\n"
                        "Система готова к работе."
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