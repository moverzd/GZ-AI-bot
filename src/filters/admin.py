"""
admin.py
Filtering admins messages and other managament stuff

TODO: figure out what to put here
"""

from aiogram import types
from typing import List, Union, Dict, Any
from aiogram.filters import BaseFilter
from src.config.settings import settings
from aiogram.types InlineKeyboardMarkup

class AdminFilter(BaseFilter):
    """
    filtering admin accounts
    """

    def __init__(self, admin_ids: List[int]= None):
        self.admin_ids = admin_ids or settings.admin_ids
    
    async def __call__(self, message: types.Message) -> Union[bool, Dict[str,Any]]:
        """
        account admin checker
        """
        is_admin = message.from_user.id in self.admin_ids
        return {"is_admin": is_admin} if is_admin else False
    

from database.repositories import insert_image, insert_doc, soft_delete_product

"""
- admin handlers
- admin lists
"""

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