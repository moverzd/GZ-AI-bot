from typing import List, Optional, Dict, Any, Sequence
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, desc, update
from sqlalchemy.orm import selectinload
from datetime import datetime

from src.database.models import UserQuery, BotResponse, UserFeedback

"""
Репозитории для работы с метриками обратной связи пользователей.
"""


class UserQueryRepository:
    """Репозиторий для работы с пользовательскими запросами."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create_query(
        self, 
        user_id: int, 
        username: Optional[str], 
        query_text: str, 
        query_type: str = 'ai_question'
    ) -> UserQuery:
        """Создать новый запрос пользователя."""
        query = UserQuery(
            user_id=user_id,
            username=username,
            query_text=query_text,
            query_type=query_type
        )
        self.session.add(query)
        await self.session.commit()
        await self.session.refresh(query)
        return query
    
    async def get_user_queries(self,user_id: Optional[int] = None,limit: int = 50) -> List[UserQuery]:
        """Получить запросы пользователя или все запросы."""
        query = select(UserQuery).order_by(desc(UserQuery.created_at))
        
        if user_id:
            query = query.where(UserQuery.user_id == user_id)
        
        query = query.limit(limit)
        result = await self.session.execute(query)
        return list(result.scalars().all())
    
    async def get_query_with_responses(self, query_id: int) -> Optional[UserQuery]:
        """Получить запрос со всеми ответами."""
        query = select(UserQuery).options(
            selectinload(UserQuery.responses).selectinload(BotResponse.feedbacks)
        ).where(UserQuery.id == query_id)
        
        result = await self.session.execute(query)
        return result.scalar_one_or_none()


class BotResponseRepository:
    """Репозиторий для работы с ответами бота."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create_response(
        self,
        query_id: int,
        response_text: str,
        response_type: str = 'ai_generated',
        execution_time: Optional[float] = None,
        sources_count: int = 0,
        message_id: Optional[int] = None
    ) -> BotResponse:
        """Создать новый ответ бота."""
        response = BotResponse(
            query_id=query_id,
            response_text=response_text,
            response_type=response_type,
            execution_time=execution_time,
            sources_count=sources_count,
            message_id=message_id
        )
        self.session.add(response)
        await self.session.commit()
        await self.session.refresh(response)
        return response
    
    async def get_response_by_message_id(self, message_id: int) -> Optional[BotResponse]:
        """Получить ответ по ID сообщения в Telegram."""
        query = select(BotResponse).where(BotResponse.message_id == message_id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
    
    async def get_responses_without_feedback(self, limit: int = 100) -> List[BotResponse]:
        """Получить ответы без обратной связи."""
        query = select(BotResponse).outerjoin(UserFeedback).where(
            UserFeedback.id == None
        ).order_by(desc(BotResponse.created_at)).limit(limit)
        
        result = await self.session.execute(query)
        return list(result.scalars().all())


class UserFeedbackRepository:
    """Репозиторий для работы с обратной связью пользователей."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create_feedback(
        self,
        response_id: int,
        user_id: int,
        feedback_type: str,
        comment: Optional[str] = None
    ) -> UserFeedback:
        """Создать новую обратную связь."""
        # Проверяем, есть ли уже feedback от этого пользователя для этого ответа
        existing_feedback = await self.get_user_feedback_for_response(response_id, user_id)
        
        if existing_feedback:
            # Обновляем существующую обратную связь через update query
            await self.session.execute(
                update(UserFeedback)
                .where(UserFeedback.id == existing_feedback.id)
                .values(
                    feedback_type=feedback_type,
                    comment=comment,
                    updated_at=datetime.now()
                )
            )
            await self.session.commit()
            # Получаем обновленную запись
            await self.session.refresh(existing_feedback)
            return existing_feedback
        else:
            # Создаем новую обратную связь
            feedback = UserFeedback(
                response_id=response_id,
                user_id=user_id,
                feedback_type=feedback_type,
                comment=comment
            )
            self.session.add(feedback)
            await self.session.commit()
            await self.session.refresh(feedback)
            return feedback
    
    async def get_user_feedback_for_response(
        self, 
        response_id: int, 
        user_id: int
    ) -> Optional[UserFeedback]:
        """Получить обратную связь пользователя для конкретного ответа."""
        query = select(UserFeedback).where(
            and_(
                UserFeedback.response_id == response_id,
                UserFeedback.user_id == user_id
            )
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
    
    async def get_feedback_stats(self) -> Dict[str, Any]:
        """Получить статистику по обратной связи."""
        # Количество лайков и дизлайков
        like_count_query = select(func.count()).where(UserFeedback.feedback_type == 'like')
        dislike_count_query = select(func.count()).where(UserFeedback.feedback_type == 'dislike')
        
        # Общее количество ответов
        total_responses_query = select(func.count()).select_from(BotResponse)
        
        # Ответы с обратной связью
        responses_with_feedback_query = select(func.count(func.distinct(UserFeedback.response_id)))
        
        like_count = await self.session.scalar(like_count_query) or 0
        dislike_count = await self.session.scalar(dislike_count_query) or 0
        total_responses = await self.session.scalar(total_responses_query) or 0
        responses_with_feedback = await self.session.scalar(responses_with_feedback_query) or 0
        
        total_feedback = like_count + dislike_count
        feedback_rate = (responses_with_feedback / total_responses * 100) if total_responses > 0 else 0
        satisfaction_rate = (like_count / total_feedback * 100) if total_feedback > 0 else 0
        
        return {
            'total_responses': total_responses,
            'responses_with_feedback': responses_with_feedback,
            'feedback_rate': round(feedback_rate, 2),
            'likes': like_count,
            'dislikes': dislike_count,
            'total_feedback': total_feedback,
            'satisfaction_rate': round(satisfaction_rate, 2)
        }
    
    async def get_negative_feedback_with_comments(self, limit: int = 50) -> List[UserFeedback]:
        """Получить негативную обратную связь с комментариями."""
        query = select(UserFeedback).options(
            selectinload(UserFeedback.response).selectinload(BotResponse.query)
        ).where(
            and_(
                UserFeedback.feedback_type == 'dislike',
                UserFeedback.comment.is_not(None)
            )
        ).order_by(desc(UserFeedback.created_at)).limit(limit)
        
        result = await self.session.execute(query)
        return list(result.scalars().all())
