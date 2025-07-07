from aiogram import Router, types
from aiogram.filters import Command
from aiogram.types import Message
from src.keyboards.user import get_main_menu_keyboard

router = Router()

@router.message(Command('start'))
async def cmd_start(message: types.Message):
    """Обработчик команды /start"""
    await message.answer(
        'ГБ - телеграм бот битумных материалов\n'
        'Для быстрого поиска введите название продукта',
        reply_markup=get_main_menu_keyboard()
    )

@router.callback_query(lambda c: c.data == 'menu:main')
async def main_menu(callback: types.CallbackQuery):
    """Возврат в главное меню"""
    if callback.message and isinstance(callback.message, Message):
        await callback.message.edit_text(
            'Главное меню:',
            reply_markup=get_main_menu_keyboard()
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

@router.callback_query(lambda c: c.data == 'menu:question')
async def question(callback: types.CallbackQuery):
    """Задать вопрос"""
    if callback.message and isinstance(callback.message, Message):
        await callback.message.edit_text(
            'TBA',
            reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[[
                types.InlineKeyboardButton(
                    text="⬅️ Главное меню",
                    callback_data="menu:main"
                )
            ]])
        )
    await callback.answer()

@router.callback_query(lambda c: c.data == 'menu:features')
async def features(callback: types.CallbackQuery):
    """Описание возможностей бота"""
    if callback.message and isinstance(callback.message, Message):
        await callback.message.edit_text(
            '<b>🤖 Возможности бота:</b>\n\n'
            '• Просмотр всего ассортимента битумных материалов\n'
            '• Детальная информация о каждом продукте\n'
            '• Технические характеристики\n\n'
            '• Умный поиск\n'
            '• Контактная информация\n\n',
            reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[[
                types.InlineKeyboardButton(
                    text="⬅️ Главное меню",
                    callback_data="menu:main"
                )
            ]]),
            parse_mode='HTML'
        )
    await callback.answer()
