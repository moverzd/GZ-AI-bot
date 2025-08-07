from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardMarkup

def get_main_menu_keyboard() -> InlineKeyboardMarkup:
    """
    Клавиатура главного меню для пользователя
    """
    builder = InlineKeyboardBuilder()
    builder.button(text='🔍 Поиск по продукции', callback_data='menu:search')
    builder.button(text='📂 Каталог продукции', callback_data='menu:catalog')
    builder.button(text='🤖 Спросить у AI', callback_data='menu:question')
    builder.button(text='❔ П️омощь', callback_data='menu:features')
    builder.button(text='📞 Контактная информация', callback_data='menu:contact')

    builder.adjust(1)

    return builder.as_markup()
