from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardMarkup

def get_admin_main_menu_keyboard() -> InlineKeyboardMarkup:
    """
    Создает клавиатуру главного меню для администратора
    
    Returns:
        Разметка с админскими кнопками
    """
    builder = InlineKeyboardBuilder()
    builder.button(text = "📋📦 Показать весь список продуктов", callback_data= "admin:get_products")
    builder.button(text="➕📦 Добавить продукт", callback_data="admin:add_product")
    builder.button(text="✏️📦 Отредактировать продукт", callback_data="admin:edit_product")
    builder.button(text="️🗑️📦 Удалить продукт", callback_data="admin:delete_product")
    builder.button(text="🔄🖼️ Изменить главное фото продукта", callback_data="admin:upload_main_image")
    builder.button(text="🗑️🖼️️ Удалить главное фото продукта", callback_data="admin:delete_main_image")
    builder.button(text="➕📎 Добавить файлы к продукту", callback_data="admin:add_files")
    builder.button(text="🗑📎 Удалить файлы продукта", callback_data="admin:delete_files")
    builder.button(text="🏠 Главное меню", callback_data="menu:main")
    builder.adjust(1)
    return builder.as_markup()


def get_edit_field_keyboard(product_id: int) -> InlineKeyboardMarkup:
    """
    Создает клавиатуру выбора поля для редактирования
    """
    builder = InlineKeyboardBuilder()
    builder.button(text="Название", callback_data=f"field:name:{product_id}")
    builder.button(text="Полное описание", callback_data=f"field:description:{product_id}")
    builder.button(text="Преимущества", callback_data=f"field:advantages:{product_id}")
    builder.button(text="Расход", callback_data=f"field:notes:{product_id}")
    builder.button(text="📦 Упаковка", callback_data=f"edit_package:{product_id}")
    builder.button(text="⬅️ Вернуться в меню", callback_data="menu:main")
    builder.adjust(1)
    return builder.as_markup()

def get_delete_confirm_keyboard(product_id: int) -> InlineKeyboardMarkup:
    """
    Создает клавиатуру подтверждения удаления
    """
    builder = InlineKeyboardBuilder()
    builder.button(text="Подтвердить удаление", callback_data=f"confirm_delete:{product_id}")
    builder.button(text="Отмена", callback_data=f"cancel_delete:{product_id}")
    builder.adjust(1)
    return builder.as_markup()