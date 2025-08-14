from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

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


def get_feedback_keyboard(message_id: int) -> InlineKeyboardMarkup:
    """
    Клавиатура для сбора обратной связи по ответу AI.
    
    Args:
        message_id: ID сообщения с ответом AI для связи с feedback
    
    Returns:
        Клавиатура с кнопками лайк/дизлайк
    """
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="👍 Полезно",
                callback_data=f"feedback:like:{message_id}"
            ),
            InlineKeyboardButton(
                text="👎 Не помогло",
                callback_data=f"feedback:dislike:{message_id}"
            )
        ],
        [
            InlineKeyboardButton(
                text="⬅️ В главное меню",
                callback_data="menu:main"
            )
        ]
    ])
    return keyboard


def get_feedback_submitted_keyboard() -> InlineKeyboardMarkup:
    """
    Клавиатура после отправки обратной связи.
    """
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="🔍 Поиск по продукции",
                callback_data="search:new"
            ),
            InlineKeyboardButton(
                text="🤖 Спросить AI",
                callback_data="menu:question"
            )
        ],
        [
            InlineKeyboardButton(
                text="⬅️ В главное меню",
                callback_data="menu:main"
            )
        ]
    ])
    return keyboard
