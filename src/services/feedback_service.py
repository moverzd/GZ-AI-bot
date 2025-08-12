from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.feedback_repositories import (
    UserQueryRepository, 
    BotResponseRepository, 
    UserFeedbackRepository
)
from src.database.models import UserQuery, BotResponse, UserFeedback

"""
Сервис для работы с метриками и обратной связью пользователей.
"""


class FeedbackService:
    """Сервис для работы с обратной связью пользователей."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.query_repo = UserQueryRepository(session)
        self.response_repo = BotResponseRepository(session)
        self.feedback_repo = UserFeedbackRepository(session)
    
    async def log_user_query(
        self, 
        user_id: int, 
        username: Optional[str], 
        query_text: str, 
        query_type: str = 'ai_question'
    ) -> UserQuery:
        """Логирование пользовательского запроса."""
        return await self.query_repo.create_query(
            user_id=user_id,
            username=username,
            query_text=query_text,
            query_type=query_type
        )
    
    async def log_bot_response(
        self,
        query_id: int,
        response_text: str,
        response_type: str = 'ai_generated',
        execution_time: Optional[float] = None,
        sources_count: int = 0,
        message_id: Optional[int] = None
    ) -> BotResponse:
        """Логирование ответа бота."""
        return await self.response_repo.create_response(
            query_id=query_id,
            response_text=response_text,
            response_type=response_type,
            execution_time=execution_time,
            sources_count=sources_count,
            message_id=message_id
        )
    
    async def add_user_feedback(
        self,
        message_id: int,
        user_id: int,
        feedback_type: str,
        comment: Optional[str] = None
    ) -> Optional[UserFeedback]:
        """
        Добавление обратной связи пользователя.
        
        Args:
            message_id: ID сообщения в Telegram
            user_id: ID пользователя
            feedback_type: 'like' или 'dislike'
            comment: Комментарий (необязательный)
        
        Returns:
            UserFeedback или None, если ответ не найден
        """
        # Находим ответ бота по ID сообщения
        response = await self.response_repo.get_response_by_message_id(message_id)
        
        if not response:
            return None
        
        return await self.feedback_repo.create_feedback(
            response_id=response.id,
            user_id=user_id,
            feedback_type=feedback_type,
            comment=comment
        )
    
    async def get_feedback_stats(self) -> Dict[str, Any]:
        """Получить статистику по обратной связи."""
        return await self.feedback_repo.get_feedback_stats()
    
    async def get_user_feedback_for_message(
        self, 
        message_id: int, 
        user_id: int
    ) -> Optional[UserFeedback]:
        """Получить обратную связь пользователя для конкретного сообщения."""
        response = await self.response_repo.get_response_by_message_id(message_id)
        
        if not response:
            return None
        
        return await self.feedback_repo.get_user_feedback_for_response(
            response_id=response.id,
            user_id=user_id
        )
    
    async def get_negative_feedback_reports(self, limit: int = 50):
        """Получить отчеты с негативной обратной связью для анализа."""
        return await self.feedback_repo.get_negative_feedback_with_comments(limit)
