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

@router.callback_query(lambda c: c.data == 'menu:main')
async def main_menu(callback: types.CallbackQuery, state: FSMContext):
    """Возврат в главное меню"""
    await state.clear()
    if callback.message and isinstance(callback.message, Message):
        try:
            # Пытаемся отредактировать как текстовое сообщение
            await callback.message.edit_text(
                '<b>Главное меню</b>\n\nВыберите действие:',
                reply_markup=get_main_menu_keyboard(),
                parse_mode='HTML'
            )
        except Exception:
            # Если не получилось (например, сообщение с медиа), отправляем новое
            await callback.message.answer(
                '<b>Главное меню</b>\n\nВыберите действие:',
                reply_markup=get_main_menu_keyboard(),
                parse_mode='HTML'
            )
            # Пытаемся удалить предыдущее сообщение
            try:
                await callback.message.delete()
            except Exception:
                pass  # Игнорируем ошибку удаления
    await callback.answer()

@router.callback_query(lambda c: c.data == 'menu:contact')
async def contact(callback: types.CallbackQuery):
    """Контактная информация"""
    if callback.message and isinstance(callback.message, Message):
        try:
            await callback.message.edit_text(
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
        except Exception:
            await callback.answer()
            await callback.message.delete()
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
            return
    await callback.answer()

@router.callback_query(lambda c: c.data == 'menu:features')
async def features(callback: types.CallbackQuery):
    """Описание возможностей бота"""
    if callback.message and isinstance(callback.message, Message):
        try:
            await callback.message.edit_text(
                '<b>👤 Возможности пользователей:</b>\n\n'
                '• Просмотр каталога продукции\n'
                '• Получение информации о продукте\n'
                '• Умный поиск\n'
                '• Получение контактной информации\n'
                '\n\n<b>🛠️ Возможности администраторов:</b>\n\n'
                '• Панель администратора по команде /admin\n'
                '• Показать весь список продуктов \n'
                '• Добавить продукт\n'
                '• Отредактировать карточку\n'
                '• Удалить карточку\n'
                '• Изменить главное фото продукта \n'
                '• Удалить главное фото продукта \n'
                '• Добавить файлы к определенному продукту \n'
                '• Удалить файлы у определенного продукта\n',
                reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[[
                    types.InlineKeyboardButton(
                        text="⬅️ Главное меню",
                        callback_data="menu:main"
                    )
                ]]),
                parse_mode='HTML'
            )
        except Exception:
            await callback.answer()
            await callback.message.delete()
            await callback.message.answer(
                '<b>👤 Возможности пользователей:</b>\n\n'
                '• Просмотр каталога продукции\n'
                '• Получение информации о продукте\n'
                '• Умный поиск\n'
                '• Получение контактной информации\n'
                '\n\n<b>🛠️ Возможности администраторов:</b>\n\n'
                '• Панель администратора по команде /admin\n'
                '• Показать весь список продуктов \n'
                '• Добавить продукт\n'
                '• Отредактировать карточку\n'
                '• Удалить карточку\n'
                '• Изменить главное фото продукта \n'
                '• Удалить главное фото продукта \n'
                '• Добавить файлы к определенному продукту \n'
                '• Удалить файлы у определенного продукта\n',
                reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[[
                    types.InlineKeyboardButton(
                        text="⬅️ Главное меню",
                        callback_data="menu:main"
                    )
                ]]),
                parse_mode='HTML'
            )
            return
    await callback.answer()

@router.callback_query(lambda c: c.data == 'menu:search')
async def search_menu(callback: types.CallbackQuery, state: FSMContext):
    """Меню поиска"""
    # Устанавливаем состояние ожидания поискового запроса
    await state.set_state(SearchProduct.waiting_query)
    
    if callback.message and isinstance(callback.message, Message):
        await callback.message.edit_text(
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
        await callback.message.edit_text(
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
        "Запрос не распознан. Для получения информации о доступных командах, используйте команду /help.",
        reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[
            [
                types.InlineKeyboardButton(text="🔍 Поиск по продукции", callback_data="menu:search"),
                types.InlineKeyboardButton(text="📂 Каталог продукции", callback_data="catalog:categories")
            ],
            [
                types.InlineKeyboardButton(text="🏠 Главное меню", callback_data="menu:main")
            ]
        ])
    )