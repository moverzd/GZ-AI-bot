import logging

from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from src.services.rag import RagService
from src.services.feedback_service import FeedbackService
from src.handlers.states import AskAI
from src.keyboards.user import get_main_menu_keyboard, get_feedback_keyboard

logger = logging.getLogger(__name__)
router = Router()

# Создаем экземпляр RAG-сервиса
rag_service = RagService()

@router.message(AskAI.waiting_question)
async def handle_ai_question(message: Message, session: AsyncSession, state: FSMContext):
    """Обработчик вопросов к AI для всех пользователей."""
    if not message.text:
        await message.answer("Пожалуйста, задайте вопрос текстом.")
        return
    
    if not message.from_user:
        await message.answer("Ошибка определения пользователя.")
        return
    
    query_text = message.text.strip()
    
    # Создаем сервис для логирования
    feedback_service = FeedbackService(session)
    
    # Логируем пользовательский запрос
    user_query = await feedback_service.log_user_query(
        user_id=message.from_user.id,
        username=message.from_user.username,
        query_text=query_text,
        query_type='ai_question'
    )
    
    # Отправляем сообщение о начале обработки запроса
    processing_msg = await message.answer(
        f"🤖 Обрабатываю ваш вопрос: \n\"{query_text}\"\n"
        "Ищу информацию в базе знаний и формирую ответ..."
    )
    
    try:
        # Инициализируем RAG-сервис если еще не инициализирован
        await rag_service.initialize()
        
        # Выполняем поиск и генерацию ответа
        result = await rag_service.search_and_answer(
            query=query_text,
            top_k=8,  # Больше документов для лучшего контекста
            threshold=0.25,  # Снижаем порог для включения больше документов
            generate_answer=True
        )
        
        # Формируем ответ
        if isinstance(result, dict):
            llm_answer = result.get("llm_answer")
            search_results = result.get("search_results", [])
            execution_time = result.get("execution_time", 0)
            
            if llm_answer:
                # Редактируем сообщение о загрузке на уведомление о завершении
                await processing_msg.edit_text(
                    f"✅ Обработка завершена за {execution_time:.1f} сек."
                )
                
                # Отправляем ответ от AI отдельным сообщением
                response_text = f"🤖 <b>Ответ AI</b>:\n\n{llm_answer}"
                
                # Отправляем ответ с кнопками для обратной связи
                ai_response_msg = await message.answer(
                    response_text,
                    reply_markup=get_feedback_keyboard(message_id=0),  # Временно 0, обновим после получения ID
                    parse_mode="HTML"
                )
                
                # Логируем ответ бота с правильным message_id
                await feedback_service.log_bot_response(
                    query_id=user_query.id,
                    response_text=llm_answer,
                    response_type='ai_generated',
                    execution_time=execution_time,
                    sources_count=len(search_results),
                    message_id=ai_response_msg.message_id
                )
                
                # Обновляем клавиатуру с правильным message_id
                await ai_response_msg.edit_reply_markup(
                    reply_markup=get_feedback_keyboard(message_id=ai_response_msg.message_id)
                )
                
            else:
                # Редактируем сообщение о загрузке на ошибку
                await processing_msg.edit_text("❌ Обработка завершена с ошибкой")
                
                error_response = await message.answer(
                    "❌ Не удалось сгенерировать ответ на ваш вопрос. "
                    "Попробуйте переформулировать запрос или обратитесь к каталогу продукции.",
                    reply_markup=get_main_menu_keyboard()
                )
                
                # Логируем ошибочный ответ
                await feedback_service.log_bot_response(
                    query_id=user_query.id,
                    response_text="Не удалось сгенерировать ответ",
                    response_type='error',
                    execution_time=execution_time,
                    message_id=error_response.message_id
                )
        else:
            # Редактируем сообщение о загрузке на ошибку
            await processing_msg.edit_text("❌ Обработка завершена с ошибкой")
            
            error_response = await message.answer(
                "❌ Произошла ошибка при обработке запроса.",
                reply_markup=get_main_menu_keyboard()
            )
            
            # Логируем ошибочный ответ
            await feedback_service.log_bot_response(
                query_id=user_query.id,
                response_text="Произошла ошибка при обработке запроса",
                response_type='error',
                message_id=error_response.message_id
            )
    
    except Exception as e:
        logger.error(f"Ошибка при обработке AI-вопроса: {e}")
        
        # Редактируем сообщение о загрузке на ошибку
        try:
            await processing_msg.edit_text("❌ Обработка завершена с ошибкой")
        except:
            pass  # Игнорируем ошибки редактирования
        
        error_response = await message.answer(
            f"❌ Произошла ошибка при обработке вашего вопроса: {str(e)}\n"
            "Попробуйте позже или воспользуйтесь поиском по каталогу.",
            reply_markup=get_main_menu_keyboard()
        )
        
        # Логируем ошибочный ответ
        try:
            await feedback_service.log_bot_response(
                query_id=user_query.id,
                response_text=f"Ошибка: {str(e)}",
                response_type='error',
                message_id=error_response.message_id
            )
        except Exception as log_error:
            logger.error(f"Ошибка при логировании ответа: {log_error}")
    
    await state.clear()
