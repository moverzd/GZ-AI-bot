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
"""


router = Router()

@router.message(Command('start'))
async def cmd_start(message: types.Message, state: FSMContext):
    """Обработчик команды /start"""
    await state.clear() # очистка состояния FSM
    await message.answer(
        'ГБ - телеграм бот битумных материалов\n',
        reply_markup=get_main_menu_keyboard()
    )

@router.callback_query(lambda c: c.data == 'menu:main')
async def main_menu(callback: types.CallbackQuery, state: FSMContext):
    """Возврат в главное меню"""
    await state.clear()
    if callback.message and isinstance(callback.message, Message):
        await callback.message.edit_text(
            '<b>Главное меню</b>\n\nВыберите действие:',
            reply_markup=get_main_menu_keyboard(),
            parse_mode='HTML'
        )
    await callback.answer()

@router.callback_query(lambda c: c.data == 'menu:contact')
async def contact(callback: types.CallbackQuery):
    """Контактная информация"""
    if callback.message and isinstance(callback.message, Message):
        await callback.message.edit_text(
            '<b>Контактная информация:</b>\n'
            '"ООО Газпромнефть-БМ"\n'
            '<b>Телефон:</b> +7 (812) 493-25-66\n'
            '<b>Адрес:</b> TBA\n'
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
        await callback.message.edit_text(
            '<b>Возможности пользователей:</b>\n\n'
            '• Просмотр каталога продукции\n'
            '• Получение информации о продукте\n'
            '• Умный поиск\n'
            '• Получение контактной информации\n'
            '\n\n<b>Возможности администраторов:</b>\n\n'
            '• Меню администратора по команде /admin\n'
            '• Добавить продукт - /add_product\n'
            '• Отредактировать карточку - /edit_product ID_продукта\n'
            '• Удалить карточку - /delete_product ID_продукта\n',
            reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[[
                types.InlineKeyboardButton(
                    text="⬅️ Главное меню",
                    callback_data="menu:main"
                )
            ]]),
            parse_mode='HTML'
        )
    await callback.answer()

@router.callback_query(lambda c: c.data == 'menu:search')
async def search_menu(callback: types.CallbackQuery, state: FSMContext):
    """Меню поиска"""
    # Устанавливаем состояние ожидания поискового запроса
    await state.set_state(SearchProduct.waiting_query)
    
    if callback.message and isinstance(callback.message, Message):
        await callback.message.edit_text(
            '<b>Поиск продуктов</b>\n\n'
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
