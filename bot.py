import asyncio
import datetime

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
from src.keyboards.user import get_main_menu_keyboard
from aiogram import Bot, Dispatcher

"""
bot.py:
Инициализация базы данных, запуск бота, 
handlers: 
help - все команды
admin - команды админа

уведомления админам что бот поднялся

"""

async def main():
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
    dp.include_router(common_router) # основное меню
    dp.include_router(catalog_router) # логика каталога
    dp.include_router(search_router) # поисковик
    dp.include_router(admin_router) # админ-панель
    dp.include_router(edit_router) # редактирование
        
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
            '<b>Панель администратора</b>\n\n'
            'Выберите действие:'
        )

        # Отправляем админ текст и админ панель
        await message.answer(admin_text, reply_markup=get_admin_main_menu_keyboard(), parse_mode='HTML')
    
    # Инициализируем базу данных
    await init_db()
        
    # Отправляем уведомление админам о запуске
    if settings.admin_ids:
        for admin_id in settings.admin_ids:
            try:
                now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                await bot.send_message(
                    admin_id,
                    f"Бот стал доступен в {now}"
                )
            except Exception:
                pass 
        
    
    await dp.start_polling(bot, skip_updates = True) # не отвечаем на ожидающие ответа сообщения
        

if __name__ == '__main__':
    asyncio.run(main())