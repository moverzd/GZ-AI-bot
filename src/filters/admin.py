from aiogram import types
from typing import List, Union, Dict, Any
from aiogram.filters import BaseFilter
from src.config.settings import settings

"""
Фильтрация сообщений от админов.
"""
class AdminFilter(BaseFilter):
    """
    Класс фильтра, является ли пользователь админом.
    """
    def __init__(self, admin_ids: List[int] | None = None):
        self.admin_ids = admin_ids or settings.admin_ids

   # __call__ - позволяет объекту фильтра вести себя как функция. 
    async def __call__(self, message: types.Message) -> Union[bool, Dict[str,Any]]:
        if message.from_user is None:
            return False
        is_admin = message.from_user.id in self.admin_ids
        return {"is_admin": is_admin} if is_admin else False
