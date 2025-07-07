from typing import Dict, Any, Callable, Awaitable, Union, Optional
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, User, Message, CallbackQuery
from src.config.settings import settings


class AdminMiddleware(BaseMiddleware):
    """
    Проверка админ прав добавление флага is_admin в handler
    """
    async def __call__(
            self,
            handler: Callable[[TelegramObject, Dict[str,Any]], Awaitable[Any]],
            event: TelegramObject,
            data: Dict[str,Any]
    ) -> Any:
        user: Optional[User] = None
        
        if isinstance(event, Message):
            user = event.from_user
        
        elif isinstance(event, CallbackQuery):
            user = event.from_user
        
        if user and user.id in settings.admin_ids:
            data["is_admin"] = True
        else:
            data["is_admin"] = False
        
        return await handler(event, data)



class DatabaseSessionMiddleware(BaseMiddleware):
    """
    Управление сессиями бд
    Добавляет сессию в контекст handler'а и закрывает ее после выполнения.
    """
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        from src.database.connection import AsyncSessionLocal
        
        # Создаем новую сессию для каждого запроса
        async with AsyncSessionLocal() as session:
            # Добавляем сессию в данные обработчика
            data["session"] = session
            try:
                return await handler(event, data)
            finally:
                await session.close()
        
        # Обрабатываем событие
        result = await handler(event, data)
        
        # Возвращаем результат
        return result