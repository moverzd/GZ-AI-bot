from aiogram import Router, types
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from src.keyboards.user import get_main_menu_keyboard
from src.handlers.states import SearchProduct

"""
Содержит базовые команды и навигацю по боту:
- /start
- возврат в главное меню
- контактное меню
- возмжности бота
- меню поиска
- базовый автоответчик
"""


router = Router()

@router.message(Command('start'))
async def cmd_start(message: types.Message, state: FSMContext):
    """Обработчик команды /start"""
    await state.clear() # очистка состояния FSM
    await message.answer(
        '<b>Газпромнефть - Битумные материалы </b>\n' \
        'Официальный телеграм-бот с каталогом продукции',
        reply_markup=get_main_menu_keyboard(), parse_mode= 'HTML'
    )

@router.message(Command('help'))
async def cmd_help(message: types.Message, state: FSMContext):
    """Обработчик команды /help - показывает возможности бота"""
    await state.clear()
    await message.answer(
        '<b>📖 Справка по боту</b>\n\n'
        '<b>👤 Возможности для пользователей:</b>\n\n'
        '🔍 Поиск продукции\n'
        '• Умный поиск по названиям продуктов\n'
        '📂 Каталог продукции\n'
        '• Фильтрация по категорям или сферам применения\n'
        '• Подробная информация о продуктах\n'
        '• Просмотр технических документов\n'
        '🤖 AI-помощник\n'
        '• Ответы на вопросы о продукции\n'
        '• Поиск в базе технических документов\n'
        '📞 Контакты\n'
        '• Информация о компании\n'
        '• Контактные данные для связи\n\n'
        '<b>🛠️ Возможности для администраторов:</b>\n\n'
        '📦Управление продукцией\n'
        '• Добавление новых продуктов\n'
        '• Редактирование характеристик\n'
        '• Удаление продуктов\n'
        '• Просмотр всего каталога\n\n'
        '📎 Управление файлами\n'
        '• Загрузка технических документов\n'
        '• Управление изображениями продуктов\n'
        '• Удаление файлов\n\n'
        '<b>💡 Команды:</b>\n'
        '/start - Главное меню\n'
        '/help - Эта справка\n'
        '/admin - Панель администратора',
        reply_markup=get_main_menu_keyboard(),
        parse_mode='HTML'
    )

@router.callback_query(lambda c: c.data == 'menu:main')
async def main_menu(callback: types.CallbackQuery, state: FSMContext):
    """Возврат в главное меню"""
    await state.clear()
    if callback.message and isinstance(callback.message, Message):
        # Всегда отправляем новое сообщение вместо редактирования
        await callback.message.answer(
            '<b>🏠 Главное меню</b>\n\nВыберите действие:',
            reply_markup=get_main_menu_keyboard(),
            parse_mode='HTML'
        )
    await callback.answer()

@router.callback_query(lambda c: c.data == 'menu:contact')
async def contact(callback: types.CallbackQuery):
    """Контактная информация"""
    if callback.message and isinstance(callback.message, Message):
        # Отправляем новое сообщение вместо редактирования
        await callback.message.answer(
            '<b>Контактная информация:</b>\n'
            '"ООО Газпромнефть-БМ"\n'
            '<b>Телефон:</b> +7 (812) 493-25-66\n'
            '<b>Адрес:</b> Большой пр. В.О. д. 80, лит. Р3-5, Санкт-Петербург, Россия, 199178 \n'
            '<b>Email:</b> Brit@gazprom-neft.ru\n'
            '<b>Сайт:</b> https://www.gazprom-neft.ru',
            reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[[
                types.InlineKeyboardButton(
                    text="⬅️ Главное меню",
                    callback_data="menu:main"
                )
            ]]),
            parse_mode='HTML'
        )
    await callback.answer()

@router.callback_query(lambda c: c.data == 'menu:features')
async def features(callback: types.CallbackQuery):
    """Описание возможностей бота"""
    if callback.message and isinstance(callback.message, Message):
        try:
            await callback.message.answer(
            '<b>📖 Справка по боту</b>\n\n'
            '<b>👤 Возможности для пользователей:</b>\n\n'
            '🔍 Поиск продукции\n'
            '• Умный поиск по названиям продуктов\n'
            '📂 Каталог продукции\n'
            '• Фильтрация по категорям или сферам применения\n'
            '• Подробная информация о продуктах\n'
            '• Просмотр технических документов\n'
            '🤖 AI-помощник\n'
            '• Ответы на вопросы о продукции\n'
            '• Поиск в базе технических документов\n'
            '📞 Контакты\n'
            '• Информация о компании\n'
            '• Контактные данные для связи\n\n'
            '<b>🛠️ Возможности для администраторов:</b>\n\n'
            '📦Управление продукцией\n'
            '• Добавление новых продуктов\n'
            '• Редактирование характеристик\n'
            '• Удаление продуктов\n'
            '• Просмотр всего каталога\n\n'
            '📎 Управление файлами\n'
            '• Загрузка технических документов\n'
            '• Управление изображениями продуктов\n'
            '• Удаление файлов\n\n'
            '<b>💡 Команды:</b>\n'
            '/start - Главное меню\n'
            '/help - Эта справка\n'
            '/admin - Панель администратора',
            reply_markup=get_main_menu_keyboard(),
            parse_mode='HTML'
        )
        except Exception:
            # В случае ошибки отправляем новое сообщение
            await callback.message.answer(
            '<b>📖 Справка по боту</b>\n\n'
            '<b>👤 Возможности для пользователей:</b>\n\n'
            '🔍 Поиск продукции\n'
            '• Умный поиск по названиям продуктов\n'
            '📂 Каталог продукции\n'
            '• Фильтрация по категорям или сферам применения\n'
            '• Подробная информация о продуктах\n'
            '• Просмотр технических документов\n'
            '🤖 AI-помощник\n'
            '• Ответы на вопросы о продукции\n'
            '• Поиск в базе технических документов\n'
            '📞 Контакты\n'
            '• Информация о компании\n'
            '• Контактные данные для связи\n\n'
            '<b>🛠️ Возможности для администраторов:</b>\n\n'
            '📦Управление продукцией\n'
            '• Добавление новых продуктов\n'
            '• Редактирование характеристик\n'
            '• Удаление продуктов\n'
            '• Просмотр всего каталога\n\n'
            '📎 Управление файлами\n'
            '• Загрузка технических документов\n'
            '• Управление изображениями продуктов\n'
            '• Удаление файлов\n\n'
            '<b>💡 Команды:</b>\n'
            '/start - Главное меню\n'
            '/help - Эта справка\n'
            '/admin - Панель администратора',
            reply_markup=get_main_menu_keyboard(),
            parse_mode = 'HTML'
        )
            return
    await callback.answer()

@router.callback_query(lambda c: c.data == 'menu:search')
async def search_menu(callback: types.CallbackQuery, state: FSMContext):
    """Меню поиска"""
    # Устанавливаем состояние ожидания поискового запроса
    await state.set_state(SearchProduct.waiting_query)
    
    if callback.message and isinstance(callback.message, Message):
        # Отправляем новое сообщение вместо редактирования
        await callback.message.answer(
            '<b>🔍 Поиск продуктов</b>\n\n'
            'Введите название продукта или его часть для поиска:',
            reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[[
                types.InlineKeyboardButton(
                    text="⬅️ Главное меню",
                    callback_data="menu:main"
                )
            ]]),
            parse_mode='HTML'
        )
    await callback.answer()

@router.callback_query(lambda c: c.data == 'menu:question')
async def ai_question_menu(callback: types.CallbackQuery, state: FSMContext):
    """Меню для вопросов к AI"""
    from src.handlers.states import AskAI
    # Устанавливаем состояние ожидания вопроса для AI
    await state.set_state(AskAI.waiting_question)
    if callback.message and isinstance(callback.message, Message):
        # Отправляем новое сообщение вместо редактирования существующего
        await callback.message.answer(
            '<b>🤖 Спросить у AI</b>\n\n'
            'Задайте текстовый вопрос о продукции Газпромнефть-Битумные Материалы. '
            'ИИ проверит базу знаний и предоставим ответ, основываясь на доступной информации.\n\n'
            '<i>Примечание:</i>\n'
            'Ответы основываются на базе знаний, абсолютная точность не гарантирована. Если информации недостаточно, ИИ предложит уточнить запрос.\n',
            reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[[
                types.InlineKeyboardButton(
                    text="⬅️ Главное меню",
                    callback_data="menu:main"
                )
            ]]),
            parse_mode='HTML'
        )
    await callback.answer()


# NOTE: ВСЕГДА В КОНЦЕ ФАЙЛА ИНАЧЕ БУДЕТ КОНТЕКСТ НАРУШАТЬСЯ
@router.message(lambda message: message.text and not message.text.startswith('/'))
async def context_handler_outer_context(message: types.Message, state: FSMContext):
    """
    Базовый автоответчик для текстовых сообщений вне контекста
    Срабатывает только если:
    1. Это текстовое сообщение
    2. Не команда (не начинается с /)
    3. Пользователь не в FSM состоянии
    """
    current_state = await state.get_state()
    if current_state is not None:
        return  
    
    await message.answer(
        "Запрос не распознан. Для получения информации о возможностях бота, воспользуйтесь командой /help",
        reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[
            [
                types.InlineKeyboardButton(text="🔍 Поиск", callback_data="menu:search"),
                types.InlineKeyboardButton(text="📂 Каталог", callback_data="catalog:categories")
            ],
            [
                types.InlineKeyboardButton(text="🏠 Главное меню", callback_data="menu:main")
            ]
        ])
    )