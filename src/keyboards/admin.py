from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardMarkup

def get_admin_main_menu_keyboard() -> InlineKeyboardMarkup:
    """
    Создает клавиатуру главного меню для администратора
    
    Returns:
        Разметка с админскими кнопками
    """
    builder = InlineKeyboardBuilder()
    builder.button(text='Каталог', callback_data='menu:catalog')
    builder.button(text='Контактная информация', callback_data='menu:contact')
    builder.button(text="➕ Добавить товар", callback_data="admin:add_prod")
    builder.adjust(1)
    return builder.as_markup()

def get_admin_product_keyboard(product_id: int) -> InlineKeyboardMarkup:
    """
    Создает клавиатуру администрирования продукта
    
    Args:
        product_id: ID продукта
        
    Returns:
        Разметка с кнопками администрирования
    """
    builder = InlineKeyboardBuilder()
    builder.button(text="✏️ Редактировать", callback_data=f"edit:{product_id}")
    builder.button(text="🗑️ Удалить", callback_data=f"delete:{product_id}")
    builder.button(text="➕ Добавить фото", callback_data=f"add_photo:{product_id}")
    builder.button(text="📄 Добавить документ", callback_data=f"add_doc:{product_id}")
    builder.button(text="⬅️ Назад", callback_data="menu:main")
    builder.adjust(1)
    return builder.as_markup()

def get_edit_field_keyboard(product_id: int) -> InlineKeyboardMarkup:
    """
    Создает клавиатуру выбора поля для редактирования
    
    Args:
        product_id: ID продукта
        
    Returns:
        Разметка с кнопками полей для редактирования
    """
    builder = InlineKeyboardBuilder()
    builder.button(text="Название", callback_data=f"field:name:{product_id}")
    builder.button(text="Описание", callback_data=f"field:short_desc:{product_id}")
    # Другие поля...
    builder.button(text="⬅️ Отмена", callback_data=f"product:{product_id}")
    builder.adjust(1)
    return builder.as_markup()

def get_delete_confirm_keyboard(product_id: int) -> InlineKeyboardMarkup:
    """
    Создает клавиатуру подтверждения удаления
    
    Args:
        product_id: ID продукта
        
    Returns:
        Разметка с кнопками подтверждения
    """
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Подтвердить удаление", callback_data=f"confirm_delete:{product_id}")
    builder.button(text="❌ Отмена", callback_data=f"cancel_delete:{product_id}")
    builder.adjust(1)
    return builder.as_markup()