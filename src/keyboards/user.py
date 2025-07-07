from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardMarkup

def get_main_menu_keyboard() -> InlineKeyboardMarkup:
    """
    Making keyboard of main menu for basic level user

    Returns: Markup of main menu buttons
    """
    builder = InlineKeyboardBuilder()
    builder.button(text='🔍 Поиск продукции', callback_data='menu:search')
    builder.button(text='Описание возможностей', callback_data='menu:features')
    builder.button(text='Каталог Продукции', callback_data='menu:catalog')
    builder.button(text='Контактная информация', callback_data='menu:contact')
    builder.button(text='Спросить у AI (TBA)', callback_data='menu:question')

    builder.adjust(1)

    return builder.as_markup()


def get_catalog_keyboard() -> InlineKeyboardMarkup:
    """
    Making keyboard for menu catalgo

    Returns: Markyp of catalog buttons
    """
    builder = InlineKeyboardBuilder()
    builder.button(text='⬅️ Назад', callback_data='menu:main')

    builder.adjust(1)

    return builder.as_markup()


def get_product_keyboard(product_id: int) -> InlineKeyboardMarkup:
    """
    making keyboard for for showing products

    Returns: markup of products button
    """
    builder = InlineKeyboardBuilder()
    builder.button(text='⬅️ Назад к категории', callback_data='catalog:back')
    builder.adjust(1)

    return builder.as_markup()


